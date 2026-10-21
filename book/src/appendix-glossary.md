# Glossary

| Term | Meaning |
|---|---|
| **ADOT** | AWS Distro for OpenTelemetry: AWS-supported OpenTelemetry SDKs/collector exporting to X-Ray and CloudWatch |
| **Alias (Lambda)** | Named pointer to a function version, optionally splitting traffic between two versions |
| **AMI** | Amazon Machine Image, the template an EC2 instance boots from |
| **ARN** | Amazon Resource Name: `arn:partition:service:region:account:resource` |
| **ASL** | Amazon States Language, the JSON language of Step Functions state machines |
| **AZ** | Availability Zone: isolated data center(s) within a Region |
| **Blue/green** | Two environments, traffic switched from old (blue) to new (green) at once |
| **Canary** | Shift a small percentage of traffic to the new version first, then the rest |
| **Claim check** | Store a large payload (S3) and send only a reference in the message |
| **Cold start** | Extra latency when Lambda creates and initializes a new execution environment |
| **Concurrency (Lambda)** | Number of invocations running at the same time |
| **CMK** | Customer managed (KMS) key |
| **DLQ** | Dead-letter queue: where failed messages/events go after retries |
| **EMF** | Embedded Metric Format: JSON log lines from which CloudWatch extracts metrics |
| **Envelope encryption** | Encrypt data with a data key, and encrypt the data key with a KMS key |
| **ESM** | Event source mapping: Lambda pollers reading SQS/Kinesis/DynamoDB Streams/Kafka/MQ |
| **Fan-out** | Delivering one message to many consumers (SNS → SQS queues) |
| **GSI / LSI** | Global / local secondary index (DynamoDB) |
| **IaC** | Infrastructure as code (CloudFormation, SAM, CDK) |
| **Idempotent** | Repeating the operation has the same effect as doing it once |
| **IMDS** | EC2 instance metadata service (`169.254.169.254`). IMDSv2 requires a session token |
| **Instance profile** | Container that attaches an IAM role to an EC2 instance |
| **JWT** | JSON Web Token: signed token with claims (Cognito ID and access tokens) |
| **OAC** | Origin Access Control: lets only CloudFront read a private S3 bucket |
| **OIDC / SAML** | Identity federation standards (OpenID Connect / Security Assertion Markup Language) |
| **Partition key** | DynamoDB key hashed to choose the partition. Also Kinesis's shard selector |
| **PHI / PII** | Protected health information / personally identifiable information |
| **PITR** | Point-in-time recovery (DynamoDB: any second of the last 35 days) |
| **Presigned URL** | URL embedding a SigV4 signature, granting one S3 operation until expiry |
| **Provisioned concurrency** | Pre-initialized Lambda environments (no cold starts) |
| **RCU / WCU** | Read / write capacity units (DynamoDB provisioned mode) |
| **Reserved concurrency** | Concurrency guaranteed to, and capped for, one Lambda function |
| **Resource-based policy** | Policy attached to a resource (bucket, queue, key, function), with a Principal |
| **SAM** | Serverless Application Model: CloudFormation transform + CLI |
| **SCP** | Service control policy (AWS Organizations guardrail) |
| **Segment / subsegment** | X-Ray units of work: per service / per downstream call or code block |
| **Shard** | Unit of capacity of a Kinesis data stream |
| **SigV4** | Signature Version 4, the request-signing protocol of AWS APIs |
| **Stage (API Gateway)** | A named deployment of an API (dev, prod) with its own settings and variables |
| **STS** | Security Token Service: issues temporary credentials (AssumeRole...) |
| **TTL** | Time to live: expiry of cache entries, DynamoDB items, DNS records |
| **Visibility timeout** | Time an SQS message stays hidden after being received |
