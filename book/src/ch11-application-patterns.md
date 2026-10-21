# Application patterns and resilience

> **In this chapter**
> - Architectural patterns the exam names: event-driven, microservices, monolith, choreography vs orchestration, fan-out
> - Stateless vs stateful, tightly vs loosely coupled, synchronous vs asynchronous
> - Idempotency, and why at-least-once delivery makes it mandatory
> - Fault tolerance: timeouts, retries with backoff and jitter, circuit breakers, bulkheads, DLQs, fallbacks
> - Serialization and event design
>
> **Exam weight**: Domain 1 Task 1.1 (its "knowledge" list is this chapter) · **Exercises**:
> `lambda_5`, `res_1`, `res_2` (and `sdk_3`, `sqs_2`) · **Quiz**: `uv run awslings quiz patterns`

## Architectural patterns

| Pattern | Idea | On AWS |
|---|---|---|
| **Monolith** | One deployable unit | EC2/Beanstalk/ECS app. Simple at first, scales and deploys as one block |
| **Microservices** | Small services owning their data, communicating over APIs/events | API Gateway + Lambda/ECS per service, one DynamoDB table per service |
| **Event-driven** | Producers emit events, routers deliver them, consumers react | EventBridge, SNS, SQS, Kinesis, S3/DynamoDB events |
| **Fan-out** | One message → many independent consumers | SNS → SQS queues, EventBridge rules |
| **Queue-based load leveling** | A queue absorbs spikes, consumers process at a steady rate | SQS + Lambda/ECS workers |
| **Claim check** | Store a large payload elsewhere, pass a reference | S3 + pointer in SQS/SNS/EventBridge (exercise `sqs_4`) |
| **Saga** | A long transaction as local steps + compensating actions on failure | Step Functions with Catch → compensation steps |

### Choreography vs orchestration

```text
CHOREOGRAPHY (decentralized)                ORCHESTRATION (central coordinator)
OrderPlaced ──► EventBridge ─┬─► Payment     Step Functions: Validate → Charge → Ship
                             ├─► Inventory      (knows the sequence, retries, compensations,
                             └─► Email           and the current state of each order)
```

- **Choreography**: every service reacts to events. Loosely coupled and easy to extend (add a
  consumer without touching others), but the overall flow is implicit and harder to follow.
- **Orchestration**: one workflow drives the steps. The flow is explicit, with centralized error
  handling and visibility, but there is a central component to maintain.

> **Exam tip** — "Coordinate several steps with retries, error handling and visibility of the process
> state" → **orchestration with Step Functions**. "Services must react independently to business events,
> new consumers added without changing producers" → **choreography with EventBridge**.

## Core properties

- **Stateless vs stateful**: a stateless component keeps no client state between requests, so any instance
  can serve any request (horizontal scaling, safe replacement). Put state in DynamoDB, ElastiCache,
  S3 or RDS, not in instance memory or local disk. Lambda functions must be designed stateless.
- **Tightly vs loosely coupled**: tight coupling (direct synchronous calls, shared databases) spreads
  failures and forces coordinated deployments. Loose coupling (queues, events, contracts) isolates them.
- **Synchronous vs asynchronous**: synchronous = the caller waits (simple, but latency adds up and failures
  propagate). Asynchronous = the caller hands off work (queue/event) and continues (resilient, scalable,
  but eventual consistency and more moving parts). Long work behind an API → accept, enqueue, return **202**.

## Idempotency

An operation is **idempotent** if doing it twice has the same effect as doing it once.

Why it matters: **at-least-once delivery** is everywhere: SQS standard queues, SNS, EventBridge, S3
notifications, Lambda asynchronous retries, event source mapping retries, client retries after a timeout.

Techniques:

1. **Idempotency key**: a unique id per business operation (payment id, request id, event id).
   Record it with a **conditional write** before doing the side effect (exercise `lambda_5`):

   ```python
   table.put_item(Item={"pk": event_id, "expires_at": now + 86400},
                  ConditionExpression="attribute_not_exists(pk)")   # ConditionalCheckFailed → duplicate
   ```

2. **Naturally idempotent writes**: `PUT` the final state (`SET status = SHIPPED`) rather than
   increments (`ADD balance :x`). Increments need deduplication.
3. **API idempotency tokens**: `ClientToken` (EC2), `ClientRequestToken` (DynamoDB transactions, Step
   Functions, Secrets Manager).
4. **FIFO deduplication**: SQS FIFO `MessageDeduplicationId` (5-minute window).
5. Libraries: Powertools for AWS Lambda has an **idempotency** utility backed by DynamoDB.

> **Trap** — "Exactly-once" end to end is rare. The exam's answer is usually **idempotent consumers**
> (plus FIFO deduplication when ordering and dedup are explicit requirements).

## Fault-tolerance toolbox

| Tool | What it does | AWS examples |
|---|---|---|
| **Timeouts** | Never wait forever on a dependency | SDK `connect_timeout`/`read_timeout`, Lambda timeout, Step Functions `TimeoutSeconds` |
| **Retries with exponential backoff + jitter** | Survive transient errors without amplifying the overload | SDK retry modes, Step Functions `Retry`, your own loop (exercise `sdk_3`) |
| **Circuit breaker** | Stop calling a failing dependency for a while, fail fast, probe again later | Your code or library (exercise `res_1`) |
| **Bulkhead** | Isolate resources so one failure cannot consume everything | Reserved concurrency per function, separate queues/pools |
| **Dead-letter queues** | Park poison messages instead of retrying forever | SQS redrive policy, Lambda destinations/DLQ, SNS subscription DLQ, EventBridge target DLQ |
| **Fallback / graceful degradation** | Serve cached or default data when a dependency is down | ElastiCache, static responses |
| **Load leveling / rate limiting** | Protect downstream systems | SQS buffer, Lambda reserved concurrency or SQS maximum concurrency, API Gateway throttling, EventBridge API destination rate limits |
| **Health checks and failover** | Detect bad instances and route around them | ELB health checks, Route 53 failover, Multi-AZ |

### Resilient third-party integrations (exam guide v2.1)

Calling an external API (payment provider, partner, SaaS) needs every tool above:

1. **Timeouts** shorter than your own SLA.
2. **Retries** with backoff and jitter on 429/5xx/timeouts, never on 4xx validation errors, and only for idempotent calls
   (or with an idempotency key the partner supports).
3. A **circuit breaker** so that an outage does not tie up all your workers.
4. **Buffer** requests in **SQS** and process them with limited concurrency to respect the partner's rate limits.
   EventBridge **API destinations** offer built-in rate limiting and retries.
5. **Fallbacks**: cached responses, queued "pending" status, user-facing degradation.
6. **Observability**: metrics on errors/latency per dependency, alarms, traces (X-Ray subsegments).

### Circuit breaker states

```text
CLOSED ──N consecutive failures──► OPEN ──reset timeout──► HALF_OPEN ──trial succeeds──► CLOSED
                                    ▲                          │
                                    └──── trial fails ─────────┘
```

## Serialization and event design

- **Serialization** turns objects into bytes for storage or transport (JSON most often, also Avro/Protobuf).
  The usual pitfalls: floats in DynamoDB (use `Decimal`), `Decimal` in `json.dumps`, dates (use ISO 8601
  strings in UTC, which also sort), binary in JSON (base64), character encodings (exercise `res_2`).
- **Event design**:
  - make events **self-describing** (`source`, `detail-type`, a version: `OrderPlaced.v2`),
  - choose between **thin events** (ids only, consumers fetch details) and **event-carried state**
    (full data, fewer callbacks, bigger payloads),
  - evolve schemas in a **backward-compatible** way (add optional fields, never rename/remove in place),
  - the **EventBridge schema registry** documents events and generates code bindings.
- **Configuration** outside the code (environment variables, Parameter Store, AppConfig) so the same
  artifact runs in every environment (chapter 14).

## Hands-on

| Exercise | Skill |
|---|---|
| `lambda_5` | Idempotent payment handler with a conditional put + TTL |
| `res_1` | A circuit breaker (closed / open / half-open) |
| `res_2` | Serialization for DynamoDB and JSON (Decimal, ISO dates, enums) |
| `sdk_3`, `sqs_2` | Backoff with jitter, dead-letter queues |

## Summary

- Event-driven + loosely coupled + stateless = scalable and resilient. Synchronous chains spread failures.
- Choreography (EventBridge/SNS) for independent reactions. Orchestration (Step Functions) for explicit, observable flows.
- At-least-once delivery → **idempotent consumers** (idempotency keys + conditional writes).
- Timeouts, retries with backoff and jitter (transient errors only), circuit breakers, bulkheads, DLQs, fallbacks.
- Serialize carefully (Decimal, ISO 8601, base64) and version your events.

## Check yourself

1. A Lambda function triggered by SNS sometimes sends two confirmation emails for the same order. Why, and what is the fix?
2. A partner API allows 10 requests/s, but your traffic peaks at 100/s. Design?
3. Orchestration or choreography: "When an order is placed, five teams each want to run their own process, and new teams will join"?
4. Why add jitter to exponential backoff?
5. What state does a circuit breaker enter after the reset timeout, and what happens next?

<details><summary>Answers</summary>

1. SNS (and Lambda async retries) deliver at least once. Make the handler **idempotent**: record the
   order/event id with a conditional write before sending, and skip duplicates.
2. Buffer requests in **SQS** and consume with limited concurrency (e.g. Lambda maximum concurrency or
   reserved concurrency) sized for 10 req/s, with retries/backoff on 429 and a DLQ. EventBridge API
   destinations with a rate limit are an alternative.
3. **Choreography** (EventBridge rules per team): producers don't change when consumers are added.
4. To spread retries over time so that many clients don't retry at the same instant (thundering herd).
5. **Half-open**: one trial call goes through. Success → closed. Failure → open again (timer restarts).

</details>

## Further reading

- [AWS Well-Architected — Reliability pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html)
- [Timeouts, retries and backoff with jitter (Amazon Builders' Library)](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/)
- [Making retries safe with idempotent APIs (Amazon Builders' Library)](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)
- [Powertools for AWS Lambda — Idempotency](https://docs.powertools.aws.dev/lambda/python/latest/utilities/idempotency/)
- [Serverless Land patterns](https://serverlessland.com/patterns)
