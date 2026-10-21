# Troubleshooting playbook

> **In this chapter**
> - A root-cause-analysis method
> - HTTP status codes and SDK exceptions you must recognize instantly
> - Symptom → cause → fix tables for Lambda, API Gateway, DynamoDB, SQS, S3, Kinesis, Cognito
> - Troubleshooting deployments: CloudFormation, CodeBuild, CodeDeploy, CodePipeline, Beanstalk, ECS
> - The toolbox: Logs Insights, X-Ray, CloudTrail, policy simulator, decode-authorization-message
>
> **Exam weight**: Domain 4 Task 4.1 (debugging, interpreting metrics/logs/traces, HTTP codes, SDK
> exceptions, deployment failures) · **Quiz**: `uv run awslings quiz troubleshooting`

## A method

1. **Scope** — Who is affected (one user, a tenant, everyone)? Which Region? Since when?
2. **What changed?** — Deployments, configuration, traffic, quotas, dependencies (AWS Health Dashboard).
3. **Signals** — metrics first (where and when), then **traces** (which component), then **logs** (why).
4. **Hypothesis → test → fix**, then **prevent** it from happening again: an alarm, a test, a guardrail.

## HTTP status codes

| Code | Meaning | Typical AWS cause |
|---|---|---|
| 400 | Bad request | Validation error, malformed parameters, `ValidationException` |
| 401 | Unauthenticated | Missing/expired/invalid token (Cognito/Lambda authorizer) |
| 403 | Forbidden | IAM/resource policy deny, WAF, presigned URL expired. API Gateway: **unknown path** ("Missing Authentication Token") |
| 404 | Not found | Wrong resource/key/stage |
| 409 | Conflict | Concurrent modification, resource in use |
| 413 | Payload too large | Request exceeds a service limit (e.g. Lambda 6 MB synchronous payload) |
| 429 | Too many requests | **Throttling**, quota exceeded → backoff and retry, raise limits |
| 500 | Internal error | Integration misconfiguration (e.g. API Gateway cannot invoke Lambda), service error |
| 502 | Bad gateway | Malformed Lambda proxy response, or an unhandled exception in Lambda behind API Gateway/ALB |
| 503 | Service unavailable | Overload (S3 `SlowDown`), no healthy targets behind an ALB |
| 504 | Gateway timeout | Backend slower than the integration/idle timeout (API Gateway 29 s default, ALB idle timeout) |

**Rule**: 4xx → fix the request or permissions (do not blindly retry). 429/5xx → retry with exponential backoff and jitter.

## SDK exceptions

| Exception | Meaning / fix |
|---|---|
| `AccessDenied(Exception)`, `UnauthorizedOperation` | Not allowed by policies. Check identity, resource and KMS key policies, SCPs, boundaries. EC2 returns an **encoded message**: `aws sts decode-authorization-message` |
| `UnrecognizedClientException`, `InvalidClientTokenId` | Unknown access key (wrong keys, deleted user) |
| `SignatureDoesNotMatch` | Wrong secret key or clock skew |
| `ExpiredToken(Exception)` | Temporary credentials expired. Refresh them (roles do this automatically) |
| `ThrottlingException`, `TooManyRequestsException`, `RequestLimitExceeded`, `SlowDown` | Rate limits → backoff + jitter, reduce request rate, request quota increase |
| `ProvisionedThroughputExceededException` | DynamoDB/Kinesis capacity → backoff, more capacity/shards, better key |
| `ConditionalCheckFailedException` | A DynamoDB condition failed. Expected with optimistic locking/idempotency |
| `TransactionCanceledException` | A transaction was cancelled. Read `CancellationReasons` |
| `ResourceNotFoundException` | Wrong name/ARN or **wrong Region** in the client |
| `ResourceInUseException`, `ResourceConflictException` | The resource is being created/updated, or the name is taken |
| `ValidationException` | Bad parameters: DynamoDB reserved word without `#placeholder`, key schema mismatch, float instead of Decimal (boto3 raises a `TypeError` before the call) |
| `LimitExceededException` | A service quota is reached (e.g. too many tables, concurrent executions, open shards) |
| `KMSAccessDeniedException`, `DisabledException`, `InvalidCiphertextException` | KMS: missing permission/key policy, key disabled, wrong encryption context or corrupted ciphertext |
| `RequestEntityTooLargeException` | Payload above the service limit (Lambda invoke payload, API Gateway 10 MB...) |

## Symptom → cause → fix

### Lambda

| Symptom | Likely cause | Fix |
|---|---|---|
| `Task timed out after 3.00 seconds` | Default 3 s timeout, slow dependency, **VPC function without NAT/endpoint** calling AWS APIs | Raise the timeout, set SDK timeouts, add a NAT gateway or VPC endpoints |
| `Runtime exited ... signal: killed`, `Max Memory Used` = `Memory Size` | Out of memory | Increase memory (also adds CPU) |
| `Runtime.ImportModuleError` / `Unable to import module` | Wrong handler name, package structure (deps not at the zip root), wrong architecture/native deps | Fix the handler string, rebuild with `sam build --use-container` |
| 429 for callers, `Throttles` metric > 0 | Concurrency limit (account or reserved) | Raise the quota, adjust reserved concurrency, reduce duration |
| Latency spikes on the first requests | Cold starts | Provisioned concurrency, SnapStart, smaller packages |
| S3/SNS/EventBridge never triggers the function | Missing **resource-based policy** (invoke permission) or wrong filter | `lambda add-permission`, check event configuration |
| Function cannot write to DynamoDB/S3 | **Execution role** missing permissions | Add least-privilege permissions to the role |
| Async events lost | Retries exhausted, no DLQ/destination, `AsyncEventsDropped` | Configure an on-failure destination/DLQ, fix errors |
| `IteratorAge` keeps growing (Kinesis/DynamoDB Streams) | Consumer too slow or a poison batch blocking the shard | Bisect on error, max retries/age, on-failure destination, parallelization factor, more shards |
| Same SQS messages processed several times | Visibility timeout < processing time, whole batch failing | Visibility timeout ≥ 6× function timeout, partial batch responses, idempotency |

### API Gateway

| Symptom | Cause | Fix |
|---|---|---|
| 502 | Malformed proxy response or Lambda error | Return `{statusCode, headers, body:string}`, handle exceptions |
| 504 after ~29 s | Integration timeout | Make it asynchronous (SQS/Step Functions + 202), optimize the backend |
| 500 "Invalid permissions on Lambda function" | API Gateway lacks invoke permission (per alias with stage variables) | `lambda add-permission` with the right `SourceArn` (and qualifier) |
| CORS error in the browser | Missing `Access-Control-Allow-*` headers (OPTIONS and/or the Lambda proxy response) | Enable CORS + return headers from Lambda |
| High `Latency` but low `IntegrationLatency` | Time spent in API Gateway (authorizer, mapping), or authorizer cold starts | Cache authorizer results, simplify mappings |
| 429 | Account/stage/method throttling or usage plan limits | Raise limits, usage plans per client, retries |

### DynamoDB

| Symptom | Cause | Fix |
|---|---|---|
| Throttling with low average utilization | **Hot partition key** | Higher-cardinality key, write sharding |
| Writes throttled on the table while the table has capacity | **GSI** under-provisioned (back-pressure) | Give the GSI enough capacity or use on-demand |
| Scan very slow and expensive | Full table reads | Query with a better key/GSI, avoid Scan, parallel scan for batch jobs |
| `ValidationException: Attribute name is a reserved keyword` | Reserved word in an expression | `ExpressionAttributeNames` (`#s`) |
| Stale reads right after a write | Eventually consistent read | `ConsistentRead=True` (not on GSIs) |
| Items missing after BatchWriteItem | `UnprocessedItems` ignored | Retry them with backoff |
| `ItemCollectionSizeLimitExceededException` | An LSI item collection reached 10 GB | Redesign the keys, use a GSI |

### SQS, S3, Kinesis, Cognito

| Symptom | Cause | Fix |
|---|---|---|
| SQS: `ApproximateAgeOfOldestMessage` growing | Consumers too slow/few | Scale consumers on backlog, batch processing |
| SQS: many empty receives, high cost | Short polling | Long polling (`WaitTimeSeconds` up to 20) |
| SQS: messages pile up in the DLQ | Poison messages / consumer bug | Fix, then redrive from the DLQ |
| S3: 403 on GetObject although IAM allows it | Bucket policy deny, **KMS key policy** (SSE-KMS), Object Ownership/ACLs, Block Public Access, expired presigned URL | Check every layer, CloudTrail for the denied call |
| S3: 503 SlowDown | Request rate too high on a prefix | Backoff, spread keys across prefixes |
| S3: event notifications never arrive | Destination policy does not allow S3, overlapping/mismatched prefix/suffix | Queue/topic/function resource policy, fix filters |
| Kinesis: `ProvisionedThroughputExceededException` | Hot shard or too few shards | Better partition key, split shards/on-demand, backoff |
| Cognito: `NotAuthorizedException` | Wrong credentials, expired refresh token, missing `SECRET_HASH` for a client with a secret | Check the client config. Public clients should have no secret |
| Cognito: `UserNotConfirmedException` | User never confirmed sign-up | Confirmation flow or pre sign-up auto-confirm |

## Troubleshooting deployments

| Tool | Where to look | Classic failures |
|---|---|---|
| **CloudFormation** | Stack **Events** tab: the **first** `CREATE_FAILED`/`UPDATE_FAILED` event is usually the root cause | Missing `CAPABILITY_IAM`/`AUTO_EXPAND`. Resource name already exists. Insufficient permissions of the caller/service role. `DELETE_FAILED` for a non-empty S3 bucket. `UPDATE_ROLLBACK_FAILED` (fix, then *continue update rollback*). Custom resource never responding (stack waits until timeout) |
| **CodeBuild** | Build logs (CloudWatch/S3), phase details | buildspec YAML errors, missing permissions in the service role, Docker builds without **privileged mode**, VPC builds without NAT (no internet for dependencies) |
| **CodeDeploy** | Deployment events per instance, agent logs (`/var/log/aws/codedeploy-agent/`) | Agent not running, instance profile cannot read the S3 revision, hook script failing/timing out, **`ApplicationStop` script of the previous revision broken**, files already exist |
| **CodePipeline** | Execution details per action | Artifact bucket/KMS permissions (especially cross-account), wrong artifact names, approval timed out (7 days) |
| **Elastic Beanstalk** | Environment events, health, `eb logs` | Bad `.ebextensions`, application failing health checks, insufficient capacity, platform hook errors |
| **ECS** | **Stopped task reason**, service events, container logs | `CannotPullContainerError` (execution role, image tag, no route to ECR: NAT/VPC endpoints), essential container exited, failing ALB health checks, invalid CPU/memory combination |

## Toolbox

| Question | Tool |
|---|---|
| What is failing, where, since when? | CloudWatch metrics, dashboards, alarms |
| Which component is slow or failing in a request? | **X-Ray** trace map and traces |
| What exactly happened in the code? | **CloudWatch Logs Insights** queries, Live Tail |
| Who changed what? Which call was denied? | **CloudTrail** event history / Lake |
| Why is this principal denied? | IAM policy simulator, **Access Analyzer**, `aws sts get-caller-identity`, `aws sts decode-authorization-message` |
| Network path blocked? | VPC Flow Logs, Reachability Analyzer, security groups/NACLs |
| Is AWS having an issue? | AWS Health Dashboard (and Health events in EventBridge) |
| Help reading an error / code | Amazon Q Developer (console error diagnosis, code explanations, security scans) |

## Summary

- Method: scope → recent changes → metrics → traces → logs → fix → prevent.
- 4xx = fix the request/permissions. 429/5xx = retry with backoff. 502/504 behind API Gateway = Lambda response shape / timeout.
- Lambda: timeouts (VPC + no NAT, defaults), memory, import errors, throttles, missing permissions (role vs resource policy).
- DynamoDB: hot keys, GSI back-pressure, reserved words, UnprocessedItems. SQS: visibility timeout, long polling, DLQs.
- Deployments: CloudFormation first failure event, CodeDeploy agent logs and hooks, ECS stopped reasons.

## Check yourself

1. A VPC-attached Lambda function times out when calling DynamoDB, but works outside the VPC. Fix?
2. CloudFormation shows 15 failed events during an update rollback. Which one do you read first?
3. ECS tasks stop with `CannotPullContainerError` in private subnets. Two possible causes?
4. API Gateway returns 502 right after a deployment. The Lambda logs show the function returned `{"ok": true}`. Why?
5. An EC2 API call fails with `UnauthorizedOperation` and a long encoded message. How do you read it?

<details><summary>Answers</summary>

1. Add a **DynamoDB gateway VPC endpoint** (or a NAT gateway for internet access).
2. The **first** (oldest) failure event: later ones are usually consequences.
3. No network route to ECR (no NAT gateway or ECR/S3 VPC endpoints), or the **task execution role** lacks ECR permissions (also a wrong image tag).
4. With proxy integration the function must return `{"statusCode": ..., "body": "..."}`. `{"ok": true}` is a malformed proxy response.
5. `aws sts decode-authorization-message --encoded-message <msg>` (requires `sts:DecodeAuthorizationMessage`).

</details>

## Further reading

- [Troubleshoot Lambda](https://docs.aws.amazon.com/lambda/latest/dg/lambda-troubleshooting.html)
- [Troubleshooting CloudFormation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/troubleshooting.html)
- [Troubleshooting CodeDeploy](https://docs.aws.amazon.com/codedeploy/latest/userguide/troubleshooting.html)
- [Amazon ECS stopped task errors](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/stopped-task-errors.html)
- [Error retries and exponential backoff](https://docs.aws.amazon.com/general/latest/gr/api-retries.html)
