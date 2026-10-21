# Kinesis and Step Functions

> **In this chapter**
> - Kinesis Data Streams: shards, partition keys, ordering, capacity math, producers, consumers
> - Amazon Data Firehose and Managed Service for Apache Flink, and how they differ from Data Streams
> - AWS Step Functions: states, Standard vs Express, retries and catchers, data flow, integration patterns
>
> **Exam weight**: Domain 1 Task 1.1 (handling data streaming, orchestration, fault-tolerant patterns)
> · **Exercises**: `kinesis_1`–`kinesis_3`, `sfn_1`, `sfn_2` · **Quiz**: `uv run awslings quiz streaming`

## Kinesis Data Streams

A **stream** is an ordered, replayable log split into **shards**. Many consumers can read the same
data independently, at their own pace, and re-read it within the retention period.

```text
Producers ──PutRecords(partition key)──► shard 1 ──► consumer A (KCL app)
                    MD5(partition key) │  shard 2 ──► consumer B (Lambda)
                       → hash range    └► shard 3 ──► consumer C (Firehose → S3)
```

- **Record**: partition key + data blob (up to 1 MB) + **sequence number** (assigned per shard).
- The **partition key** is hashed to a shard. Same key → same shard → **ordered**. Choose a
  high-cardinality key (user id, device id) to spread load. A bad key creates a **hot shard**.
- **Retention**: **24 hours** by default, up to **365 days**. Records are not deleted when read, so replay is possible.
- **Capacity modes**: **provisioned** (you choose and reshard the shard count) or **on-demand** (scales automatically).

### Shard limits (provisioned mode)

| Direction | Per shard |
|---|---|
| **Write** | **1 MB/s or 1,000 records/s** |
| **Read, shared throughput** | **2 MB/s** shared by all consumers, 5 GetRecords calls/s (up to 10 MB / 10,000 records per call) |
| **Read, enhanced fan-out** | **2 MB/s per consumer**, pushed over HTTP/2 (`SubscribeToShard`), with lower latency |

```text
Shards for writes = max(records/s ÷ 1,000 ; MB/s in ÷ 1)
Shards for reads  = MB/s out × number of consumers ÷ 2      (shared throughput)
                  = MB/s out ÷ 2                            (enhanced fan-out)
```

- Exceeding the limits → **`ProvisionedThroughputExceededException`**. Fix it with retries and backoff,
  a better partition key, or more shards (**split** hot shards, **merge** cold ones).
- `PutRecords` (up to 500 records / 5 MB per call) is **not atomic**: check `FailedRecordCount` and
  resend only the failed records (exercise `kinesis_1`).

### Producers and consumers

| Producers | Consumers |
|---|---|
| SDK `PutRecord` / `PutRecords` | SDK `GetShardIterator` + `GetRecords` (low level, exercise `kinesis_2`) |
| **KPL** (Kinesis Producer Library): batching, aggregation, async retries | **KCL** (Kinesis Client Library): one worker per shard **lease**, **checkpoints in a DynamoDB table**, rebalancing across workers |
| Kinesis Agent (log files), AWS services (CloudWatch Logs, IoT...) | **Lambda** event source mapping: batches, **parallelization factor** (up to 10 concurrent batches per shard, still ordered per partition key), bisect, retries, on-failure destination |
| | **Firehose**, **Managed Service for Apache Flink** |

Shard iterator types: `TRIM_HORIZON` (oldest), `LATEST` (new records only), `AT_SEQUENCE_NUMBER` /
`AFTER_SEQUENCE_NUMBER` (resume from a checkpoint), `AT_TIMESTAMP`.

> **Trap** — More KCL workers than shards does not increase throughput: each shard is processed by
> one worker at a time. To scale consumers, add shards (or use the Lambda parallelization factor).

Monitoring: `IncomingBytes/Records`, `WriteProvisionedThroughputExceeded`,
`ReadProvisionedThroughputExceeded`, and **`GetRecords.IteratorAgeMilliseconds`** (consumer lag;
for Lambda, the `IteratorAge` metric).

Security: IAM, **server-side encryption with KMS**, TLS in transit, VPC interface endpoints.

## Amazon Data Firehose (formerly Kinesis Data Firehose)

A fully managed **delivery** service: it ingests streaming data and loads it into **S3, Redshift
(via S3 + COPY), OpenSearch, Splunk, Snowflake, Apache Iceberg tables, HTTP endpoints** and
partner tools.

- **Near real-time**: it **buffers** by size and time before delivering. Not millisecond real-time.
- Optional **Lambda transformation**, format conversion (JSON → **Parquet/ORC**), compression,
  **dynamic partitioning** of S3 prefixes, failed-record backup to S3.
- No shards to manage, scales automatically, pay per GB ingested. **No replay, no consumers of your own.**
- Sources: direct PUT, a Kinesis data stream, MSK, CloudWatch Logs, EventBridge, SNS...

| | **Kinesis Data Streams** | **Amazon Data Firehose** |
|---|---|---|
| Latency | Real-time (~200 ms, ~70 ms with enhanced fan-out) | Near real-time (buffered) |
| Management | Shards (provisioned) or on-demand | Fully managed |
| Storage / replay | 1–365 days, replay | None |
| Consumers | Custom (KCL, Lambda, Flink...), many | Fixed destinations |
| Transformation | In your consumers | Lambda + format conversion built in |

> **Exam tip** — "Load streaming data into S3/Redshift/OpenSearch with **the least operational
> overhead**" → **Firehose**. "**Real-time** processing, **custom** consumers, **replay**, ordering" → **Data Streams**.

**Amazon Managed Service for Apache Flink** (formerly Kinesis Data Analytics) runs Apache Flink
applications (Java, Python, SQL in Studio notebooks) for real-time analytics: windows, aggregations,
anomaly detection. **Amazon MSK** is managed Apache Kafka, for teams already using Kafka.

## AWS Step Functions

**Serverless orchestration**: a **state machine** defined in the **Amazon States Language (ASL)**
coordinates steps, with retries, branching, parallelism, waiting and human interaction, and a
visual execution history. Avoid "Lambda calling Lambda" chains: they pay for idle waiting and
handle errors badly.

### State types

| State | Purpose |
|---|---|
| **Task** | Do work: invoke Lambda, call an AWS service (200+ services through SDK integrations), run an activity |
| **Choice** | Branch on input values (`NumericGreaterThanEquals`, `StringEquals`, `IsPresent`...), with a `Default` |
| **Parallel** | Run branches concurrently, wait for all of them |
| **Map** | Run the same steps for each item of an array (**inline**), or for millions of items in S3 (**distributed map**) |
| **Wait** | Pause for a duration or until a timestamp |
| **Pass** | Pass/transform input to output (also useful to mock steps) |
| **Succeed / Fail** | End the execution successfully / with an error and cause |

### Standard vs Express workflows

| | **Standard** | **Express** |
|---|---|---|
| Max duration | **1 year** | **5 minutes** |
| Execution semantics | **Exactly-once** | At-least-once (async) / at-most-once (sync) |
| Execution history | Visual history in the console/API (kept 90 days) | In CloudWatch Logs (if enabled) |
| Pricing | Per **state transition** | Per request + duration/memory |
| Fits | Long-running, auditable business processes, human approval, non-idempotent steps | High-volume, short, idempotent event processing (IoT ingestion, streaming transforms, microservice glue) |

> **Exam tip** — "Workflow waits days for a manager's approval" → **Standard** + callback pattern.
> "Hundreds of thousands of short executions per second, cost matters" → **Express**.

### Error handling: Retry and Catch

```json
"ChargeCard": {
  "Type": "Task",
  "Resource": "arn:aws:states:::lambda:invoke",
  "Parameters": {"FunctionName": "charge", "Payload.$": "$"},
  "Retry": [{
    "ErrorEquals": ["Lambda.ServiceException", "Lambda.TooManyRequestsException", "States.Timeout"],
    "IntervalSeconds": 2, "MaxAttempts": 3, "BackoffRate": 2.0, "JitterStrategy": "FULL"
  }],
  "Catch": [{"ErrorEquals": ["States.ALL"], "ResultPath": "$.error", "Next": "NotifyFailure"}],
  "TimeoutSeconds": 30,
  "Next": "Ship"
}
```

- **Retry** runs first (defaults: `IntervalSeconds` 1, `MaxAttempts` 3, `BackoffRate` 2.0).
  **Catch** takes over when retries are exhausted or for errors you don't retry.
- Predefined errors: `States.ALL`, `States.Timeout`, `States.TaskFailed`, `States.Permissions`,
  `States.HeartbeatTimeout`... plus errors raised by your code (exception names).
- `TimeoutSeconds` and `HeartbeatSeconds` on tasks prevent executions from hanging forever.
- The **saga pattern**: catchers route to compensating steps (refund, release stock) when a later step fails.

### Data flow (JSONPath)

```text
state input → InputPath (select) → Parameters (build task input) → [Task]
           → ResultSelector (shape the result) → ResultPath (where to put it in the input) → OutputPath (select) → next state
```

- `"ResultPath": "$.error"` keeps the original input and **adds** the result/error under `error`.
  `"ResultPath": null` discards the result and passes the input through.
- Keys ending in `.$` are evaluated: `"order_id.$": "$.order_id"` (input), `"token.$": "$$.Task.Token"` (context object).
- Since late 2024 you can also use **JSONata** (`"QueryLanguage": "JSONata"`, with `Arguments`/`Output`) as a
  simpler alternative to the JSONPath fields.

### Service integration patterns

| Pattern | Resource suffix | Behavior |
|---|---|---|
| **Request Response** | (none) | Call the service, continue as soon as it answers |
| **Run a Job** | `.sync` | Wait for the job to complete (ECS task, Batch, Glue, CodeBuild, nested Step Functions...) |
| **Wait for Callback** | `.waitForTaskToken` | Pass `$$.Task.Token` to someone (SQS message, email via Lambda...). The execution pauses until `SendTaskSuccess` / `SendTaskFailure` (exercise `sfn_2`) |

Permissions: the state machine's **execution role** must allow every action its tasks perform.
Testing: the **TestState** API tests a single state, and Workflow Studio visualizes and edits
workflows. Observability: execution history, CloudWatch metrics and logs, X-Ray tracing.

## Hands-on

| Exercise | Skill |
|---|---|
| `kinesis_1` | Producer with batches of 500, retrying only failed records |
| `kinesis_2` | Consumer with shard iterators, iterator types |
| `kinesis_3` | Shard capacity math, shared vs enhanced fan-out |
| `sfn_1` | ASL with Retry, Catch (ResultPath), Choice, Fail |
| `sfn_2` | Callback pattern with task tokens |

Optional lab: `labs/lab03-event-driven`.

## Summary

- Data Streams: shards (1 MB/s or 1,000 rec/s in, 2 MB/s out), ordering per partition key, 24 h–365 days retention, replay, many consumers.
- Hot shard / throughput exceeded → better partition key, more shards, backoff. KCL uses DynamoDB for leases/checkpoints.
- Firehose: managed near-real-time delivery to S3/Redshift/OpenSearch/Splunk/HTTP, transforms, no replay.
- Step Functions: Standard (1 year, exactly-once, auditable) vs Express (5 min, high volume, at-least-once).
- Retry then Catch. ResultPath keeps the input. `.sync` waits for jobs. `.waitForTaskToken` waits for callbacks.

## Check yourself

1. Records arrive at 3,000 records/s, 0.5 KB each. How many shards are needed for writes?
2. Five applications read the whole stream in parallel and fall behind. What feature helps without adding shards?
3. A company wants clickstream data in S3 as Parquet files, with minimal management. Which service?
4. A Lambda step in a workflow sometimes fails with throttling errors. How do you handle it in ASL?
5. A workflow must wait for a human to approve an order, sometimes for 3 days. Which workflow type and pattern?

<details><summary>Answers</summary>

1. 3,000 records/s ÷ 1,000 = **3 shards** (the bandwidth, 1.5 MB/s, also needs 2, so 3 dominates).
2. **Enhanced fan-out** (2 MB/s per consumer per shard).
3. **Amazon Data Firehose** with format conversion to Parquet.
4. A `Retry` on `Lambda.TooManyRequestsException` (and similar errors) with backoff, then a `Catch` for persistent failures.
5. A **Standard** workflow (Express is limited to 5 minutes) with the **wait for callback** pattern (`.waitForTaskToken`).

</details>

## Further reading

- [Kinesis Data Streams developer guide](https://docs.aws.amazon.com/streams/latest/dev/introduction.html) and [quotas](https://docs.aws.amazon.com/streams/latest/dev/service-sizes-and-limits.html)
- [Amazon Data Firehose developer guide](https://docs.aws.amazon.com/firehose/latest/dev/what-is-this-service.html)
- [Step Functions developer guide](https://docs.aws.amazon.com/step-functions/latest/dg/welcome.html)
- [Standard vs Express workflows](https://docs.aws.amazon.com/step-functions/latest/dg/choosing-workflow-type.html)
- [Handling errors in Step Functions](https://docs.aws.amazon.com/step-functions/latest/dg/concepts-error-handling.html)
