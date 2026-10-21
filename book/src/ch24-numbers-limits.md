# Numbers and limits cheat sheet

> Use this page for `/drill` sessions and the last days before the exam. Values are AWS defaults/limits
> as documented in late 2026. ⚠️ marks values that changed after the exam guide was written
> (the exam may still use the old value). "Soft" = can be raised through Service Quotas.

## Exam

| | |
|---|---|
| Questions / time | 65 (50 scored) / 130 min (+30 with ESL accommodation) |
| Passing score | 720 / 1000 |
| Domain weights | 32% / 26% / 24% / 18% |
| Last day for DVA-C02 | **30 Nov 2026** |

## Lambda

| Item | Value |
|---|---|
| Memory | 128 MB – 10,240 MB (CPU proportional, ~1 vCPU at 1,769 MB) |
| Timeout | default 3 s, **max 900 s (15 min)** |
| `/tmp` ephemeral storage | 512 MB (default) – 10,240 MB |
| Environment variables | 4 KB total |
| Layers | 5 per function |
| Deployment package | 50 MB zipped (direct upload), **250 MB unzipped** (incl. layers), container image **10 GB** |
| Payload | **6 MB** synchronous (request and response) · async **1 MB** ⚠️ (was 256 KB) |
| Concurrency | **1,000** per Region (soft). ≥ 100 always unreserved. Scaling +1,000 per 10 s per function |
| Async retries / max event age | **2** retries (0–2) / up to **6 h** |
| SQS event source visibility timeout | ≥ **6×** function timeout |
| Kinesis/DynamoDB ESM parallelization factor | 1 – **10** |
| Free tier | 1M requests + 400,000 GB-s per month |

## API Gateway

| Item | Value |
|---|---|
| Integration timeout | 50 ms – **29 s** (REST, raisable for Regional/private), 30 s (HTTP API) |
| Account throttle | **10,000 rps** steady, **5,000** burst per Region (soft) |
| Payload size | 10 MB |
| Cache TTL | default **300 s**, max **3,600 s**. Cache size 0.5 – 237 GB |
| Lambda authorizer cache TTL | default 300 s, max 3,600 s |

## DynamoDB

| Item | Value |
|---|---|
| Item size | **400 KB** |
| 1 RCU | 1 strongly consistent read/s of **4 KB** = 2 eventually consistent reads/s. Transactional ×2 |
| 1 WCU | 1 write/s of **1 KB**. Transactional ×2 |
| Query/Scan page | 1 MB |
| BatchGetItem / BatchWriteItem | 100 items / **25** items (16 MB) |
| Transactions | **100** actions, 4 MB |
| LSI / GSI per table | 5 (at creation only) / 20 (default) |
| LSI item collection | 10 GB per partition key value |
| Streams retention | **24 h** |
| PITR | 35 days |
| TTL attribute | epoch **seconds** (Number), deletion typically within a few days |
| DAX default item TTL | 5 min |

## S3

| Item | Value |
|---|---|
| Object size | 0 B – **5 TB** |
| Single PUT | 5 GB (multipart recommended > 100 MB, required > 5 GB) |
| Multipart | parts 5 MB – 5 GB, ≤ 10,000 parts |
| Request rate per prefix | 3,500 PUT/COPY/POST/DELETE, 5,500 GET/HEAD per second |
| Presigned URL max validity | 7 days (SigV4, IAM user). Shorter with temporary credentials |
| Min storage duration | Standard-IA / One Zone-IA **30 days**, Glacier IR / Flexible **90 days**, Deep Archive **180 days** |
| Transition to IA | objects must be ≥ **30 days** old |
| Glacier Flexible restore | Expedited 1–5 min · Standard 3–5 h · Bulk 5–12 h |
| Deep Archive restore | Standard ≤ 12 h · Bulk ≤ 48 h |
| User metadata | 2 KB |
| Tags per object | 10 |

## SQS / SNS / EventBridge / Kinesis

| Item | Value |
|---|---|
| SQS message size | **1 MiB** ⚠️ (was **256 KB**, the exam's usual value). Extended client: up to 2 GB via S3 |
| SQS retention | default **4 days**, 1 min – **14 days** |
| SQS visibility timeout | default **30 s**, 0 – **12 h** |
| SQS long polling | `WaitTimeSeconds` up to **20 s** |
| SQS delay | 0 – **15 min** |
| SQS batch | **10** messages |
| SQS FIFO throughput | **300** msg/s per API action, **3,000** with batching (more in high throughput mode) |
| FIFO deduplication interval | **5 min** |
| SNS message size | **256 KiB** default, opt-in up to 1 MiB ⚠️ (Sep 2026) |
| EventBridge | ≤ **5 targets** per rule. Retries up to **24 h / 185 attempts**. Events up to 1 MB ⚠️ |
| Kinesis shard (provisioned) | write **1 MB/s or 1,000 records/s**. Read **2 MB/s** shared (or 2 MB/s per consumer with enhanced fan-out) |
| Kinesis record | 1 MB. PutRecords ≤ 500 records / 5 MB |
| Kinesis retention | **24 h** default, up to **365 days** |

## Step Functions

| Item | Value |
|---|---|
| Standard workflow | up to **1 year**, exactly-once, priced per state transition |
| Express workflow | up to **5 minutes**, at-least-once (async), priced per request + duration |
| Retry defaults | IntervalSeconds 1, MaxAttempts 3, BackoffRate 2.0 |

## Security

| Item | Value |
|---|---|
| KMS `Encrypt` plaintext | **4 KB** max → envelope encryption above |
| KMS key deletion waiting period | 7 – 30 days (default 30) |
| KMS automatic rotation | yearly by default (90 – 2,560 days configurable) for customer managed keys |
| STS AssumeRole duration | 15 min – role max session (≤ **12 h**). Role chaining ≤ 1 h |
| Cognito tokens | ID/access 60 min default (5 min – 24 h). Refresh 30 days default (60 min – 10 years) |
| Secrets Manager | secret ≤ 64 KB, ~$0.40/secret/month |
| Parameter Store | Standard 4 KB (free, 10,000 params), Advanced 8 KB (100,000 params, policies) |
| IAM managed policy versions | 5 |

## Monitoring and deployment

| Item | Value |
|---|---|
| CloudWatch metric resolution | standard 1 min, high-resolution 1 s. EC2 basic monitoring 5 min (detailed 1 min) |
| Metric dimensions | up to 30 |
| Metric retention | 1-s data 3 h · 1-min 15 days · 5-min 63 days · 1-h 455 days |
| CloudWatch Logs default retention | **never expire** (set it!) |
| CloudTrail event history | **90 days** (management events, free) |
| X-Ray default sampling | **1 request/s + 5%** |
| X-Ray daemon | **UDP 2000** |
| X-Ray annotations | up to 50 per trace |
| CodePipeline manual approval | expires after **7 days** |
| ALB deregistration delay | 300 s default |
| CodeArtifact auth token | up to 12 h |
