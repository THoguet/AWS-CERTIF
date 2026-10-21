# SAM and serverless deployments

> **In this chapter**
> - AWS SAM templates: the transform, Globals, serverless resource types, events, policy templates, connectors
> - The SAM CLI: build, local testing, deploy, sync, pipelines
> - Packaging Lambda code: zip archives, layers, container images
> - Lambda versions and aliases, weighted aliases
> - Safe deployments: canary and linear traffic shifting with CodeDeploy, alarms and hooks
> - Amplify Hosting and the Serverless Application Repository
>
> **Exam weight**: Domain 3 Tasks 3.1–3.4 (packaging, aliases, IaC, deployment strategies, rollbacks)
> · **Exercises**: `sam_1`, `lambda_8` · **Quiz**: `uv run awslings quiz sam`

## AWS SAM templates

SAM (Serverless Application Model) is a **CloudFormation transform**: shorthand resource types expand into
regular CloudFormation at deploy time (so you need `CAPABILITY_AUTO_EXPAND` / `CAPABILITY_IAM`).

```yaml
AWSTemplateFormatVersion: "2010-09-09"
Transform: AWS::Serverless-2016-10-31          # ← makes it a SAM template

Globals:                                         # defaults for every function/API
  Function:
    Runtime: python3.12
    Timeout: 10
    Tracing: Active
    Architectures: [arm64]
    Environment:
      Variables: {LOG_LEVEL: INFO}

Resources:
  OrdersFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: app.handler
      CodeUri: src/                              # local folder; sam build/package uploads it
      Policies:                                   # SAM policy templates (least privilege, scoped)
        - DynamoDBCrudPolicy: {TableName: !Ref OrdersTable}
      Environment:
        Variables: {TABLE_NAME: !Ref OrdersTable}
      Events:
        Api:   {Type: Api, Properties: {Path: /orders, Method: get}}           # creates an API Gateway REST API
        Queue: {Type: SQS, Properties: {Queue: !GetAtt OrdersQueue.Arn, BatchSize: 10,
                                        FunctionResponseTypes: [ReportBatchItemFailures]}}
      AutoPublishAlias: live
      DeploymentPreference:
        Type: Canary10Percent5Minutes
        Alarms: [!Ref ErrorsAlarm]
        Hooks: {PreTraffic: !Ref PreTrafficCheck}

  OrdersTable:
    Type: AWS::Serverless::SimpleTable           # DynamoDB table with a simple primary key
  OrdersQueue:
    Type: AWS::SQS::Queue                         # plain CloudFormation resources work too
```

**Serverless resource types**: `Function`, `Api` (REST), `HttpApi`, `SimpleTable`, `LayerVersion`,
`StateMachine`, `Application` (nested app from the Serverless Application Repository), `GraphQLApi`,
and **`Connector`** (declares "function X writes to table Y" and SAM generates the IAM permissions).

**Event sources** on functions: `Api`, `HttpApi`, `S3`, `SQS`, `SNS`, `Kinesis`, `DynamoDB`,
`EventBridgeRule`, `Schedule` / `ScheduleV2` (EventBridge Scheduler), `CloudWatchLogs`, `Cognito`, `MSK`...
SAM creates the trigger, the permissions and the event source mapping for you.

**Policy templates** (scoped to one resource): `DynamoDBCrudPolicy`, `DynamoDBReadPolicy`,
`S3ReadPolicy`, `S3CrudPolicy`, `SQSPollerPolicy`, `SQSSendMessagePolicy`, `SNSPublishMessagePolicy`,
`LambdaInvokePolicy`, `StepFunctionsExecutionPolicy`, `SSMParameterReadPolicy`, `KMSDecryptPolicy`...

## The SAM CLI

| Command | Does |
|---|---|
| `sam init` | Scaffold a project from templates |
| `sam build` | Install dependencies, prepare artifacts in `.aws-sam/` (`--use-container` for native deps) |
| `sam local invoke Fn -e event.json` | Run a function locally in a Docker container with an event |
| `sam local start-api` | Local API Gateway emulation on `localhost:3000` |
| `sam local start-lambda` | Local Lambda endpoint for SDK/integration tests |
| `sam local generate-event s3 put` | Sample events (S3, SQS, API Gateway, DynamoDB...) to test with |
| `sam validate --lint` | Validate the template (cfn-lint) |
| `sam deploy --guided` | Package + deploy, saving answers in **`samconfig.toml`** (environments with `--config-env prod`) |
| `sam sync --watch` | Fast incremental deploys while developing (dev stacks only) |
| `sam logs -n Fn --tail`, `sam traces` | CloudWatch logs and X-Ray traces from the terminal |
| `sam pipeline init --bootstrap` | Generate a CI/CD pipeline (CodePipeline, GitHub Actions, GitLab...) with per-stage roles and buckets |
| `sam delete` | Delete the stack |

> **Exam tip** — "Test a Lambda function and API locally before deploying" → **`sam local invoke`** /
> **`sam local start-api`** (Docker). "Deploy the same SAM template to a staging environment" →
> `sam deploy --config-env staging` (parameter overrides / separate stack name).

## Packaging Lambda code

| Option | How | Limits / notes |
|---|---|---|
| **Zip archive** | Code + dependencies at the root (Python: `pip install -t .`) | **50 MB zipped** direct upload, **250 MB unzipped** (including layers). Upload through S3 above 50 MB |
| **Layers** | Shared libraries, custom runtimes, data. Extracted to `/opt` (Python: put packages under `python/`) | Up to **5 layers** per function. Versioned, shareable across accounts |
| **Container image** | `FROM public.ecr.aws/lambda/python:3.12`, push to **ECR**, `PackageType: Image` | Up to **10 GB**. The image must implement the Lambda Runtime API (AWS base images include the runtime interface client). Test locally with the Runtime Interface Emulator |

- Build dependencies for the right **architecture** (x86_64 vs arm64) and OS (Amazon Linux). `sam build --use-container` helps.
- Keep packages small: faster deploys and cold starts. Exclude tests and dev dependencies.
- Configuration does not belong in the artifact. Use environment variables, Parameter Store, AppConfig (chapter 14).

## Versions and aliases

- **`$LATEST`**: the mutable working copy.
- **Version** (`1`, `2`, ...): `PublishVersion` freezes code + configuration. Immutable, with its own ARN
  (`...:function:orders:7`).
- **Alias** (`live`, `beta`): a named pointer to a version, with an ARN (`...:function:orders:live`).
  Point event sources, API Gateway integrations and clients at the **alias**: releasing means
  moving the alias, and **rollback is instant**.
- **Weighted alias**: an alias sends a percentage of traffic to a second version:

```python
lam.update_alias(FunctionName="orders", Name="live", FunctionVersion="6",
                 RoutingConfig={"AdditionalVersionWeights": {"7": 0.1}})   # 90% v6, 10% v7
```

- Provisioned concurrency and SnapStart apply to versions/aliases, not `$LATEST`.
- With API Gateway stage variables, `dev`/`prod` stages can target aliases `dev`/`prod` (chapter 6).

## Safe deployments: traffic shifting with CodeDeploy

With `AutoPublishAlias` + `DeploymentPreference`, every code change publishes a new version, and
**CodeDeploy** shifts the alias's traffic gradually:

| Type | Behavior |
|---|---|
| `Canary10Percent5Minutes` (also 10, 15, 30 minutes) | 10% to the new version, wait, then 100% |
| `Linear10PercentEvery1Minute` (also 2, 3, 10 minutes) | +10% at each interval until 100% |
| `AllAtOnce` | Immediate switch |

- **Alarms** (CloudWatch: errors, latency...) during the deployment → **automatic rollback** (the alias goes back to the old version).
- **Hooks**: `PreTraffic` and `PostTraffic` Lambda functions run validation tests before and after the
  shift. They report back with `codedeploy:PutLifecycleEventHookExecutionStatus` (Succeeded/Failed).
- The same mechanism exists in CodeDeploy for ECS (blue/green with canary/linear configs, chapter 17).

> **Exam tip** — "Gradually shift traffic to a new Lambda version and roll back automatically if errors
> increase" → **SAM `AutoPublishAlias` + `DeploymentPreference` (Canary/Linear) + CloudWatch alarms** (CodeDeploy).

## Multiple environments

- **One template, several stacks**: parameters (`Env`), `samconfig.toml` environments, stage-specific
  mappings. Best practice: **separate AWS accounts** per environment (dev/test/prod) with a pipeline promoting
  the **same artifact**.
- API Gateway stages + Lambda aliases for lightweight environments within one stack.
- Approved versions for integration tests: test against a specific **alias / image tag / Amplify branch**, then promote.

## Amplify Hosting and the Serverless Application Repository

- **AWS Amplify**: hosting + CI/CD for web front ends (React, Next.js, Vue...) connected to a Git repository.
  **Each branch gets its own environment** (`main` → prod, `dev` → dev), with **pull request previews**, custom domains
  and HTTPS. Amplify Gen 2 defines backends (auth, data, storage, functions) in TypeScript (CDK underneath).
  > **Exam tip** — "Front-end team wants each Git branch deployed to its own environment automatically" → **Amplify Hosting**.
- **Serverless Application Repository (SAR)**: publish, share and deploy SAM applications (public or private), referenced
  with `AWS::Serverless::Application`.

## Hands-on

| Exercise | Skill |
|---|---|
| `sam_1` | A complete SAM template: Globals, policy templates, events, canary deployment (+ cfn-lint) |
| `lambda_8` | Publish versions, weighted alias canary, promotion |

Optional lab: `labs/lab01-serverless-api` deploys a SAM app with a canary deployment and alarms.

## Summary

- SAM = a CloudFormation transform: `AWS::Serverless::*` types, Globals, events, policy templates, connectors.
- SAM CLI: `build`, `local invoke/start-api`, `generate-event`, `deploy --guided` (samconfig.toml), `sync`, `pipeline`.
- Zip (50 MB zipped / 250 MB unzipped with ≤ 5 layers) or container image (10 GB, from ECR).
- Versions are immutable, aliases are movable pointers (weighted for canaries). Event sources should target aliases.
- `AutoPublishAlias` + `DeploymentPreference` = CodeDeploy canary/linear shifting with alarm rollback and Pre/PostTraffic hooks.

## Check yourself

1. Which two SAM properties enable gradual traffic shifting for a function?
2. A Python dependency with native code works locally on a Mac but crashes on Lambda. How do you build it properly?
3. Why should an SQS event source mapping point to an alias rather than `$LATEST`?
4. What does a `PreTraffic` hook do, and how does it report its result?
5. A function's deployment package is 3 GB because of an ML model. Options?

<details><summary>Answers</summary>

1. `AutoPublishAlias` and `DeploymentPreference`.
2. Build for Amazon Linux and the right architecture: `sam build --use-container` (or build in a Lambda-compatible Docker image), or use a container image.
3. So that releases and rollbacks happen by moving the alias, without reconfiguring the trigger. `$LATEST` changes as soon as code is updated.
4. It runs tests against the new version before traffic shifts, then calls `PutLifecycleEventHookExecutionStatus` with Succeeded or Failed (Failed triggers a rollback).
5. A **container image** (up to 10 GB), or load the model at runtime from S3/EFS (EFS mounted on the function).

</details>

## Further reading

- [AWS SAM developer guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html)
- [SAM policy templates](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-policy-templates.html)
- [Deploying serverless applications gradually](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/automating-updates-to-serverless-apps.html)
- [Lambda versions](https://docs.aws.amazon.com/lambda/latest/dg/configuration-versions.html) and [aliases](https://docs.aws.amazon.com/lambda/latest/dg/configuration-aliases.html)
- [Lambda container images](https://docs.aws.amazon.com/lambda/latest/dg/images-create.html)
