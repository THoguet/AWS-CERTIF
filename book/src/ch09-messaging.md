# SQS, SNS and EventBridge

> **In this chapter**
> - Amazon SQS: standard vs FIFO, visibility timeout, long polling, DLQs, message size, scaling consumers
> - Amazon SNS: pub/sub, fan-out to SQS, subscription filter policies, FIFO topics
> - Amazon EventBridge: event buses, rules and patterns, targets, Scheduler, archive/replay, Pipes
> - How to choose between SQS, SNS, EventBridge and Kinesis
>
> **Exam weight**: Domain 1 Task 1.1 (messaging, event-driven patterns, fan-out, DLQs), Domain 4
> Task 4.3 (messaging, filter policies) · **Exercises**: `sqs_1`–`sqs_4`, `sns_1`, `events_1`
> · **Quiz**: `uv run awslings quiz messaging`

## Why messaging?

A synchronous chain (`API → service A → service B`) fails as soon as one link is slow or down.
Putting a **queue** or an **event bus** between components:

- **decouples** producers from consumers (they scale, deploy and fail independently),
- **absorbs bursts** (the queue is a buffer, and consumers work at their own pace),
- adds **durability and retries** (messages wait until processed).

## Amazon SQS

### Standard vs FIFO

| | **Standard queue** | **FIFO queue** (`name.fifo`) |
|---|---|---|
| Throughput | Nearly unlimited | 300 messages/s per API action, **3,000 with batching** (10 per batch). Much more with *high throughput mode* |
| Delivery | **At least once** (occasional duplicates) | **Exactly-once processing**: duplicates dropped within a **5-minute deduplication interval** |
| Order | Best effort | **Strict order within a message group** (`MessageGroupId`). Groups are processed in parallel |
| Deduplication | none | `MessageDeduplicationId`, or **content-based deduplication** (SHA-256 of the body) |

You cannot convert a standard queue into a FIFO queue (or the reverse): create a new queue.

> **Exam tip** — "Process orders in sequence per customer, no duplicates" → **FIFO queue** with
> `MessageGroupId = customer_id`. Ordering only holds **within** a group, which is what makes parallelism possible.

### Message lifecycle and visibility timeout

```text
Producer ──SendMessage──► [queue] ──ReceiveMessage──► Consumer ──DeleteMessage(ReceiptHandle)──► gone
                              ▲                          │
                              └─ visibility timeout expires without a delete: the message reappears
```

- After a consumer receives a message, it is **invisible** to others for the **visibility timeout**
  (default **30 s**, 0 s – **12 h**). If the consumer does not **delete** it in time, the message
  becomes visible again and is processed again.
- Set the timeout above your processing time. For long jobs, extend it with
  `ChangeMessageVisibility` (a heartbeat). With Lambda, use **≥ 6× the function timeout**.
- Each receive increments `ApproximateReceiveCount`.

### Polling

- **Short polling** (default, `WaitTimeSeconds=0`) returns immediately, often empty, and costs requests.
- **Long polling** (`WaitTimeSeconds` 1–**20** s, or the queue attribute `ReceiveMessageWaitTimeSeconds`)
  waits for messages: fewer empty responses, lower cost, lower latency. **Prefer it.**
- Receive up to **10** messages per call. The batch APIs (`SendMessageBatch`, `DeleteMessageBatch`)
  also handle 10 messages per call and reduce cost.

### Other settings

| Setting | Values |
|---|---|
| Message retention | 1 min – **14 days**, default **4 days** |
| Message size | **1 MiB** since August 2025 (it was **256 KB**, the value most exam questions assume). Larger: the **claim-check pattern** with S3, e.g. the SQS Extended Client Library (up to 2 GB) |
| Delay queue (`DelaySeconds`) | 0 – **15 min** before new messages become visible. Message timers set it per message (standard queues) |
| Message attributes | Up to 10 typed attributes (metadata for routing/filtering) |
| Encryption | SSE-SQS (default) or SSE-KMS. In transit: HTTPS |
| Access | IAM + **queue policy** (resource-based): cross-account access, letting SNS/S3/EventBridge send messages |

### Dead-letter queues

A **redrive policy** moves a message to a **DLQ** after `maxReceiveCount` failed receives, so that a
**poison message** stops looping (exercise `sqs_2`).

- The DLQ must be the same type (FIFO → FIFO), in the same account and Region.
- Give the DLQ a **longer retention** than the source: standard queues keep the original enqueue timestamp.
- Alarm on the DLQ's `ApproximateNumberOfMessagesVisible > 0`. After fixing the bug, **redrive** the
  messages back to the source queue (console or `StartMessageMoveTask`).

### Scaling consumers

- Key metrics: `ApproximateNumberOfMessagesVisible` (backlog) and `ApproximateAgeOfOldestMessage` (lag).
- EC2/ECS consumers: auto scale on **backlog per instance** (a target tracking policy on a custom metric).
- Lambda consumers scale automatically with the queue (cap them with *maximum concurrency* on the event source mapping).

## Amazon SNS

A **pub/sub** service: publishers send to a **topic**, and SNS **pushes** a copy to every subscription.
SNS does not store messages for later retrieval.

- Subscribers: **SQS, Lambda, HTTP/S endpoints, email, SMS, mobile push** (APNs, FCM...), **Amazon Data Firehose**.
- **Fan-out pattern**: SNS → several SQS queues. Each consumer gets its own durable copy and its own
  retry/DLQ policy (exercise `sns_1`).
- **Subscription filter policies**: each subscription receives only matching messages. Policies match
  **message attributes** (default) or the **message body** (`FilterPolicyScope: MessageBody`), with exact
  values, prefixes, `anything-but`, numeric ranges, `exists`...
  - AND across keys, OR within a key's list: `{"event_type": ["order_placed"], "country": ["FR", "BE"]}`.
  - Filtering in SNS saves the cost of invoking consumers only to discard messages.
- **Raw message delivery** (SQS, HTTP/S, Firehose): deliver just the body, without the SNS JSON envelope.
- **FIFO topics** (`.fifo`): ordering and deduplication, fanning out to SQS queues.
- Message size: **256 KiB** by default. Since September 2026 a topic can opt in to **1 MiB**
  (`MaximumMessageSize` attribute, which restricts subscription types). Larger payloads → the claim-check pattern (extended client library with S3).
- Delivery retries: built-in for AWS endpoints, a configurable delivery policy for HTTP/S. A
  **DLQ per subscription** (an SQS queue) catches messages that could not be delivered.
- Security: **topic access policy** (who can publish/subscribe: S3, CloudWatch alarms, other accounts),
  SSE-KMS (the KMS key policy must allow publishing services to use the key).

> **Exam tip** — "One event must trigger several independent processes, each able to retry on its own"
> → **SNS + one SQS queue per consumer** (fan-out). "Each consumer only wants some events" → **filter policies**.

## Amazon EventBridge

An **event router**: events land on an **event bus**, and **rules** match them with **patterns**
and route them to **targets**.

- **Buses**: the **default** bus (events from AWS services: EC2 state changes, CodePipeline, S3 with EventBridge
  notifications enabled...), **custom** buses (your applications), **partner** buses (SaaS: Zendesk, Datadog, Auth0...).
- **Event envelope**: `source`, `detail-type`, `account`, `region`, `time`, `resources`, `detail` (your JSON).
  `PutEvents` sends up to 10 entries per call.
- **Rules**: an event pattern (or a schedule), up to **5 targets** per rule, an optional **input
  transformer** (reshape the event for the target), a retry policy (default **24 hours / 185 attempts**)
  and a **DLQ** (SQS) per target.
- **Targets**: Lambda, SQS, SNS, Step Functions, Kinesis, Firehose, ECS tasks, CodePipeline, CloudWatch
  Logs, **API destinations** (any HTTP API, with auth and rate limiting), another event bus (cross-account / cross-Region)...
- **Event patterns** (exercise `events_1`):

```json
{
  "source": ["shop.orders"],
  "detail-type": ["OrderPlaced"],
  "detail": {
    "amount":  [{"numeric": [">=", 100]}],
    "country": [{"anything-but": ["TEST"]}],
    "coupon":  [{"exists": false}],
    "sku":     [{"prefix": "BOOK-"}]
  }
}
```

  Every listed field must match. Values are **arrays** (OR). Other content filters include `suffix`,
  `equals-ignore-case`, `wildcard`, `cidr` and `$or`.
- **EventBridge Scheduler**: one-time and recurring schedules (cron/rate, time zones, flexible
  windows) invoking 200+ AWS APIs. Prefer it over scheduled rules.
- **Archive and replay**: keep events and replay them (after a bug fix, or to test a new consumer).
- **Schema registry**: discovers event structures and generates **code bindings**.
- **EventBridge Pipes**: point-to-point integration source → filter → enrich → target (e.g. DynamoDB
  Stream → filter → Lambda enrichment → Step Functions), without glue code.
- Event size: up to **1 MB** (raised from 256 KB in early 2026).

> **Exam tip** — "React to events from AWS services or SaaS applications", "route events to many
> targets by content", "schedule a task", "loosely coupled microservices (choreography)" → **EventBridge**.

## Choosing a messaging service

| | **SQS** | **SNS** | **EventBridge** | **Kinesis Data Streams** (ch10) |
|---|---|---|---|---|
| Model | Queue (pull) | Pub/sub (push) | Event bus + rules (push) | Stream (pull, replayable) |
| Consumers per message | **One** (competing consumers) | Every subscriber | Every matching target (≤ 5 per rule) | **Many**, each reading the whole stream |
| Persistence | Up to 14 days, until deleted | None (DLQ for failed deliveries) | Archive (optional) | 24 h – 365 days, **replay** |
| Ordering | FIFO queues per group | FIFO topics | No ordering guarantee | **Per shard** (partition key) |
| Filtering | — (consumer side) | Filter policies | Rich event patterns | — (consumer side, or Lambda ESM filters) |
| Typical use | Decoupling, buffering, work queues | Fan-out, notifications (email/SMS/push) | Event routing, AWS/SaaS events, schedules | Real-time analytics, high-throughput ordered streams |

## Hands-on

| Exercise | Skill |
|---|---|
| `sqs_1` | Long polling, attributes, deleting only after success |
| `sqs_2` | Redrive policy and DLQ retention |
| `sqs_3` | FIFO naming, message groups, content-based deduplication |
| `sqs_4` | The claim-check pattern for large payloads |
| `sns_1` | Fan-out with filter policies and raw delivery |
| `events_1` | Event patterns: prefix, numeric, anything-but, routing to SQS |

Optional lab: `labs/lab03-event-driven`.

## Summary

- SQS: delete after processing. Visibility timeout (30 s default, ≤ 12 h) > processing time. Long polling up to 20 s. Retention 4 days default (≤ 14). DLQ via redrive policy.
- FIFO: order per message group, 5-minute deduplication, 300 TPS (3,000 batched), name ends in `.fifo`.
- Message sizes: the exam usually says 256 KB → S3 claim check for bigger payloads (SQS now accepts 1 MiB).
- SNS: push fan-out, filter policies, raw delivery, DLQ per subscription. SNS + SQS = durable fan-out.
- EventBridge: buses, patterns, ≤ 5 targets per rule, retries 24 h, archive/replay, Scheduler, Pipes.

## Check yourself

1. Messages are processed twice even though consumers succeed. Processing takes 45 s. What is wrong?
2. How do you reduce empty `ReceiveMessage` responses and cost?
3. A failing message blocks other messages of the same customer in a FIFO queue. What should you configure?
4. Billing needs all order events. Shipping needs only `order_placed` events for France. Design?
5. Which service lets you replay last week's events after fixing a consumer bug: SNS, EventBridge or SQS?

<details><summary>Answers</summary>

1. The visibility timeout (probably the 30 s default) is shorter than the processing time, so messages reappear before
   they are deleted. Raise it (or extend it with ChangeMessageVisibility).
2. **Long polling** (`WaitTimeSeconds` up to 20 or `ReceiveMessageWaitTimeSeconds` on the queue), and batch receives.
3. A **DLQ** (redrive policy with `maxReceiveCount`) so that the poison message leaves the group, plus alarms on the DLQ.
4. An SNS topic with two SQS subscriptions: billing without a filter, shipping with the filter policy
   `{"event_type": ["order_placed"], "country": ["FR"]}`. Or EventBridge rules.
5. **EventBridge** (archive and replay). Kinesis would also allow replay within its retention.

</details>

## Further reading

- [SQS developer guide](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/welcome.html) and [SQS FAQ](https://aws.amazon.com/sqs/faqs/)
- [SNS message filtering](https://docs.aws.amazon.com/sns/latest/dg/sns-message-filtering.html)
- [EventBridge event patterns](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-event-patterns.html)
- [EventBridge Scheduler](https://docs.aws.amazon.com/scheduler/latest/UserGuide/what-is-scheduler.html)
- [EventBridge Pipes](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-pipes.html)
