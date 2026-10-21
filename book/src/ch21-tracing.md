# Tracing with X-Ray and OpenTelemetry

> **In this chapter**
> - Distributed tracing: traces, segments, subsegments, trace headers
> - AWS X-Ray: SDK, daemon, enabling tracing on Lambda, API Gateway, ECS, Beanstalk, EC2
> - Annotations vs metadata, sampling rules, filter expressions, groups, the service map
> - OpenTelemetry and ADOT, and the X-Ray SDK maintenance timeline
> - Troubleshooting missing traces
>
> **Exam weight**: Domain 4 Tasks 4.1 (service maps) and 4.2 (distributed tracing, annotations)
> · **Exercises**: `xray_1` · **Quiz**: `uv run awslings quiz xray`

## Distributed tracing

In a distributed system, one user request crosses API Gateway, several Lambda functions, queues and
databases. Logs per service cannot show the **whole path** or **where the time goes**. A **trace** can.

```text
Trace 1-6716a2f1-3f1c8a1e9b2d4c5e6f708192            (one request, end to end)
├─ Segment: API Gateway "orders-api/prod"        120 ms
│  └─ Segment: Lambda "create-order"              110 ms
│     ├─ Subsegment: DynamoDB PutItem              18 ms
│     ├─ Subsegment: payment-provider (HTTP)       75 ms   ← the slow part
│     └─ Subsegment: SQS SendMessage                6 ms
```

- **Trace**: all the data of one request, identified by a trace id.
- **Segment**: the work done by one service for that request (timing, HTTP data, errors).
- **Subsegment**: a finer unit inside a segment: a downstream call (AWS SDK, HTTP, SQL) or a block of your code.
- **Trace header** `X-Amzn-Trace-Id: Root=1-...;Parent=...;Sampled=1` is propagated between services
  (HTTP headers, SQS/SNS message attributes) so segments join the same trace.

## AWS X-Ray components

| Component | Role |
|---|---|
| **SDK / instrumentation** | Creates segments and subsegments in your code. Patches libraries (boto3, requests, SQL clients) to trace downstream calls automatically |
| **X-Ray daemon** (or the CloudWatch agent / ADOT collector) | Listens on **UDP port 2000**, buffers segments and sends them in batches to the X-Ray API |
| **X-Ray API** | `PutTraceSegments`, `PutTelemetryRecords`, `GetSamplingRules`... |
| **Console** | **Trace map / service map**, trace list and timeline, analytics, insights |

### Enabling tracing per compute

| Where | How | Permissions |
|---|---|---|
| **Lambda** | `TracingConfig: Active` (SAM `Tracing: Active`). The daemon is built in. Instrument the code for subsegments | Execution role: `xray:PutTraceSegments`, `xray:PutTelemetryRecords` (`AWSXRayDaemonWriteAccess`) |
| **API Gateway** | Enable X-Ray tracing on the **stage** | — |
| **Elastic Beanstalk** | Option `XRayEnabled: true` (namespace `aws:elasticbeanstalk:xray`) or `.ebextensions` | Instance profile with X-Ray write access |
| **ECS** | Run the daemon (or ADOT collector) as a **sidecar container**, open UDP 2000, set `AWS_XRAY_DAEMON_ADDRESS` | **Task role** with X-Ray write access |
| **EC2 / on-premises** | Install and run the daemon (user data) | Instance profile / credentials with X-Ray write access |

Services such as SNS, SQS, EventBridge, Step Functions and ALB propagate or add tracing data.

Environment variables to know: `AWS_XRAY_DAEMON_ADDRESS` (where to send segments), `AWS_XRAY_CONTEXT_MISSING`
(behavior when there is no active segment: `LOG_ERROR`, `RUNTIME_ERROR`, `IGNORE_ERROR`),
`_X_AMZN_TRACE_ID` (set by Lambda for the current invocation).

## Annotations vs metadata

```python
from aws_xray_sdk.core import xray_recorder, patch_all
patch_all()                                               # trace boto3, requests... automatically

def handler(event, context):
    with xray_recorder.in_subsegment("checkout") as subsegment:
        subsegment.put_annotation("customer_tier", event["tier"])     # indexed → filterable
        subsegment.put_metadata("order", event, "shop")               # not indexed → debugging details
        with xray_recorder.in_subsegment("payment-provider"):
            pay(event)
```

> **Lambda detail** — Lambda creates the function's segment itself. The SDK sees it as a read-only
> *facade segment*, so `xray_recorder.put_annotation()` called outside a subsegment raises
> `FacadeSegmentMutationException`. Annotate a subsegment you create, as above. On EC2, ECS or
> Beanstalk, your code (or a framework middleware) creates the segment and can annotate it directly.

| | **Annotations** | **Metadata** |
|---|---|---|
| Types | String, number, boolean | Any JSON value (objects, arrays) |
| Indexed | **Yes**: usable in **filter expressions** and groups | **No** |
| Limit | Up to 50 per trace | — |
| Use for | Customer tier, tenant id, order type, feature flag, anything you will **search** by | Payloads, responses, debug context |

> **Exam tip** — "Find all traces for premium customers / a given tenant" → record it as an
> **annotation**, then use a **filter expression**. Metadata cannot be searched.

Segments also carry **error** (4xx), **fault** (5xx) and **throttle** (429) flags, plus HTTP and AWS details.

## Sampling

Tracing every request is expensive and unnecessary. **Sampling rules** decide which requests are recorded:

- **Default rule**: the **first request each second** (reservoir = 1/s) **plus 5%** of the additional requests.
- **Custom rules** in the console/API, matched by service name/type, host, HTTP method, URL path, with
  their own reservoir and fixed rate. The SDKs fetch them centrally: **change sampling without redeploying code**.
- Sampled traces still capture all segments of a sampled request (the decision propagates in the trace header).

## Using traces

- **Trace map** (service map): nodes per service with latency, request rates and error/fault/throttle
  ratios (color-coded). Click through to traces.
- **Filter expressions**:

```text
service("checkout") { fault = true }
annotation.customer_tier = "gold" AND fault
responsetime > 2 AND http.url CONTAINS "/orders"
http.status = 429
```

- **Groups**: a saved filter expression with its own trace map and CloudWatch metrics (e.g. "gold customers").
- **Insights**: automatic anomaly detection on fault rates, with notifications.
- **Analytics**: response time distributions, comparisons between time ranges.
- CloudWatch **Application Signals** and **Transaction Search** build on the same trace data.

## OpenTelemetry and ADOT

- **OpenTelemetry (OTel)** is the vendor-neutral standard for traces, metrics and logs.
  **AWS Distro for OpenTelemetry (ADOT)** is AWS's supported distribution (SDKs, collector, a Lambda layer)
  that exports to X-Ray and CloudWatch (and other backends).
- The **X-Ray SDKs and daemon entered maintenance mode on 25 February 2026** (security fixes only) and
  reach **end of support on 25 February 2027**. AWS recommends migrating to OpenTelemetry. The **X-Ray
  service** itself continues and accepts OTel data. OTel span attributes become X-Ray annotations or metadata.
- For the exam the vocabulary is unchanged: segments, subsegments, annotations vs metadata, sampling,
  daemon on UDP 2000, service map.

## Troubleshooting missing traces

| Symptom | Check |
|---|---|
| No traces at all from Lambda | **Active tracing** enabled? Execution role allows `xray:PutTraceSegments` / `PutTelemetryRecords`? |
| No traces from EC2/ECS | Daemon/collector running? **UDP 2000** reachable? `AWS_XRAY_DAEMON_ADDRESS` correct? Instance profile / **task role** permissions? |
| Traces exist but downstream calls are missing | Libraries not **patched/instrumented** (`patch_all()`, OTel auto-instrumentation) |
| Only some requests traced | **Sampling** is working as designed. Add a custom sampling rule if you need more |
| Separate traces per service instead of one | Trace header not **propagated** (custom HTTP client, async hop without the header) |
| "SegmentNotFoundException / context missing" in logs | Code runs outside an active segment (`AWS_XRAY_CONTEXT_MISSING`) |

## Hands-on

| Exercise | Skill |
|---|---|
| `xray_1` | Annotations vs metadata, subsegments with exception recording, filter expressions |

Optional lab: `labs/lab05-observability` (enable tracing on API Gateway + Lambda, explore the trace map).

## Summary

- Trace = request end to end. Segment = one service. Subsegment = a downstream call or code block. Propagated by `X-Amzn-Trace-Id`.
- Lambda: Active tracing + IAM permissions. ECS: daemon sidecar + task role. Beanstalk: XRayEnabled. EC2: daemon + instance profile.
- Annotations are indexed (search with filter expressions). Metadata is not.
- Default sampling: 1 request/s + 5%. Custom rules change sampling without code changes.
- X-Ray SDKs are in maintenance mode (2026) → OpenTelemetry/ADOT. Same concepts.

## Check yourself

1. Which data should be an annotation: the full order JSON or the customer's subscription tier?
2. Traces from an ECS service never appear. Name two likely causes.
3. What does the default sampling rule record?
4. How do you see only traces that returned 5xx errors for the `checkout` service?
5. What replaces the X-Ray SDKs for new instrumentation?

<details><summary>Answers</summary>

1. The subscription tier (it should be searchable). The full order JSON belongs in metadata.
2. No X-Ray daemon/collector sidecar (or UDP 2000 not reachable / wrong daemon address), or the **task role** lacks X-Ray write permissions.
3. The first request each second, plus 5% of additional requests.
4. The filter expression `service("checkout") { fault = true }`.
5. **OpenTelemetry**, through the AWS Distro for OpenTelemetry (ADOT).

</details>

## Further reading

- [AWS X-Ray concepts](https://docs.aws.amazon.com/xray/latest/devguide/xray-concepts.html)
- [Using filter expressions](https://docs.aws.amazon.com/xray/latest/devguide/xray-console-filters.html)
- [Configuring sampling rules](https://docs.aws.amazon.com/xray/latest/devguide/xray-console-sampling.html)
- [X-Ray SDK and daemon support timeline](https://docs.aws.amazon.com/xray/latest/devguide/xray-sdk-daemon-timeline.html)
- [AWS Distro for OpenTelemetry](https://aws-otel.github.io/)
