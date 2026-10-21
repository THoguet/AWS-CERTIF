# DVA-C02 exam guide — map of this repository

This page summarizes the official **AWS Certified Developer – Associate (DVA-C02)** exam guide
(version 2.1, December 2024) and maps every task statement to the book chapters,
awslings exercises and quiz topics of this repository.

> Always check the official sources before booking:
> [exam page](https://aws.amazon.com/certification/certified-developer-associate/) ·
> [exam guide](https://docs.aws.amazon.com/aws-certification/latest/developer-associate-02/developer-associate-02.html) ·
> [revisions](https://docs.aws.amazon.com/aws-certification/latest/developer-associate-02/dva-02-revisions.html)

## ⚠️ Deadline

| Date | Event |
|---|---|
| **30 Nov 2026** | **Last day to take DVA-C02** |
| 27 Oct 2026 | Registration opens for DVA-C03 (the next version) |
| 1 Dec 2026 | DVA-C03 becomes generally available |

Exam slots close to a retirement date fill up quickly, so book early.
DVA-C03 keeps the four domains (AWS announced re-weighted domains and new
AI-assisted development topics). Almost everything in this repo stays valid for C03.

## Exam facts

| | |
|---|---|
| Questions | 65 = 50 scored + 15 unscored (you cannot tell which ones are unscored) |
| Duration | 130 minutes (≈ 2 min per question) |
| Question types | Multiple choice (1 correct answer out of 4) · multiple response (2 or more correct answers out of 5 or more, "Choose TWO") |
| Scoring | Scaled score 100–1000, **pass = 720**. Compensatory: you pass on the total, not per domain. No penalty for wrong answers, so never leave a question blank |
| Price | 150 USD (+ local taxes) |
| Delivery | Pearson VUE test center or online proctoring |
| Validity | 3 years |
| Retake | After a fail, wait 14 days. Each attempt is paid |

**Non-native English speakers:** AWS offers an "ESL +30 minutes" exam accommodation.
Request it in your AWS Certification account **before** you schedule the exam (it applies to
exams booked after it is approved).

## Domains and weights

| Domain | Weight | ≈ scored questions |
|---|---|---|
| 1. Development with AWS Services | 32% | 16 |
| 2. Security | 26% | 13 |
| 3. Deployment | 24% | 12 |
| 4. Troubleshooting and Optimization | 18% | 9 |

`awslings mock` builds 65-question mock exams with the same weights (21/17/16/11 questions).

---

## Domain 1 — Development with AWS Services (32%)

### Task 1.1 Develop code for applications hosted on AWS
- Architectural patterns: event-driven, microservices, monolithic, choreography, orchestration, fan-out
- Idempotency; stateful vs stateless; tightly vs loosely coupled; synchronous vs asynchronous
- Fault-tolerant patterns: retries with exponential backoff and jitter, dead-letter queues, circuit breakers (v2.1)
- Creating, extending and maintaining APIs (request/response transformations, validation rules, overriding status codes)
- Writing and running unit tests (e.g. with AWS SAM); writing code that uses messaging services; data streaming
- Writing code that interacts with AWS services through APIs and SDKs
- v2.1 additions: event-driven patterns with **Amazon EventBridge**, resilient third-party integrations (retry logic, circuit breakers), **Amazon Q Developer** as an AI coding assistant

| Book | Exercises | Quiz topics |
|---|---|---|
| ch03, ch06, ch09, ch10, ch11, ch19 | intro_2, sdk_2, sdk_3, s3_6, lambda_3, lambda_5, sqs_1–4, sns_1, events_1, kinesis_1–3, sfn_1–2, res_1 | sdk, apigw, messaging, streaming, patterns |

### Task 1.2 Develop code for AWS Lambda
- Event source mappings, stateless functions, event-driven architecture, scalability
- Access to private resources in a VPC from Lambda
- Configuration: environment variables, memory, concurrency, timeout, runtime, handler, layers, extensions, triggers, destinations
- Handling the event lifecycle and errors in code (destinations, DLQs); testing; tuning for performance

| Book | Exercises | Quiz topics |
|---|---|---|
| ch05 (+ ch16 for versions and aliases) | lambda_1–8, s3_7, ddb_9 | lambda |

### Task 1.3 Use data stores in application development
- Relational vs non-relational; CRUD; high-cardinality partition keys
- Storage options (file, object, database); consistency models (strong vs eventual)
- Query vs Scan; DynamoDB keys and indexes; caching strategies (write-through, read-through, lazy loading, TTL)
- S3 storage classes and lifecycle management; ephemeral vs persistent storage
- Serializing/deserializing data for persistence; managing data lifecycles; using caching services

| Book | Exercises | Quiz topics |
|---|---|---|
| ch04, ch07, ch08 | s3_1–7, ddb_1–9, cache_1–3, res_2 | s3, dynamodb, caching |

## Domain 2 — Security (26%)

### Task 2.1 Implement authentication and/or authorization
- Identity federation (SAML, OIDC, Amazon Cognito); bearer tokens (JWT, OAuth, AWS STS)
- Cognito user pools vs identity pools; resource-based, service and principal policies
- RBAC, ACLs, least privilege, AWS managed vs customer managed policies
- Programmatic access, authenticated (SigV4) calls, assuming roles, defining permissions

| Book | Exercises | Quiz topics |
|---|---|---|
| ch02, ch03, ch06, ch12 | iam_1–5, sdk_1, sdk_4, apigw_3, cognito_1–3, s3_2, cache_3 | iam, sdk, apigw, cognito |

### Task 2.2 Implement encryption by using AWS services
- Encryption at rest and in transit; certificate management (ACM, AWS Private CA)
- Key protection and rotation; client-side vs server-side encryption
- AWS managed vs customer managed KMS keys; encrypting/decrypting data; cross-account encryption
- Generating certificates and SSH keys for development

| Book | Exercises | Quiz topics |
|---|---|---|
| ch13, ch04 | kms_1–3, s3_4, iam_4 | kms, s3 |

### Task 2.3 Manage sensitive data in application code
- Data classification (PII, PHI); environment variables (and encrypting them)
- Secrets management: Secrets Manager, Systems Manager Parameter Store; secure credential handling
- Sanitizing sensitive data

| Book | Exercises | Quiz topics |
|---|---|---|
| ch14 | secrets_1–4 | secrets |

## Domain 3 — Deployment (24%)

### Task 3.1 Prepare application artifacts to be deployed to AWS
- Accessing configuration data (AWS AppConfig, Secrets Manager, Parameter Store)
- Lambda packaging, layers and configuration; Git-based version control; container images
- Managing dependencies (environment variables, configuration files, container images); organizing files
- Applying resource requirements (memory, cores)

| Book | Exercises | Quiz topics |
|---|---|---|
| ch16, ch18, ch14 | ecs_1, beanstalk_1, lambda_7 | sam, containers, secrets |

### Task 3.2 Test applications in development environments
- Deployment features of AWS services; integration testing with mock endpoints; Lambda versions and aliases
- Testing deployed code; mock integrations for APIs; development endpoints (API Gateway stages)
- Deploying stack updates to existing environments (e.g. a SAM template to another stage)

| Book | Exercises | Quiz topics |
|---|---|---|
| ch19, ch06, ch16 | apigw_1, lambda_8, sam_2 | testing, apigw, sam |

### Task 3.3 Automate deployment testing
- API Gateway stages; branches and actions in CI/CD workflows; automated tests (unit, mock)
- Creating test events (JSON payloads for Lambda, API Gateway, SAM)
- Environments using approved versions (Lambda aliases, image tags, Amplify branches)
- Implementing and deploying IaC templates (SAM, CloudFormation); managing environments (dev/test/prod)

| Book | Exercises | Quiz topics |
|---|---|---|
| ch19, ch17, ch15, ch16 | sam_2, cicd_1, cfn_2 | testing, cicd, cloudformation |

### Task 3.4 Deploy code by using AWS CI/CD services
- Git; manual and automated approvals in CodePipeline; AppConfig and Secrets Manager at deploy time
- CloudFormation, CDK, SAM, CodeArtifact, Amplify, Lambda deployment options; API Gateway stages and custom domains
- Deployment strategies: canary, blue/green, rolling (and all-at-once, linear, immutable)
- Updating IaC templates; deploying versions with a strategy; commits triggering pipelines; rollbacks
- Labels/branches for release management; runtime configuration (stage variables)

| Book | Exercises | Quiz topics |
|---|---|---|
| ch15, ch16, ch17, ch18 | cfn_1–2, sam_1, cicd_1–4, lambda_8, apigw_1 | cloudformation, sam, cicd, containers |

## Domain 4 — Troubleshooting and Optimization (18%)

### Task 4.1 Assist in a root cause analysis
- Logging and monitoring systems; log query languages (CloudWatch Logs Insights); dashboards
- Code analysis tools; common HTTP error codes; common SDK exceptions; X-Ray service maps
- Interpreting metrics, logs and traces; custom metrics (EMF); troubleshooting deployment failures from service logs

| Book | Exercises | Quiz topics |
|---|---|---|
| ch20, ch21, ch22 | cw_2, cw_4, ddb_7 | monitoring, xray, troubleshooting |

### Task 4.2 Instrument code for observability
- Distributed tracing; logging vs monitoring vs observability; structured logging
- Custom, embedded and built-in metrics; notification alerts (quota limits, deployment completions)
- Annotations for tracing; implementing tracing with AWS tools

| Book | Exercises | Quiz topics |
|---|---|---|
| ch20, ch21 | cw_1, cw_3, cw_5, xray_1 | monitoring, xray |

### Task 4.3 Optimize applications by using AWS services and features
- Caching; concurrency; messaging services (SQS, SNS)
- Profiling performance; minimum memory/compute for a workload
- Subscription filter policies; caching content based on request headers

| Book | Exercises | Quiz topics |
|---|---|---|
| ch23, ch08, ch05 | opt_1–2, lambda_2, lambda_6, sns_1, sdk_5 | optimization, caching, lambda |

---

## In-scope services

Grouped like the guide's appendix (v2.0 list, with the v2.1 changes noted). The list is
**not exhaustive**, and services outside it can still show up as wrong answers.

| Category | Services |
|---|---|
| Analytics | Athena · Kinesis (Data Streams, Firehose) · OpenSearch Service |
| Application integration | AppSync · EventBridge · SNS · SQS · Step Functions |
| Compute | EC2 · Elastic Beanstalk · Lambda · SAM |
| Containers | ECR · ECS · EKS (· AWS Copilot, reported removed in v2.1) |
| Database | Aurora · DynamoDB (+ DAX) · ElastiCache · MemoryDB · RDS |
| Developer tools | Amplify · CloudShell · CodeArtifact · CodeBuild · CodeCommit · CodeDeploy · CodePipeline · X-Ray · Amazon Q Developer (v2.1, replaces CodeWhisperer) (· Cloud9, CodeStar: no longer offered to new customers · CodeGuru: reported removed in v2.1) |
| Management & governance | AppConfig · CDK · CloudFormation · CloudTrail · CloudWatch · CloudWatch Logs · AWS CLI · Systems Manager |
| Networking & content delivery | API Gateway · CloudFront · Elastic Load Balancing · Route 53 · VPC |
| Security, identity & compliance | ACM · AWS Private CA · Cognito · IAM · KMS · Secrets Manager · STS · WAF |
| Storage | EBS · EFS · S3 · S3 Glacier |

## Known changes since the exam guide was written

The exam was written against the state of AWS in late 2024. Questions may lag behind these changes:

| Change | What to answer in the exam |
|---|---|
| SQS max message size 256 KB → **1 MiB** (Aug 2025). Lambda async payload 256 KB → **1 MB** (Oct 2025). EventBridge events up to 1 MB. SNS: 1 MiB **opt-in** per topic (`MaximumMessageSize`, Sep 2026), 256 KiB by default | Questions written with 256 KB in mind still expect the **claim-check pattern** (payload in S3, pointer in the message / SQS Extended Client Library) for large payloads |
| CodeCommit closed to new customers (Jul 2024), **back to GA** (Nov 2025) | Still in scope. Know repositories, triggers, IAM/Git credentials |
| X-Ray SDKs/daemon in **maintenance mode** since Feb 2026 (end of support Feb 2027). OpenTelemetry/ADOT recommended | Exam vocabulary stays X-Ray: segments, subsegments, annotations vs metadata, sampling, daemon on UDP 2000 |
| API Gateway REST integration timeout can exceed 29 s (Regional/private APIs, quota increase, Jun 2024) | "504 after ~29 s" still points to the integration timeout. The fix is usually to go asynchronous |
| Amazon CodeWhisperer → **Amazon Q Developer** | Q Developer: AI code suggestions, chat, security scans, unit test generation |
| Cloud9 and CodeStar closed to new customers (2024) | Rarely the right answer today |
