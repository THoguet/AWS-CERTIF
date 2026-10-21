# Optimization

> **In this chapter**
> - Right-sizing Lambda (memory, architecture), cold starts, concurrency
> - Caching at every layer, including caching based on request headers
> - Optimizing messaging: filter policies, batching, long polling, event filtering
> - Data access performance: DynamoDB and S3
> - Profiling and recommendations: X-Ray, Lambda Insights, Compute Optimizer, Power Tuning
> - Cost levers a developer controls
>
> **Exam weight**: Domain 4 Task 4.3 (caching, concurrency, messaging, profiling, minimum memory/compute,
> subscription filter policies, caching on request headers) · **Exercises**: `opt_1`, `opt_2` (and
> `lambda_2`, `lambda_6`, `sns_1`, `sdk_5`) · **Quiz**: `uv run awslings quiz optimization`

## Lambda performance and cost

### Memory = CPU

Lambda allocates CPU **proportionally to memory** (about 1 vCPU at 1,769 MB, up to 6 vCPUs at 10,240 MB),
and you pay **memory × duration**. For CPU-bound code, more memory often means **shorter duration at the
same or lower cost** (exercise `opt_1`):

| Memory | Duration | GB-seconds per invocation |
|---|---|---|
| 128 MB | 2,000 ms | 0.25 |
| 512 MB | 450 ms | 0.225 |
| **1,024 MB** | **210 ms** | **0.21** ← cheapest *and* ~10× faster |
| 2,048 MB | 205 ms | 0.41 (no more gain) |

- **AWS Lambda Power Tuning** (an open-source Step Functions state machine) runs the function at several memory
  sizes and plots cost against speed. **Compute Optimizer** recommends memory settings from real usage.
  Watch `Max Memory Used` in the REPORT lines.
- **arm64 (Graviton)**: usually cheaper per GB-second with similar or better performance. Check native dependencies.
- **Initialization**: create SDK clients and connections **outside the handler** and reuse them (exercise
  `lambda_2`). Keep HTTP connections alive. Lazy-load rarely used modules. Trim package size.
- **Cold starts**: provisioned concurrency (predictable latency, paid), **SnapStart** (Java, Python, .NET), smaller packages.
- Don't pay for waiting: no Lambda calling Lambda synchronously, and no sleeping in functions.
  **Step Functions** waits for free (Standard) and orchestrates retries.

### Concurrency

- Concurrency ≈ requests/s × duration. Shorter durations → fewer concurrent executions → fewer throttles (exercise `lambda_6`).
- **Reserved concurrency** protects downstream systems (a database) and isolates critical functions.
- **SQS in front** of a fragile dependency smooths spikes. Cap consumers with the SQS event source **maximum concurrency**.
- For event source mappings: tune **batch size** and **batching window** (fewer, bigger invocations),
  **parallelization factor** for streams, and **event filtering** so that Lambda is not invoked for irrelevant records.

## Caching at every layer

| Layer | Tool | Notes |
|---|---|---|
| Browser / client | HTTP `Cache-Control`, `ETag` | Free, closest to the user |
| Edge | **CloudFront** | Static and dynamic content. Cache policy = cache key + TTLs |
| API | **API Gateway caching** (REST) | Per stage, TTL 300 s default (max 3,600), cache keys from parameters/headers |
| Application | **ElastiCache** (Redis/Valkey/Memcached) | Query results, sessions, computed data. Lazy loading / write-through + TTL |
| Database | **DAX** (DynamoDB), RDS read replicas | Microsecond reads with no code change (DAX) |
| Function | Globals / `/tmp` in Lambda, the Parameters and Secrets extension | Per execution environment. Short TTLs |

### Caching content based on request headers

When the response **varies** by a header (language, device type, country), that header must be part of the
**cache key**. Otherwise users get the wrong variant. Every extra key element divides the hit ratio (exercise `opt_2`):

- CloudFront **cache policy**: include only the headers, cookies and query strings that really change the
  response (e.g. `Accept-Language`, `CloudFront-Viewer-Country`, a `lang` query parameter). Normalize values
  when possible (e.g. map `Accept-Language` to a few languages with a CloudFront Function).
- **Origin request policy**: forward values the origin needs **without** adding them to the cache key.
- API Gateway: declare method request headers/query strings as **cache key parameters**.

> **Trap** — Adding `User-Agent`, `Authorization` or tracking parameters (`utm_*`) to the cache key
> → almost every request is a miss. The cache costs money and protects nothing.

## Optimizing messaging

- **SNS subscription filter policies**: subscribers receive only relevant messages, so there are fewer invocations and less
  discard logic (exercise `sns_1`). Filter on the message body when attributes are not available.
- **EventBridge patterns** and **Lambda event filtering** (event source mappings) drop events before they cost compute.
- **SQS**: **long polling** (fewer empty receives), **batch** APIs (`SendMessageBatch`/`DeleteMessageBatch`, up to 10),
  receive up to 10 messages per call, right-sized visibility timeouts (no duplicate work).
- **Kinesis**: aggregate small records (KPL), enhanced fan-out for many consumers, enough shards.
- Payloads: keep messages small, and use the claim-check pattern (S3) for big ones.

## Data access performance

- **DynamoDB**: model for your access patterns (Query, not Scan). Use `ProjectionExpression` and sparse GSIs.
  `BatchGetItem` for multiple keys. Eventually consistent reads (half the cost) when acceptable. On-demand for
  spiky traffic, provisioned + auto scaling for steady traffic. DAX for read-heavy hot items.
- **S3**: parallelize with multipart uploads and **byte-range** GETs, spread load across prefixes,
  **Transfer Acceleration** for distant clients, CloudFront for repeated reads, compress objects, use
  columnar formats (Parquet) for analytics with Athena.
- **RDS/Aurora**: read replicas for read scaling, RDS Proxy for connection reuse, cache hot queries.
- **SDK clients**: reuse them, tune timeouts and retries (standard/adaptive modes), use pagination with sensible page sizes (exercise `sdk_5`).

## Profiling and recommendations

| Question | Tool |
|---|---|
| Which downstream call makes requests slow? | **X-Ray** traces / subsegments, Application Signals |
| How much CPU/memory does my function use, and how do cold starts behave? | **Lambda Insights**, REPORT lines in Logs Insights |
| Which memory size is optimal? | **Lambda Power Tuning**, **AWS Compute Optimizer** |
| Is my EC2/ECS sizing right? | Compute Optimizer, Container Insights |
| Where does code spend CPU time? | Profilers (e.g. CodeGuru Profiler in older questions), language profilers |
| Account-level best-practice checks | Trusted Advisor |

## Cost levers for developers

- Right-size Lambda memory, use **arm64**, cut duration (reuse connections, avoid waiting).
- Choose the right **DynamoDB capacity mode**. Set **S3 lifecycle** rules or Intelligent-Tiering.
- Set **CloudWatch Logs retention** and avoid DEBUG logs in production. Prefer **EMF** over many `PutMetricData` calls.
- Use **VPC gateway endpoints** (free) for S3/DynamoDB instead of NAT gateway data processing.
- Cache to reduce backend calls. Batch requests. Filter events early.
- Use **HTTP APIs** instead of REST APIs when their features suffice. Use Express workflows for high-volume short workflows.
- **Compute Savings Plans** cover Lambda and Fargate for steady usage (a commitment-based discount).

## Hands-on

| Exercise | Skill |
|---|---|
| `opt_1` | Lambda cost per invocation, finding the cheapest memory under a latency target |
| `opt_2` | Cache keys based on headers/query strings, hit ratio, CloudFront cache policy |
| `lambda_2`, `lambda_6`, `sns_1`, `sdk_5` | Reuse, concurrency math, filter policies, SDK tuning |

## Summary

- Lambda: memory = CPU. Right-size with Power Tuning/Compute Optimizer. arm64. Initialize once. Provisioned concurrency/SnapStart for cold starts.
- Cache at every layer. Include only the headers that change the response in the cache key, and forward others with origin request policies.
- Messaging: SNS filter policies, EventBridge/Lambda event filtering, SQS long polling and batching.
- Data: Query not Scan, projections, DAX/ElastiCache, S3 multipart/byte ranges/CloudFront, RDS Proxy.
- Profile with X-Ray and Lambda Insights. Cut costs with retention, endpoints, batching and the right capacity modes.

## Check yourself

1. A CPU-bound function runs 2 s at 128 MB. What should you try first, and with which tool?
2. A localized website served by CloudFront shows French pages to English users. What is wrong?
3. A Lambda function subscribed to an SNS topic discards 90% of messages. How do you cut cost?
4. Which two SQS settings reduce the number of API calls per processed message?
5. How do you determine the minimum memory a function needs to meet a 200 ms latency target at the lowest cost?

<details><summary>Answers</summary>

1. Increase memory (more CPU). Use **Lambda Power Tuning** (or Compute Optimizer) to find the best cost/speed point.
2. `Accept-Language` (or the language parameter) is **not in the cache key**, so one language variant is served to everyone. Add it to the cache policy, normalized to a few values.
3. Add an **SNS subscription filter policy** so that only relevant messages invoke the function.
4. **Long polling** (`WaitTimeSeconds`) and **batching** (receive/delete up to 10 messages per call).
5. Run Power Tuning (or load tests) at several memory sizes. Keep the configurations meeting 200 ms and pick the cheapest one (exercise `opt_1`).

</details>

## Further reading

- [Lambda performance optimization](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [AWS Lambda Power Tuning](https://github.com/alexcasalboni/aws-lambda-power-tuning)
- [CloudFront cache key and origin requests](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/understanding-the-cache-key.html)
- [Lambda event filtering](https://docs.aws.amazon.com/lambda/latest/dg/invocation-eventfiltering.html)
- [AWS Compute Optimizer](https://docs.aws.amazon.com/compute-optimizer/latest/ug/what-is-compute-optimizer.html)
