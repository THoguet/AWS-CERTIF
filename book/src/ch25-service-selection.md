# Which service when?

> Decision tables for the "choose the best service" questions. Read the scenario, find the deciding
> requirement in the left column, and you have the answer.

## Compute

| Requirement | Choose |
|---|---|
| Event-driven, short (≤ 15 min), scale to zero, pay per use | **Lambda** |
| Long-running/containerized service, no servers to manage | **ECS on Fargate** |
| Kubernetes required | **EKS** |
| Upload code, get a managed web environment with deployment policies | **Elastic Beanstalk** |
| Simplest container/web app from source or image | **App Runner** |
| Full control of the OS, special hardware, legacy software | **EC2** |
| Run code at CloudFront edge: header rewrites (cheap, sub-ms) / network calls | **CloudFront Functions** / **Lambda@Edge** |

## APIs and front doors

| Requirement | Choose |
|---|---|
| API keys, usage plans, caching, request validation, WAF, private API | **API Gateway REST** |
| Cheapest/fastest HTTP API to Lambda with JWT auth | **API Gateway HTTP API** |
| Real-time bidirectional connections | **API Gateway WebSocket** / **AppSync subscriptions** |
| GraphQL, multiple data sources, offline sync | **AppSync** |
| HTTP routing to containers/instances, path-based | **ALB** |
| One function, one URL, minimal setup | **Lambda function URL** |

## Data stores

| Requirement | Choose |
|---|---|
| Key-value/document at any scale, single-digit ms, serverless | **DynamoDB** |
| Microsecond reads for DynamoDB without code changes | **DAX** |
| Relational, SQL, joins, transactions across tables | **RDS / Aurora** |
| Many Lambda functions connecting to a relational DB | **RDS Proxy** |
| Cache query results, sessions, leaderboards | **ElastiCache (Redis/Valkey)** |
| Durable Redis-compatible primary database | **MemoryDB** |
| Objects, files, static assets, data lake | **S3** |
| Shared POSIX file system for many instances/functions | **EFS** |
| Full-text search | **OpenSearch Service** |
| SQL over files in S3, serverless | **Athena** |

## Integration and messaging

| Requirement | Choose |
|---|---|
| Decouple producer and consumer, buffer spikes, work queue | **SQS standard** |
| Strict ordering per key + deduplication | **SQS FIFO** (MessageGroupId) |
| Push one message to many subscribers (fan-out), email/SMS/mobile push | **SNS** (+ SQS queues per consumer) |
| Route events by content, AWS/SaaS events, schedules, archive/replay | **EventBridge** |
| Real-time ordered stream, multiple consumers, replay | **Kinesis Data Streams** |
| Load streaming data into S3/Redshift/OpenSearch with no code | **Amazon Data Firehose** |
| Multi-step workflow with retries, branching, human approval | **Step Functions (Standard)** |
| Very high-volume short workflows | **Step Functions (Express)** |
| Point-to-point integration source → filter → enrich → target | **EventBridge Pipes** |
| Large message payloads | **S3 + pointer** (claim check / extended client) |

## Security and identity

| Requirement | Choose |
|---|---|
| Credentials for code running on AWS | **IAM role** (instance profile, execution role, task role) |
| Cross-account access | **IAM role + STS AssumeRole** (or a resource-based policy) |
| App users sign up / sign in | **Cognito user pool** |
| App users get AWS credentials to call S3/DynamoDB directly | **Cognito identity pool** |
| Workforce SSO to AWS accounts | **IAM Identity Center** |
| Validate custom tokens in API Gateway | **Lambda authorizer** |
| Encrypt data with an auditable, controllable key | **KMS customer managed key** |
| Encrypt data > 4 KB / client-side | **Envelope encryption** (`GenerateDataKey`, Encryption SDK) |
| Secrets with automatic rotation | **Secrets Manager** |
| Configuration values, hierarchy, cheap | **Parameter Store** (SecureString for secrets) |
| Feature flags, safe config rollout | **AppConfig** |
| Free TLS certificates with auto-renewal for ALB/CloudFront/API Gateway | **ACM** |
| Private certificates / mutual TLS | **AWS Private CA** |
| Temporary access to one S3 object | **S3 presigned URL** |
| Private content through CloudFront | **CloudFront signed URLs / cookies** + OAC |
| Protect APIs from SQL injection/XSS, rate-based blocking | **AWS WAF** |

## Deployment

| Requirement | Choose |
|---|---|
| Infrastructure as code, declarative YAML/JSON | **CloudFormation** |
| Serverless IaC shorthand + local testing | **AWS SAM** |
| IaC in a programming language | **AWS CDK** |
| Deploy one template to many accounts/Regions | **CloudFormation StackSets** |
| Build and test code | **CodeBuild** |
| Deploy to EC2/on-prem/Lambda/ECS with hooks and rollbacks | **CodeDeploy** |
| Orchestrate source → build → test → approve → deploy | **CodePipeline** |
| Private package repository (npm, PyPI, Maven) | **CodeArtifact** |
| Managed Git repositories on AWS | **CodeCommit** (or GitHub via CodeConnections) |
| Front-end hosting with per-branch environments | **Amplify Hosting** |
| Gradual Lambda traffic shifting with alarm rollback | **SAM DeploymentPreference / CodeDeploy** |
| AI code suggestions, unit test generation, security scans in the IDE | **Amazon Q Developer** |

## Observability

| Requirement | Choose |
|---|---|
| Metrics, alarms, dashboards | **CloudWatch** |
| Custom metrics from Lambda without latency | **Embedded Metric Format** |
| Query logs interactively | **CloudWatch Logs Insights** |
| Metric from a log pattern | **Metric filter** |
| Stream logs to another system in real time | **Subscription filter** (Lambda/Kinesis/Firehose) |
| Trace requests across services, find the slow component | **X-Ray** (OpenTelemetry/ADOT) |
| Who made an API call / changed a resource | **CloudTrail** |
| React to API calls or resource state changes | **EventBridge** (+ CloudTrail events) |
| Test endpoints continuously | **CloudWatch Synthetics** |
| Memory/disk metrics on EC2 | **CloudWatch agent** |

## Classic "same goal, different answer" pairs

| Pair | Difference |
|---|---|
| SQS vs SNS | Pull, one consumer per message, persistence vs push, every subscriber, no persistence |
| SNS vs EventBridge | Simple fan-out + filter policies + email/SMS vs rich routing, AWS/SaaS events, schedules, archive/replay |
| Kinesis Data Streams vs Firehose | Real-time custom consumers + replay vs managed delivery, buffered, no replay |
| DAX vs ElastiCache | DynamoDB-only, no code change vs any data, any computed result |
| Multi-AZ vs read replicas | High availability (sync standby) vs read scaling (async) |
| Secrets Manager vs Parameter Store | Rotation, cross-account, $ vs hierarchy, free tier, no rotation |
| User pool vs identity pool | Authentication (JWT) vs AWS credentials |
| Reserved vs provisioned concurrency | Guarantee + cap (free) vs pre-warmed environments (paid) |
| LSI vs GSI | Same PK, at creation, strong reads vs any key, any time, eventual only |
| CloudFormation nested stacks vs exports | Deployed together vs independent stacks sharing values |
| Execution role vs task role (ECS) | Agent: pull image, logs, secrets vs your application's permissions |
| Execution role vs resource policy (Lambda) | What the function can do vs who can invoke it |
| Annotations vs metadata (X-Ray) | Indexed, searchable vs not indexed |
| CloudWatch vs CloudTrail vs X-Ray | Performance metrics/logs vs API audit vs request tracing |
