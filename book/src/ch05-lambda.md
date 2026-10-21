# AWS Lambda

> **In this chapter**
> - The execution model: handler, context, execution environment, cold starts
> - Configuration: memory/CPU, timeout, /tmp, environment variables, layers, extensions, architecture
> - The three invocation models: synchronous, asynchronous (retries, DLQ, destinations), event source mappings
> - Concurrency: limits, reserved and provisioned concurrency, scaling, throttling, SnapStart
> - Permissions (execution role vs resource policy), VPC access, function URLs, logging and metrics
>
> **Exam weight**: Domain 1 Task 1.2 (the single most tested service), plus Domains 3 and 4
> · **Exercises**: `lambda_1`, `lambda_2`, `lambda_4`, `lambda_6`, `lambda_7` (and `lambda_3`, `lambda_5`, `lambda_8` in later chapters)
> · **Quiz**: `uv run awslings quiz lambda`

## The execution model

A Lambda function is code plus configuration. AWS runs it in an **execution environment** (a
Firecracker micro-VM) on demand, and you pay per request and per GB-second of execution.

```python
import os, boto3

TABLE = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])   # INIT: runs once per environment

def handler(event, context):                                          # INVOKE: runs for every event
    print(context.aws_request_id, context.get_remaining_time_in_millis())
    TABLE.put_item(Item={"pk": event["id"]})
    return {"ok": True}
```

**Lifecycle of an execution environment**

```text
 COLD START                                 WARM INVOCATIONS              (idle for a while)
 ┌───────────────────────────────┐   ┌────────┐ ┌────────┐ ┌────────┐   ┌──────────┐
 │ download code · start runtime │ → │ INVOKE │ │ INVOKE │ │ INVOKE │ → │ SHUTDOWN │
 │ INIT: run module-level code   │   └────────┘ └────────┘ └────────┘   └──────────┘
 └───────────────────────────────┘    (one event at a time per environment)
```

- An environment handles **one invocation at a time**. More parallel requests mean more environments.
- **Reuse**: module-level objects (SDK clients, DB connections, caches) and `/tmp` survive between
  warm invocations of the same environment. Create clients **outside the handler** (exercise `lambda_2`).
  Never keep request-specific data in globals.
- **Cold start** = extra latency of the INIT phase (shown as `Init Duration` in the REPORT log line).
  It is larger with big packages, heavy frameworks, and Java/.NET runtimes.

### The context object

`aws_request_id`, `function_name`, `function_version`, `invoked_function_arn` (shows the alias),
`memory_limit_in_mb`, `log_group_name`, `log_stream_name`, `get_remaining_time_in_millis()`.

## Configuration

| Setting | Range / default | Notes |
|---|---|---|
| **Memory** | 128 MB – **10,240 MB** (default 128) | **CPU scales with memory** (≈ 1 vCPU at 1,769 MB, up to 6 vCPUs). More memory can be *cheaper* when it shortens duration |
| **Timeout** | 1 s – **900 s (15 min)**, default **3 s** | Longer jobs → Step Functions, ECS/Fargate, Batch |
| **Ephemeral storage `/tmp`** | **512 MB – 10,240 MB** | Not shared between environments, not durable. Use S3/EFS for persistence |
| **Environment variables** | **4 KB total** | Encrypted at rest with KMS (AWS managed key or your CMK). Secrets → Secrets Manager / Parameter Store (chapter 14) |
| **Architecture** | `x86_64` or **`arm64`** (Graviton2) | arm64 is usually cheaper per GB-second with similar or better performance |
| **Layers** | up to **5** per function | Shared libraries/dependencies, extracted to `/opt`. The function + layers must stay ≤ **250 MB unzipped** |
| **Extensions** | Delivered as layers | Run alongside the function (monitoring agents, the Parameters and Secrets extension...) |
| **Deployment package** | **50 MB zipped** (direct upload), **250 MB unzipped**. **Container image up to 10 GB** (from ECR) | Bigger artifacts → container images. Upload large zips through S3 |
| **Payload** | **6 MB** synchronous (request and response). Asynchronous: **1 MB** since Oct 2025 (256 KB before) | Larger data → put it in S3 and pass a reference |

> **Exam tip** — "The function runs out of memory / is slow and CPU-bound" → **increase memory**
> (which also adds CPU). "Need more than 15 minutes" → not Lambda (Step Functions to orchestrate, or ECS/Fargate).

## Invocation models

### 1. Synchronous (RequestResponse)

The caller waits for the result: **API Gateway, ALB, function URLs, SDK `Invoke`, Cognito triggers,
Lambda@Edge**... Errors go back to the caller, and **the caller decides whether to retry**.

### 2. Asynchronous (Event)

**S3, SNS, EventBridge, CloudWatch Logs subscriptions, SES, CloudFormation custom resources**, or
`Invoke` with `InvocationType="Event"`. Lambda puts the event in an internal queue and returns `202` immediately.

- On a function error, Lambda **retries twice** by default (configurable 0–2), with delays between attempts.
- Events can wait in the queue up to **6 hours** by default (`MaximumEventAgeInSeconds` 60 s – 6 h),
  for example while the function is throttled.
- When retries are exhausted or the event is too old:
  - **Dead-letter queue** (SQS queue or SNS topic): the original event only, failures only,
  - **Destinations** (recommended): `OnSuccess` and/or `OnFailure` → **SQS, SNS, Lambda, EventBridge**
    (and S3 for failures). The record includes the event **plus** the response or error details.

```python
lam.put_function_event_invoke_config(
    FunctionName="thumbnailer", MaximumRetryAttempts=1, MaximumEventAgeInSeconds=3600,
    DestinationConfig={"OnFailure": {"Destination": "arn:aws:sqs:eu-west-3:123456789012:failures"}})
```

> **Exam tip** — "Capture both successful and failed results of asynchronous invocations, with
> context" → **Lambda Destinations**. "Keep failed events for later analysis" → on-failure
> destination (or DLQ).

### 3. Event source mappings (poll-based)

For **SQS, Kinesis Data Streams, DynamoDB Streams, Amazon MSK / self-managed Kafka, Amazon MQ,
DocumentDB**, Lambda runs pollers that read **batches** and invoke your function **synchronously**.
The function's **execution role** needs permission to read the source (e.g. `sqs:ReceiveMessage`,
`sqs:DeleteMessage`, `sqs:GetQueueAttributes`).

| Setting | Meaning |
|---|---|
| `BatchSize`, `MaximumBatchingWindowInSeconds` | How many records per invocation, and how long to wait to fill a batch |
| `FilterCriteria` | Event filtering: drop records that don't match a pattern, before invoking (cheaper) |
| `FunctionResponseTypes: ["ReportBatchItemFailures"]` | Partial batch responses: return only the failed item ids (exercise `lambda_4`) |
| Streams only: `StartingPosition` (TRIM_HORIZON, LATEST, AT_TIMESTAMP), `BisectBatchOnFunctionError`, `MaximumRetryAttempts`, `MaximumRecordAgeInSeconds`, `ParallelizationFactor` (1–10), on-failure destination | Handling poison records in ordered streams |
| SQS only: `ScalingConfig.MaximumConcurrency` | Cap how many concurrent invocations the queue can trigger |

**SQS specifics**: messages of a failed batch become visible again after the queue's **visibility
timeout** and are retried. After `maxReceiveCount`, the queue's **redrive policy** moves them to
the queue's DLQ (a *queue* setting, not a Lambda destination). Set the queue's visibility timeout to
**at least 6× the function timeout**. FIFO queues: batch size ≤ 10, order kept per message group.

**Streams specifics** (Kinesis, DynamoDB Streams): records are processed **in order per shard**.
One failing batch **blocks its shard** until it succeeds or the records expire. Use bisect,
max retry attempts, max record age and an on-failure destination to unblock. Monitor
**IteratorAge**, which grows when consumers fall behind.

```python
def handler(event, context):                       # SQS with ReportBatchItemFailures
    failures = []
    for record in event["Records"]:
        try:
            process(json.loads(record["body"]))
        except Exception:
            failures.append({"itemIdentifier": record["messageId"]})
    return {"batchItemFailures": failures}
```

## Concurrency and scaling

**Concurrency** = the number of invocations in flight ≈ **requests per second × average duration (s)**.
100 req/s × 0.5 s = 50 concurrent executions.

- **Account quota**: **1,000** concurrent executions per Region by default (soft limit). It is shared by all functions.
- **Scaling rate**: each function can add up to **1,000 concurrent executions every 10 seconds**.
- **Reserved concurrency** (per function): *guarantees* that capacity for the function AND *caps* it.
  Lambda keeps at least **100** units unreserved for the other functions. Setting it to **0** throttles
  everything, an emergency off switch. Use it to protect a downstream database from too many connections.
- **Provisioned concurrency**: keeps N environments **initialized** to remove cold starts. Configured on a
  **version or alias** (not `$LATEST`), billed while configured, can be scaled with Application Auto Scaling.
- **Throttling**: synchronous callers get **429 `TooManyRequestsException`**. Asynchronous events are retried
  automatically (up to the max event age). Event source mappings back off and retry.

> **Exam tip** — "Predictable traffic peak at 9 a.m., cold starts unacceptable" → **provisioned concurrency**
> (scheduled scaling). "A function must never use more than 50 concurrent executions" → **reserved concurrency = 50**.

### Cold start mitigation

1. **Provisioned concurrency** for latency-critical paths.
2. **Lambda SnapStart** (Java, Python and .NET runtimes, on published versions): Lambda snapshots
   the initialized environment and restores from it, cutting init time. Code must handle
   uniqueness: re-seed randomness and refresh credentials/connections after restore.
3. Smaller packages, fewer dependencies, lazy imports. Initialize heavy clients once.
4. More memory (more CPU during INIT).

## Permissions

| Policy | Answers | Example |
|---|---|---|
| **Execution role** (IAM role, trust `lambda.amazonaws.com`) | What can the function do? | Write logs, read the SQS queue it polls, put items in DynamoDB |
| **Resource-based policy** (function policy) | Who can invoke the function? | S3, SNS, EventBridge, API Gateway, another account |

```bash
aws lambda add-permission --function-name thumbnailer --statement-id s3-invoke \
  --action lambda:InvokeFunction --principal s3.amazonaws.com \
  --source-arn arn:aws:s3:::photo-inbox --source-account 123456789012
```

> **Trap** — S3 cannot trigger the function / API Gateway returns 500 "Invalid permissions on Lambda
> function" → the **resource-based policy** is missing (for an alias, add it with `--qualifier`).
> "Function cannot write to DynamoDB" → the **execution role** is missing the permission.

## VPC access, function URLs, recursion

- **VPC**: attach subnets + security groups to reach private resources (RDS, ElastiCache). You then need a
  **NAT gateway or VPC endpoints** for AWS public endpoints (chapter 1). Use **RDS Proxy** to pool database
  connections from many concurrent functions (chapter 8).
- **Function URLs**: a dedicated HTTPS endpoint for a function, with auth type `AWS_IAM` (SigV4) or `NONE`, and
  CORS settings. Simpler and cheaper than API Gateway, but no usage plans, request validation or caching.
- **Recursive loop detection**: Lambda detects some infinite loops between Lambda and SQS/SNS/S3 and
  stops them after about 16 iterations. Design to avoid them anyway (chapter 4, exercise `s3_7`).

## Logging and monitoring

- Logs go to CloudWatch Logs `/aws/lambda/<function>` (the role needs `logs:CreateLogStream`/`PutLogEvents`,
  as in `AWSLambdaBasicExecutionRole`). You can choose **JSON log format** and **log levels** natively.
- Each invocation ends with a **REPORT** line: `Duration`, `Billed Duration`, `Memory Size`,
  `Max Memory Used`, `Init Duration` (cold starts only).
- Key metrics (namespace `AWS/Lambda`): `Invocations`, `Errors`, `Throttles`, `Duration`,
  `ConcurrentExecutions`, `IteratorAge` (streams), `DeadLetterErrors`, `DestinationDeliveryFailures`,
  async metrics such as `AsyncEventAge` and `AsyncEventsDropped`.
- **X-Ray active tracing** (`TracingConfig: Active`) and **Lambda Insights** (enhanced system metrics through an extension).

## Pricing in one line

Requests ($0.20 per million) + duration in GB-seconds (memory × billed duration, 1 ms granularity),
+ provisioned concurrency if used. Free tier: 1M requests and 400,000 GB-seconds per month.

## Hands-on

| Exercise | Skill |
|---|---|
| `lambda_1` | Handler, context, stopping before the timeout |
| `lambda_2` | Reusing clients across warm invocations |
| `lambda_4` | SQS partial batch responses |
| `lambda_6` | Concurrency math, reserved pool, visibility timeout rule |
| `lambda_7` | Memory, timeout, env vars, tracing, /tmp, arm64, async retries and destinations |
| `lambda_3`, `lambda_5`, `lambda_8` | Proxy responses (ch06), idempotency (ch11), versions/aliases (ch16) |

Optional lab: `labs/lab01-serverless-api`.

## Summary

- One event per environment at a time. INIT code runs once per environment, so reuse clients. Cold starts show as Init Duration.
- 128 MB–10 GB memory (CPU follows), 15 min max timeout, /tmp up to 10 GB, 4 KB env vars, 5 layers, 250 MB unzipped, 10 GB images.
- Sync: the caller retries. Async: 2 retries, up to 6 h, then DLQ/destinations. ESM: batches, partial failures, DLQ on the queue.
- Concurrency = rps × duration. 1,000 per Region by default. Reserved = guarantee + cap. Provisioned = no cold starts.
- Execution role = what the function does. Resource policy = who can invoke it.

## Check yourself

1. A function processes S3 events and fails on some objects. How many times does Lambda retry by default, and where can the failed events go?
2. 400 requests/s with an average duration of 3 s: what concurrency is needed, and what happens with the default account quota?
3. An SQS-triggered function takes up to 60 s. What visibility timeout should the queue have?
4. What is the difference between reserved and provisioned concurrency?
5. An ordered Kinesis stream is stuck: IteratorAge keeps growing and the same batch fails forever. Which settings help?

<details><summary>Answers</summary>

1. Twice (3 attempts in total). Then to an on-failure destination (SQS, SNS, Lambda, EventBridge, S3) or a DLQ (SQS/SNS).
2. 1,200 concurrent executions. That is more than the default 1,000 per Region, so requests are throttled
   (429 for synchronous callers). Request a quota increase and/or reduce the duration.
3. At least 6 × 60 s = 360 s.
4. Reserved concurrency guarantees and caps how many instances a function can use (no cost). Provisioned
   concurrency keeps environments pre-initialized to avoid cold starts (paid).
5. `BisectBatchOnFunctionError`, `MaximumRetryAttempts`, `MaximumRecordAgeInSeconds`, and an
   on-failure destination. Also fix the poison record handling in code.

</details>

## Further reading

- [Lambda developer guide](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html) and [Lambda FAQ](https://aws.amazon.com/lambda/faqs/)
- [Lambda quotas](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html)
- [Asynchronous invocation](https://docs.aws.amazon.com/lambda/latest/dg/invocation-async.html)
- [Event source mappings](https://docs.aws.amazon.com/lambda/latest/dg/invocation-eventsourcemapping.html)
- [Understanding Lambda function scaling](https://docs.aws.amazon.com/lambda/latest/dg/lambda-concurrency.html)
