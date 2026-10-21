# Secrets and configuration

> **In this chapter**
> - Data classification and secure credential handling
> - AWS Secrets Manager: secrets, rotation, caching, cross-account access
> - Systems Manager Parameter Store: hierarchies, SecureString, tiers, references
> - AWS AppConfig: feature flags and safe configuration deployments
> - Environment variables, dynamic references in templates, sanitizing logs
>
> **Exam weight**: Domain 2 Task 2.3 (sensitive data), Domain 3 Tasks 3.1/3.4 (accessing
> configuration data from AppConfig, Secrets Manager, Parameter Store)
> · **Exercises**: `secrets_1`–`secrets_4` · **Quiz**: `uv run awslings quiz secrets`

## Classify, then protect

- **Data classification**: label data by sensitivity. **PII** (personally identifiable information:
  names, emails, addresses, IDs), **PHI** (protected health information), financial data (cards),
  credentials and keys, public data. The label decides encryption, access, retention and logging rules.
- **Amazon Macie** discovers sensitive data (PII) in S3 buckets with machine learning.
- **Secure credential handling**:
  - never hard-code secrets in code, images, templates or Git (scan repositories),
  - prefer **IAM roles** (no secret at all) over static keys,
  - store unavoidable secrets (DB passwords, third-party API keys) in **Secrets Manager** or **Parameter Store SecureString**,
  - fetch them at runtime with least-privilege permissions, cache them briefly, rotate them,
  - never log them (and mask PII in logs).

## AWS Secrets Manager

- Stores secrets (strings or JSON, up to 64 KB), **encrypted with KMS** (AWS managed `aws/secretsmanager` or a CMK).
- **Automatic rotation** by a Lambda function on a schedule (rate or cron):
  - **managed rotation** / ready-made rotation functions for **RDS, Aurora, Redshift, DocumentDB**,
  - your own rotation function for anything else, implementing **4 steps**: `createSecret` (new version labeled
    **AWSPENDING**), `setSecret` (apply it to the database/service), `testSecret` (log in with it), `finishSecret`
    (move **AWSCURRENT** to the new version; the old one becomes **AWSPREVIOUS**) (exercise `secrets_3`),
  - strategies: single user (change the password) or alternating users (two users, zero downtime).
- **Versions and staging labels**: `AWSCURRENT`, `AWSPENDING`, `AWSPREVIOUS`, custom labels.
- **Resource policies** for **cross-account** access (plus the KMS key policy: use a CMK, not the AWS managed key).
- **Multi-Region replication** of secrets (DR, multi-Region apps).
- Integrations: RDS (`ManageMasterUserPassword`), ECS/EKS (inject secrets into containers), Lambda (the Parameters and
  Secrets **extension**), CloudFormation **dynamic references**, CodeBuild (`env.secrets-manager`).
- Pricing: ~**$0.40 per secret per month** + $0.05 per 10,000 API calls.

```python
secret = json.loads(sm.get_secret_value(SecretId="prod/db")["SecretString"])
```

**Cache it**: calling `GetSecretValue` on every invocation adds latency and cost. Use a caching client
(aws-secretsmanager-caching), the **AWS Parameters and Secrets Lambda Extension** (local HTTP cache on
`localhost:2773`), or a small TTL cache in the execution environment (exercise `secrets_2`).

## Systems Manager Parameter Store

- Stores configuration and secrets as parameters in a **hierarchy**: `/shop/prod/db/host`, `/shop/prod/db/password`.
- Types: `String`, `StringList` (comma-separated), **`SecureString`** (encrypted with KMS: AWS managed `aws/ssm` or a CMK).
- **Tiers**:

| | Standard | Advanced |
|---|---|---|
| Max value size | **4 KB** | **8 KB** |
| Parameters per account/Region | 10,000 | 100,000 |
| Parameter policies (expiration, notifications) | ❌ | ✅ |
| Price | **Free** (standard throughput) | Per parameter per month |

- **Versions** and **labels** (`/shop/prod/db/host:3`, `:prod-label`). History of changes.
- `GetParametersByPath` (with `Recursive=True`, `WithDecryption=True`, **paginated**) loads a subtree
  (exercise `secrets_1`). Reading a SecureString decrypted needs **`kms:Decrypt`** on the key.
- **Public parameters**, e.g. the latest Amazon Linux AMI id:
  `/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64`.
- Can **reference Secrets Manager**: `/aws/reference/secretsmanager/<secret-name>`.
- **No built-in rotation** (that is Secrets Manager's job). EventBridge events on parameter changes.

### Secrets Manager vs Parameter Store

| Need | Choose |
|---|---|
| Automatic **rotation** (DB credentials), cross-account sharing, replication | **Secrets Manager** |
| App configuration, feature values, hierarchy, **free**, simple secrets without rotation | **Parameter Store** (SecureString for secrets) |

> **Exam tip** — "Store database credentials and **rotate them automatically** with the least effort" →
> **Secrets Manager** (managed rotation for RDS). "Store configuration values (some encrypted) cheaply,
> organized per environment" → **Parameter Store**.

## AWS AppConfig

Part of Systems Manager. Manages **dynamic configuration and feature flags**, deployed **safely** without redeploying code:

- **Applications → environments → configuration profiles** (feature flags or freeform JSON/YAML/text,
  stored in AppConfig, S3, Parameter Store, Secrets Manager...).
- **Validators** (JSON Schema or a Lambda function) reject bad configurations **before** deployment.
- **Deployment strategies**: linear or exponential rollout over time, with **bake time** and **automatic
  rollback on CloudWatch alarms** (e.g. `AppConfig.Linear50PercentEvery30Seconds`, `AllAtOnce`).
- Clients poll for configuration. Lambda uses the **AppConfig agent Lambda extension** (local cache).

> **Exam tip** — "Turn a feature on for 10% of users, roll back automatically if errors rise, without a code
> deployment" → **AppConfig feature flags** with a deployment strategy and alarms.

## Environment variables

- Good for **non-secret** configuration (table names, stage, log level). Same artifact, different settings per environment.
- Lambda encrypts environment variables **at rest** with KMS (AWS managed key, or your CMK for control/audit).
  Anyone with `lambda:GetFunctionConfiguration` can read them in clear text, so **secrets don't belong there**.
  If you must, use **encryption helpers** (encrypt the value client-side with a CMK and decrypt in code), or better,
  store the **name** of a secret and fetch it at runtime.
- Lambda limit: **4 KB** for all variables. ECS task definitions: `environment` for plain values, **`secrets`** (with
  `valueFrom` = Secrets Manager or Parameter Store ARN) for sensitive ones, injected at container start (exercise `ecs_1`).

## Secrets in infrastructure as code

CloudFormation **dynamic references** resolve values at deploy time without putting them in the template:

```yaml
MasterUserPassword: '{{resolve:secretsmanager:prod/db:SecretString:password}}'
DbHost: '{{resolve:ssm:/shop/prod/db/host}}'
ApiKey: '{{resolve:ssm-secure:/shop/prod/api-key}}'      # SecureString (supported by some resource properties)
```

Template **parameters** with `NoEcho: true` mask values in the console and API output, but dynamic references
are better. CodeBuild `env` supports `parameter-store` and `secrets-manager` mappings (exercise `cicd_1`).

## Sanitizing sensitive data

- **Logs**: never log secrets, tokens, full card numbers, passwords. Mask PII (emails, phone numbers)
  (exercise `secrets_4`). Structured logging makes masking systematic.
- **CloudWatch Logs data protection policies** detect and **mask** sensitive data (emails, credentials, card
  numbers...) at ingestion. Only principals with `logs:Unmask` can see the original.
- API Gateway execution logs with full request/response data can leak secrets, so enable them carefully.
- Return generic error messages to clients, and keep details in protected logs.
- Remove sensitive fields before sending events to third parties (EventBridge input transformers, Lambda enrichment).

## Hands-on

| Exercise | Skill |
|---|---|
| `secrets_1` | Parameter Store hierarchy, SecureString, GetParametersByPath (recursive, decrypted, paginated) |
| `secrets_2` | A TTL cache for Secrets Manager values |
| `secrets_3` | A complete rotation function (4 steps, staging labels, idempotency) |
| `secrets_4` | Masking secrets and PII before logging |

## Summary

- Classify data (PII, PHI...) → choose controls. Roles over secrets. Secrets in Secrets Manager or SecureString, never in code/logs.
- Secrets Manager: KMS encryption, **rotation** (4 steps, AWSPENDING → AWSCURRENT → AWSPREVIOUS), cross-account, replication, ~$0.40/secret.
- Parameter Store: hierarchy, String/StringList/SecureString, Standard (free, 4 KB) vs Advanced (8 KB, policies). No rotation.
- AppConfig: feature flags and config with validators, gradual deployment, automatic rollback.
- Lambda env vars: 4 KB, encrypted at rest but readable by whoever can read the configuration. Store secret names, not secret values.

## Check yourself

1. An RDS password must rotate every 30 days with no custom code. Which service?
2. What permission besides `ssm:GetParameter` is needed to read a SecureString with `WithDecryption=True`?
3. During rotation, which staging label marks the new secret version before it is validated?
4. A team wants to enable a new checkout flow for 10% of users and roll back automatically on errors. Which service?
5. Why is a database password in a Lambda environment variable a bad idea even though variables are encrypted?

<details><summary>Answers</summary>

1. **Secrets Manager** with managed/automatic rotation for RDS.
2. `kms:Decrypt` on the KMS key that encrypts the parameter.
3. **AWSPENDING** (it becomes AWSCURRENT in `finishSecret`).
4. **AWS AppConfig** (feature flag + gradual deployment strategy + CloudWatch alarm rollback).
5. Anyone allowed to read the function configuration sees it in clear text, it cannot rotate, and it often leaks in logs or IaC templates.

</details>

## Further reading

- [Secrets Manager user guide](https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html) and [rotation](https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotating-secrets.html)
- [Parameter Store](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html)
- [AWS AppConfig](https://docs.aws.amazon.com/appconfig/latest/userguide/what-is-appconfig.html)
- [Using Secrets Manager secrets in Lambda (extension)](https://docs.aws.amazon.com/secretsmanager/latest/userguide/retrieving-secrets_lambda.html)
- [CloudFormation dynamic references](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/dynamic-references.html)
