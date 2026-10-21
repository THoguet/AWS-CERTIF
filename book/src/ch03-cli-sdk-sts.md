# CLI, SDKs, credentials and STS

> **In this chapter**
> - How requests are authenticated (SigV4) and where SDKs find credentials
> - AWS CLI v2 essentials: profiles, output, `--query`, pagination
> - SDK patterns: clients, retries with backoff and jitter, timeouts, pagination, waiters, errors
> - AWS STS: AssumeRole and friends, temporary credentials, MFA
> - Developer productivity tools in scope: CloudShell, Amazon Q Developer
>
> **Exam weight**: Domain 1 Task 1.1 (code using SDKs and APIs), Domain 2 Task 2.1 (programmatic
> access, authenticated calls, assuming roles) · **Exercises**: `intro_2`, `sdk_1`–`sdk_5`
> · **Quiz**: `uv run awslings quiz sdk`

## How a request is authenticated

Every AWS API call is an HTTPS request **signed with Signature Version 4 (SigV4)**. The SDK
derives a signing key from your **secret access key**, the date, the Region and the service, and
signs a canonical form of the request. AWS recomputes the signature on its side.

- With **temporary credentials**, the request also carries the **session token**
  (`X-Amz-Security-Token`).
- Requests are valid for a short window. A machine clock off by more than ~5 minutes gives
  `SignatureDoesNotMatch` / `RequestTimeTooSkewed`.
- **Presigned URLs** (S3) put the SigV4 signature in the query string (chapter 4).

| Error | Usual cause |
|---|---|
| `UnrecognizedClientException` / `InvalidClientTokenId` | Access key id unknown (typo, deleted key, wrong partition) |
| `SignatureDoesNotMatch` | Wrong secret key, or clock skew |
| `ExpiredToken` / `ExpiredTokenException` | Temporary credentials expired. Refresh them (the SDK does it for roles) |
| `AccessDenied` / `AccessDeniedException` (403) | Authenticated, but not authorized by policies |

## Where do credentials come from?

The CLI and SDKs walk the **default credential provider chain** and use the first source that works.
Simplified order (boto3/CLI):

1. Credentials passed **explicitly** in code or on the command line (avoid it)
2. **Environment variables**: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`
3. Profile-based sources from the config (assume-role profiles, web identity, IAM Identity Center/SSO)
4. **Shared credentials file** `~/.aws/credentials` (profile = `AWS_PROFILE` or `default`)
5. **Config file** `~/.aws/config`
6. **Container credentials** (ECS/EKS task roles) via `AWS_CONTAINER_CREDENTIALS_RELATIVE_URI`
7. **EC2 instance metadata** (instance profile role)

On **Lambda**, the runtime injects the execution role's temporary credentials as environment
variables. On **ECS**, the task role is served through the container credentials endpoint.
On **EC2**, through IMDS.

> **Trap** — Stale `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` environment variables on an EC2
> instance **win over** the instance profile, so the app runs with the wrong identity. Run
> `aws sts get-caller-identity` to see who you really are.

## AWS CLI v2 essentials

```bash
aws configure --profile dev            # writes ~/.aws/credentials and ~/.aws/config
aws configure sso                      # IAM Identity Center profile (recommended for humans)
aws s3 ls --profile dev --region eu-west-3
export AWS_PROFILE=dev                 # default profile for this shell

# Output and filtering
aws dynamodb list-tables --output table          # json | yaml | text | table
aws ec2 describe-instances \
  --filters Name=instance-state-name,Values=running \      # server-side filter
  --query 'Reservations[].Instances[].InstanceId' --output text   # client-side JMESPath

# Pagination (the CLI paginates automatically)
aws s3api list-objects-v2 --bucket b --max-items 100 --page-size 50
aws s3api list-objects-v2 --bucket b --max-items 100 --starting-token <NextToken>

# Safety and debugging
aws ec2 run-instances ... --dry-run    # checks permissions without doing anything (EC2)
aws s3 ls --debug                      # see the credential source, signed request, retries
```

An **assume-role profile** in `~/.aws/config`:

```ini
[profile prod-admin]
role_arn       = arn:aws:iam::210987654321:role/admin
source_profile = default
mfa_serial     = arn:aws:iam::123456789012:mfa/ada     ; asks for an MFA code
region         = eu-west-3
```

> **Exam tip** — `--query` filters **client-side** after download (JMESPath). `--filters` (EC2) or
> `--prefix` (S3) filter **server-side**, which is faster and cheaper on big result sets.

## SDK patterns

### Clients, resources, sessions

```python
import boto3

s3 = boto3.client("s3", region_name="eu-west-3")         # low-level, 1:1 with the API
table = boto3.resource("dynamodb").Table("Orders")        # higher-level objects (boto3 "resources")
session = boto3.Session(profile_name="dev")               # explicit profile / region
sqs = session.client("sqs")
```

Create clients **once** and reuse them. On Lambda, create them outside the handler (chapter 5).

### Retries, backoff and jitter

Transient failures are normal at scale: throttling (`ThrottlingException`,
`ProvisionedThroughputExceededException`, `TooManyRequestsException`, `RequestLimitExceeded`,
`SlowDown`) and server errors (HTTP 500/502/503/504). The right reaction is to **retry with
exponential backoff and jitter**:

```text
delay(attempt) = random(0, min(cap, base × 2^attempt))     ← "full jitter"
attempt 0: 0–100 ms · attempt 1: 0–200 ms · attempt 2: 0–400 ms · ... capped
```

Backoff spreads the load over time, and jitter keeps clients from retrying in lockstep (the thundering herd).
**All AWS SDKs already retry** with backoff and jitter. You configure them:

```python
from botocore.config import Config

config = Config(
    retries={"mode": "standard", "total_max_attempts": 10},   # legacy | standard | adaptive
    connect_timeout=2, read_timeout=5,
)
dynamodb = boto3.client("dynamodb", config=config)
```

- **standard**: consistent behavior across SDKs, more retryable errors, a retry quota (token bucket).
  The AWS CLI v2 uses it by default. boto3 defaults to **legacy** unless you configure it.
- **adaptive**: standard + client-side rate limiting when throttled.
- Only retry **idempotent** or safely repeatable operations. Use idempotency tokens when the API
  offers them (`ClientToken`, `ClientRequestToken`).
- **4xx client errors** (validation, access denied, not found) must NOT be retried. Fix the request.

> **Exam tip** — "The application receives `ProvisionedThroughputExceededException` / 429
> intermittently" → **retry with exponential backoff and jitter** (and/or raise capacity). Don't
> answer "retry immediately in a loop".

### Pagination and waiters

```python
paginator = s3.get_paginator("list_objects_v2")
for page in paginator.paginate(Bucket="data-lake", Prefix="raw/", PaginationConfig={"PageSize": 500}):
    for obj in page.get("Contents", []):
        ...

client.get_waiter("table_exists").wait(TableName="Orders")    # polls DescribeTable until ACTIVE
```

A single `ListObjectsV2` returns at most **1,000 keys**. DynamoDB `Query`/`Scan` return at most
**1 MB** per call. Forgetting to paginate is a silent data-loss bug.

### Errors in code

```python
from botocore.exceptions import ClientError

try:
    table.put_item(Item=item, ConditionExpression="attribute_not_exists(pk)")
except ClientError as err:
    code = err.response["Error"]["Code"]          # "ConditionalCheckFailedException"
    status = err.response["ResponseMetadata"]["HTTPStatusCode"]
```

## AWS STS — temporary credentials

| API | Use |
|---|---|
| `AssumeRole` | Switch to a role (same or another account). Returns `AccessKeyId` (`ASIA...`), `SecretAccessKey`, `SessionToken`, `Expiration` |
| `AssumeRoleWithWebIdentity` | Exchange an OIDC token (Google, GitHub Actions, EKS service accounts) for role credentials. For mobile/web users, prefer **Cognito identity pools** |
| `AssumeRoleWithSAML` | Enterprise SAML federation (workforce, mostly via IAM Identity Center now) |
| `GetSessionToken` | Temporary credentials for an IAM user, typically to satisfy an **MFA** requirement |
| `GetFederationToken` | Temporary credentials for a federated user, issued by a long-term identity (legacy proxy apps) |
| `GetCallerIdentity` | Who am I? (account, ARN). No permission needed |
| `DecodeAuthorizationMessage` | Decode an encoded authorization failure message |

```python
sts = boto3.client("sts")
creds = sts.assume_role(
    RoleArn="arn:aws:iam::210987654321:role/auditor",
    RoleSessionName="nightly-audit",           # visible in CloudTrail and in the assumed-role ARN
    DurationSeconds=900,                       # 15 min to the role's max session duration (≤ 12 h)
    # SerialNumber="arn:aws:iam::123456789012:mfa/ada", TokenCode="123456",   # if MFA is required
)["Credentials"]
s3 = boto3.client("s3",
    aws_access_key_id=creds["AccessKeyId"],
    aws_secret_access_key=creds["SecretAccessKey"],
    aws_session_token=creds["SessionToken"])
```

- The resulting identity is `arn:aws:sts::<account>:assumed-role/<role-name>/<session-name>`.
- Requiring MFA: add `"Bool": {"aws:MultiFactorAuthPresent": "true"}` to the trust policy (or to permissions).
- Use **regional STS endpoints** (lower latency, no dependency on us-east-1).

> **Trap** — Using temporary credentials **without the session token** fails with
> "The security token included in the request is invalid".

## Productivity tools in scope

- **AWS CloudShell** — a browser shell in the console, already authenticated as your console
  identity, with the AWS CLI and common tools installed, and 1 GB of persistent home storage per Region.
- **Amazon Q Developer** (replaced Amazon CodeWhisperer, added to the exam guide in v2.1) — an
  AI assistant in the IDE, CLI and console. It offers inline code suggestions, chat about your
  code and AWS, explaining code, **generating unit tests**, **security scanning**, code
  transformations (e.g. Java version upgrades), and diagnosing console errors.
  > **Exam tip** — "Developers want AI-generated code suggestions / tests / vulnerability scans in
  > their IDE with the least effort" → **Amazon Q Developer**.

## Hands-on

| Exercise | Skill |
|---|---|
| `intro_2` | First client, Region, string attributes |
| `sdk_1` | The credential provider chain |
| `sdk_2` | Paginators and page size |
| `sdk_3` | Exponential backoff with full jitter, retryable vs non-retryable errors |
| `sdk_4` | STS AssumeRole and clients with temporary credentials |
| `sdk_5` | Retry modes, timeouts, waiters |

## Summary

- Requests are SigV4-signed. Temporary credentials add a session token.
- Credential chain: explicit → env vars → profiles/files → container → instance metadata. On AWS, use roles.
- Paginate every list call. Use waiters instead of hand-written polling.
- Retry throttling and 5xx with exponential backoff + jitter (SDK retry modes). Never retry 4xx validation/permission errors.
- STS AssumeRole gives credentials for 15 min up to 12 h. Use `get-caller-identity` to debug.

## Check yourself

1. An app on EC2 uses the wrong permissions even though the instance profile is correct. What is the most likely cause?
2. What is the difference between `--query` and `--filters` in the CLI?
3. A batch job gets intermittent `ThrottlingException`. What should the code do?
4. Which STS API lets an IAM user get MFA-backed temporary credentials?
5. What does a waiter do, and which API does `table_exists` call?

<details><summary>Answers</summary>

1. Environment variables (or a credentials file) with other keys take precedence over the instance profile in the provider chain.
2. `--query` is a client-side JMESPath projection/filter. `--filters` (where supported) filters server-side.
3. Retry with exponential backoff and jitter (configure the SDK retry mode). Reduce the request rate or raise the quota if it persists.
4. `GetSessionToken` (with `SerialNumber` and `TokenCode`).
5. It polls an API until a resource reaches a state, with delays and a maximum number of attempts. `table_exists` polls `DescribeTable` until the table is ACTIVE.

</details>

## Further reading

- [Credential providers in the AWS SDKs](https://docs.aws.amazon.com/sdkref/latest/guide/standardized-credentials.html)
- [Retry behavior in the AWS SDKs](https://docs.aws.amazon.com/sdkref/latest/guide/feature-retry-behavior.html)
- [Exponential backoff and jitter (AWS Architecture Blog)](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/)
- [AWS STS API reference](https://docs.aws.amazon.com/STS/latest/APIReference/welcome.html)
- [Amazon Q Developer user guide](https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/what-is.html)
