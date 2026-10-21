# IAM: identities and policies

> **In this chapter**
> - Users, groups, roles and federated identities, and when to use which
> - The policy language: Effect, Action, Resource, Principal, Condition, variables
> - How AWS evaluates policies (explicit deny > allow > implicit deny), including cross-account
> - Roles in depth: trust policies, `iam:PassRole`, external IDs, service roles
> - Tools: Access Analyzer, policy simulator, `decode-authorization-message`
>
> **Exam weight**: Domain 2, Task 2.1 (and the background of most security questions)
> · **Exercises**: `iam_1`–`iam_5` · **Quiz**: `uv run awslings quiz iam`

## Identities

| Identity | Credentials | Use it for |
|---|---|---|
| **Root user** | Email + password (+ MFA) | Almost nothing: account settings, billing, closing the account |
| **IAM user** | Password (console) and/or **long-term access keys** | Legacy, break-glass, rare machine cases. Prefer roles and Identity Center |
| **IAM group** | none (a collection of users) | Attaching policies to many users. Groups **cannot be nested** and **cannot be a principal** in a policy |
| **IAM role** | **Temporary** credentials from STS when assumed | Applications (EC2, Lambda, ECS), cross-account access, federation |
| **Federated identity** | External IdP (SAML 2.0, OIDC, Cognito) → role | Workforce SSO (IAM Identity Center), app users (Cognito identity pools) |

> **Exam tip** — Whenever code runs on AWS (EC2, Lambda, ECS, CodeBuild...), the answer is
> **an IAM role** attached to that compute, never access keys in code, environment variables or AMIs.

## Policies

### Policy types

| Type | Attached to | Notes |
|---|---|---|
| **Identity-based** | Users, groups, roles | *AWS managed* (maintained by AWS, broad), *customer managed* (yours, reusable, versioned, up to 5 versions), *inline* (embedded 1:1 in a single identity, deleted with it) |
| **Resource-based** | Resources: S3 bucket policy, SQS queue policy, SNS topic policy, KMS key policy, Lambda function policy, Secrets Manager, ECR... | Has a **`Principal`** element. Enables cross-account access without assuming a role |
| **Permissions boundary** | Users, roles | Sets the **maximum** permissions an identity can get. Does not grant anything |
| **Service control policy (SCP)** | Accounts / OUs in AWS Organizations | Maximum permissions for every principal of the account (including root) |
| **Session policy** | Passed when assuming a role / federating | Further restricts that session |
| **ACLs** | S3 (legacy), VPC (network ACLs are different) | Not JSON policies. S3 ACLs are disabled by default on new buckets |

> **Exam tip** — *AWS managed vs customer managed*: AWS managed policies are convenient but
> generic (often too broad for least privilege) and change when AWS updates them. Customer managed
> policies let you scope permissions exactly and control versions. Inline policies are for a strict
> 1:1 relationship.

### Anatomy of a policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ReadOwnOrders",
      "Effect": "Allow",
      "Action": ["dynamodb:GetItem", "dynamodb:Query"],
      "Resource": [
        "arn:aws:dynamodb:eu-west-3:123456789012:table/Orders",
        "arn:aws:dynamodb:eu-west-3:123456789012:table/Orders/index/*"
      ],
      "Condition": {
        "ForAllValues:StringEquals": {"dynamodb:LeadingKeys": ["${aws:PrincipalTag/customer_id}"]}
      }
    }
  ]
}
```

- **Version** — always `"2012-10-17"`. The old `2008-10-17` does not support policy variables.
- **Effect** — `Allow` or `Deny`.
- **Action / NotAction** — `service:Operation`, wildcards allowed (`s3:Get*`). Case-insensitive.
- **Resource / NotResource** — ARNs, wildcards allowed. Case-sensitive. Some actions only support `"*"`.
- **Principal** — only in resource-based policies (and trust policies): `{"AWS": "arn:aws:iam::111122223333:root"}`,
  `{"Service": "lambda.amazonaws.com"}`, `{"Federated": "cognito-identity.amazonaws.com"}`, `"*"`.
- **Condition** — extra checks on the request context (next section).

> **Trap** — S3 has two kinds of resources: the **bucket** (`arn:aws:s3:::my-bucket`) for
> `s3:ListBucket`, and **objects** (`arn:aws:s3:::my-bucket/*`) for `s3:GetObject`/`PutObject`.
> A policy that only lists `my-bucket/*` cannot list the bucket.

### Conditions

```json
"Condition": {
  "Bool":            {"aws:SecureTransport": "false"},
  "IpAddress":       {"aws:SourceIp": "203.0.113.0/24"},
  "StringEquals":    {"aws:RequestedRegion": ["eu-west-3", "eu-west-1"]},
  "StringLike":      {"s3:prefix": ["home/${aws:username}/*"]},
  "ArnLike":         {"aws:SourceArn": "arn:aws:s3:::my-bucket"},
  "NumericLessThan": {"s3:max-keys": "100"},
  "Null":            {"aws:MultiFactorAuthAge": "true"}
}
```

- Operators: `StringEquals`/`StringLike`/`StringNotEquals`, `ArnLike`, `NumericLessThan`,
  `DateGreaterThan`, `Bool`, `IpAddress`, `Null` (key present or not), `...IfExists`, and set
  operators `ForAllValues:` / `ForAnyValue:` for multi-valued keys.
- Multiple conditions in one block are **AND**ed. Multiple values for one key are **OR**ed.
- Useful global keys: `aws:SourceIp`, `aws:SecureTransport`, `aws:MultiFactorAuthPresent`,
  `aws:PrincipalTag/...`, `aws:ResourceTag/...`, `aws:RequestedRegion`, `aws:SourceArn` and
  `aws:SourceAccount` (protect resource policies used by AWS services), `aws:PrincipalOrgID`.
- Service-specific keys: `s3:prefix`, `s3:x-amz-server-side-encryption`, `dynamodb:LeadingKeys`
  (row-level security), `kms:EncryptionContext:*`, `kms:ViaService`.

### Policy variables

Variables are resolved at evaluation time, so **one policy serves every user**:
`${aws:username}`, `${aws:userid}`, `${aws:PrincipalTag/team}`, and for Cognito identity pools
`${cognito-identity.amazonaws.com:sub}` (chapter 12).

```json
{"Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject"],
 "Resource": "arn:aws:s3:::corp-docs/home/${aws:username}/*"}
```

> **Trap** — building such a policy with a Python f-string or a shell double-quoted string
> eats `${...}`. The variable must reach IAM literally (exercise `iam_5`).

## How AWS evaluates a request

For a request inside **one account**:

```text
1. Collect every applicable policy (identity, resource, boundary, SCP, session).
2. Is there an explicit DENY matching the request?          → DENY (final)
3. SCPs, permissions boundary, session policy: does each one allow it? (if present)
                                                     no     → DENY (implicit)
4. Is there an explicit ALLOW in an identity-based OR resource-based policy?
                                                     yes    → ALLOW
5. Otherwise                                                → DENY (implicit, the default)
```

- **Explicit deny always wins.** Default is deny.
- Boundaries, SCPs and session policies only *limit*. The effective permissions are the
  **intersection** of identity policy ∩ boundary ∩ SCP ∩ session policy.
- **Cross-account** without roles: the caller's **identity policy** (account A) AND the target's
  **resource-based policy** (account B) must both allow the action. With a **role** in account B,
  the caller assumes it and acts with the role's permissions in B (trust policy + `sts:AssumeRole` permission in A).
- **KMS** is special: the key policy must allow access (directly, or by trusting the account so
  that IAM policies apply). An IAM policy alone is not enough (chapter 13).

> **Exam tip** — "User has `AmazonS3FullAccess` but gets AccessDenied on one bucket" → look for an
> explicit **Deny** (bucket policy, SCP, permissions boundary), or a KMS key policy for SSE-KMS objects.

## Roles in depth

A role has **two** policy sides:

```text
Trust policy (AssumeRolePolicyDocument)   WHO may assume the role
  {"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}

Permissions policies                       WHAT the role may do once assumed
  {"Effect": "Allow", "Action": "dynamodb:PutItem", "Resource": "arn:aws:dynamodb:...:table/Orders"}
```

- **Service roles**: a Lambda *execution role*, an ECS *task role*, a CodeBuild service role, an
  EC2 *instance profile*... **Service-linked roles** are predefined by a service and managed by it.
- **`iam:PassRole`**: to give a role to a service (create a Lambda function with role X, launch EC2
  with an instance profile, register an ECS task definition with a task role), the *caller* needs
  `iam:PassRole` on that role. This prevents privilege escalation: you cannot hand a service a role
  more powerful than what you are allowed to pass.
- **Cross-account roles for third parties**: add an **external ID** condition
  (`"Condition": {"StringEquals": {"sts:ExternalId": "..."}}`) to the trust policy to avoid the
  *confused deputy* problem.
- **Sessions**: 1 h by default, configurable up to the role's max session duration (1–12 h).
  **Role chaining** (assuming a role from a role session) is limited to 1 h.

## RBAC and ABAC

- **RBAC** (role-based access control): permissions attached to job functions (groups/roles).
  Simple, but policies multiply as resources grow.
- **ABAC** (attribute-based): permissions based on **tags**, e.g. allow actions when
  `aws:ResourceTag/project` equals `aws:PrincipalTag/project`. One policy scales to new projects.

## Tools and troubleshooting

| Tool | Use |
|---|---|
| **IAM Access Analyzer** | Find resources shared outside your account/organization. Validate policies (grammar + best practices). **Generate least-privilege policies from CloudTrail activity** |
| **IAM policy simulator** | Test whether a principal can perform an action on a resource, and which statement decides |
| **Last accessed information** / credential report | Remove unused permissions, find old access keys |
| `aws sts decode-authorization-message` | Decode the encoded failure message returned by some services (e.g. EC2 `UnauthorizedOperation`). Needs `sts:DecodeAuthorizationMessage` |
| **CloudTrail** | Who called what, when, from where, and the `AccessDenied` error code |
| `aws sts get-caller-identity` | "Which identity am I actually using?" The first thing to check when debugging credentials |

## Best practices (the exam's favorites)

1. Least privilege: start from nothing, add what is needed. Use Access Analyzer to refine.
2. Roles and temporary credentials for workloads. IAM Identity Center for humans.
3. MFA for privileged users. Never use the root user. No access keys for root.
4. Rotate any remaining access keys. Never commit them (use git-secrets / secret scanning).
5. Use conditions (`aws:SecureTransport`, `aws:SourceArn`...) and permissions boundaries for delegated administration.

## Hands-on

| Exercise | Skill |
|---|---|
| `iam_1` | Write a least-privilege identity policy for a table and its indexes |
| `iam_2` | Implement the evaluation logic (implicit deny, allow, explicit deny, wildcards) |
| `iam_3` | Create a Lambda execution role: trust policy vs permissions |
| `iam_4` | Bucket policy with conditions: deny non-TLS, require SSE-KMS, allow a role |
| `iam_5` | One policy for all users with `${aws:username}` |

## Summary

- Roles (temporary credentials) for workloads. Users with long-term keys are a last resort.
- Policy = Effect + Action + Resource (+ Principal for resource policies) + Condition.
- Explicit deny > explicit allow > implicit deny. Boundaries and SCPs only restrict.
- Cross-account: identity policy AND resource policy, or assume a role in the other account.
- `iam:PassRole` is needed to hand a role to a service. Use external IDs for third-party role assumption.

## Check yourself

1. A developer's IAM policy allows `s3:*` on `*`, but an SCP denies `s3:DeleteBucket`. Can they delete a bucket?
2. What is the difference between a trust policy and a permissions policy?
3. A CI user must create Lambda functions that use the existing role `orders-role`. Which permission, besides `lambda:CreateFunction`, is required?
4. Account A's Lambda must read objects from a bucket in account B, without assuming a role. What is needed?
5. Which policy element exists only in resource-based policies?

<details><summary>Answers</summary>

1. No. The SCP's explicit deny wins over any allow.
2. The trust policy (on the role) says which principals may assume it (`sts:AssumeRole`). The
   permissions policies say what the role can do once assumed.
3. `iam:PassRole` on `orders-role`.
4. The Lambda execution role (account A) must allow `s3:GetObject` on the bucket, AND the bucket
   policy (account B) must allow that role as principal. With SSE-KMS, the KMS key policy must allow it too.
5. `Principal`.

</details>

## Further reading

- [Policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)
- [IAM JSON policy elements reference](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements.html)
- [Global condition context keys](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html)
- [Security best practices in IAM](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [IAM Access Analyzer](https://docs.aws.amazon.com/IAM/latest/UserGuide/what-is-access-analyzer.html)
