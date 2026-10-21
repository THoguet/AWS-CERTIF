# Monitoring and logging with CloudWatch

> **In this chapter**
> - Logging vs monitoring vs observability
> - CloudWatch metrics: namespaces, dimensions, resolution, custom metrics, Embedded Metric Format
> - Alarms: evaluation (M out of N), missing data, actions, composite alarms
> - CloudWatch Logs: retention, metric filters, subscription filters, Logs Insights, data protection
> - Structured logging, dashboards, Application Signals, the CloudWatch agent
> - CloudTrail, and alerting on quotas, deployments and events
>
> **Exam weight**: Domain 4 Tasks 4.1/4.2 (log queries, custom metrics, EMF, dashboards, structured logging,
> notification alerts) · **Exercises**: `cw_1`–`cw_5` · **Quiz**: `uv run awslings quiz monitoring`

## Logging, monitoring, observability

- **Logging**: recording discrete events with context (what happened, to which request).
- **Monitoring**: collecting **metrics**, watching them against thresholds (alarms, dashboards). It tells you *that* something is wrong.
- **Observability**: being able to answer *why* from the outside, by correlating **logs, metrics and traces**
  (the three pillars), plus structured context (request ids, user ids).

## CloudWatch metrics

- A metric = **namespace** (`AWS/Lambda`, `AWS/SQS`, or your own like `Shop/Checkout`) + **name** + up to
  **30 dimensions** (`FunctionName=checkout`). Each distinct dimension combination is a separate metric.
- **Statistics**: `Sum`, `Average`, `Minimum`, `Maximum`, `SampleCount`, **percentiles** (`p50`, `p90`, `p99`).
  Use percentiles for latency: averages hide tail latency.
- **Resolution**: standard metrics are **1-minute**. **High-resolution** custom metrics keep **1-second** data
  (`StorageResolution=1`) for alarms on 10 s or 30 s periods. EC2 sends metrics every **5 minutes** by default
  (basic monitoring), **1 minute** with detailed monitoring.
- **Retention**: 1-second data for 3 hours, 1-minute data for 15 days, 5-minute data for 63 days, 1-hour data for 455 days.
- **What EC2 does not report by default**: **memory**, disk space usage, processes. Install the **CloudWatch
  agent** (also collects logs, StatsD/collectd metrics).
- **Metric math** (e.g. error rate = Errors / Invocations × 100), **anomaly detection** bands, **Metric Streams**
  (continuous export to Firehose or partners).

### Custom metrics

```python
cw.put_metric_data(Namespace="Shop/Checkout", MetricData=[{
    "MetricName": "CheckoutLatency", "Value": 412.5, "Unit": "Milliseconds",
    "Dimensions": [{"Name": "PaymentProvider", "Value": "stripe"}],
    "StorageResolution": 1}])                        # batch many data points per call (exercise cw_1)
```

### Embedded Metric Format (EMF)

From Lambda (or containers), **print** a structured JSON log line. CloudWatch extracts metrics from it
**asynchronously**: no API call latency, no throttling, and the log line keeps its context for Logs
Insights (exercise `cw_2`):

```json
{"_aws": {"Timestamp": 1767225600000,
          "CloudWatchMetrics": [{"Namespace": "Shop", "Dimensions": [["Service"]],
                                 "Metrics": [{"Name": "Latency", "Unit": "Milliseconds"}]}]},
 "Service": "checkout", "Latency": 87, "requestId": "c6af9ac6-7b61-11e6-9a41-93e8deadbeef"}
```

> **Exam tip** — "Publish custom metrics from Lambda **without adding latency**, keeping high-cardinality
> context searchable" → **Embedded Metric Format** (e.g. Powertools Metrics).

## Alarms

```text
Metric: AWS/Lambda Errors (Sum), Period 60 s, EvaluationPeriods 3, DatapointsToAlarm 2, Threshold >= 1
→ ALARM when 2 of the last 3 one-minute periods have at least one error
```

- States: `OK`, `ALARM`, `INSUFFICIENT_DATA`.
- **M out of N** (`DatapointsToAlarm` / `EvaluationPeriods`) avoids alerting on a single blip.
- **`TreatMissingData`**: `missing` (default), `notBreaching` (no data means OK, e.g. no errors when there is no traffic), `breaching`, `ignore`.
- **Actions**: SNS (email, SMS, chat, Lambda...), Auto Scaling policies, **EC2 actions** (stop, terminate,
  reboot, **recover**), Systems Manager OpsItems/incidents. Also `OKActions` and `InsufficientDataActions` (exercise `cw_3`).
- **Composite alarms** combine alarms with AND/OR/NOT, which reduces alert noise ("page only if errors AND latency are high").
- Alarms can watch metric math expressions and anomaly detection bands. Billing alarms live in **us-east-1**.

## CloudWatch Logs

- **Log groups** (one per application/function: `/aws/lambda/checkout`) contain **log streams** (one per
  instance/container/execution environment) of **log events**.
- **Retention**: by default logs **never expire**. Set a retention period (1 day to 10 years) to control cost.
  Optional **KMS encryption** per log group. Log classes: Standard and Infrequent Access (cheaper, fewer features).
- **Metric filters**: count or extract values from matching log events into a metric (then alarm on it).
  Patterns: `"ERROR"`, `[ip, user, ...]`, JSON `{ $.level = "ERROR" && $.service = "checkout" }`. They only apply
  to events ingested **after** creation (exercise `cw_4`).
- **Subscription filters**: stream matching log events in near real time to **Lambda**, **Kinesis Data
  Streams**, **Firehose** or **OpenSearch** (also cross-account through log destinations).
- **Export to S3** (`CreateExportTask`): batch, not real time. For continuous export use a subscription filter to Firehose.
- **Live Tail**: interactive real-time streaming of logs in the console/CLI.
- **Data protection policies**: detect and **mask** sensitive data (emails, credentials, card numbers) at ingestion.
- **Log anomaly detection** and **pattern analysis** surface unusual log patterns.

### CloudWatch Logs Insights

A query language for interactive analysis, with auto-discovered fields (`@timestamp`, `@message`,
`@logStream`, JSON fields, and Lambda's `@type`, `@requestId`, `@duration`, `@billedDuration`,
`@maxMemoryUsed`, `@initDuration`):

```text
# 10 slowest invocations
filter @type = "REPORT" | fields @requestId, @duration | sort @duration desc | limit 10

# errors per 5 minutes
filter @message like /ERROR/ | stats count(*) as errors by bin(5m)

# cold starts per hour and their average init time
filter @type = "REPORT" and ispresent(@initDuration)
| stats count(*) as coldStarts, avg(@initDuration) by bin(1h)

# JSON logs: top error types
filter level = "ERROR" | stats count(*) by error.type | sort count(*) desc

# extract fields from unstructured text
parse @message "user=* action=*" as user, action | stats count(*) by action
```

Queries can span several log groups. Results can be added to dashboards. You pay per GB scanned.

## Structured logging

- **JSON, one object per line**: `timestamp`, `level`, `service`, `message`, **`correlation_id`** /
  request id, and business keys. It is directly queryable and filterable (exercise `cw_5`).
- **Correlation ids** propagate across services (HTTP headers, message attributes) so you can follow one
  transaction end to end (X-Ray trace ids too).
- **Log levels** (DEBUG/INFO/WARN/ERROR) are configurable per environment. Lambda supports **JSON log format** and
  application/system **log-level filtering** natively. Powertools Logger adds context automatically.
- Never log secrets or unnecessary PII (chapter 14).

## Dashboards and insights

- **Dashboards**: metrics, alarms, Logs Insights results. Cross-account and cross-Region.
  **Automatic dashboards** per service.
- **Application Signals** (successor of ServiceLens): application performance monitoring with service maps,
  SLOs and correlated metrics/traces/logs, built on OpenTelemetry/X-Ray data.
- **Container Insights** (ECS/EKS), **Lambda Insights** (enhanced function metrics via an extension),
  **Contributor Insights** (top-N contributors, e.g. the noisiest IPs or hottest DynamoDB keys),
  **CloudWatch RUM** (real user monitoring for web apps), **Synthetics** canaries (chapter 19).

## AWS CloudTrail

Records **API calls** made in your account (console, CLI, SDK, services): who, when, from where, what parameters, result.

| Event type | Content | Default |
|---|---|---|
| **Management events** | Control-plane operations (CreateBucket, PutBucketPolicy, CreateFunction, AssumeRole...) | Logged. **Event history: 90 days, free** |
| **Data events** | Resource-level operations: S3 object GET/PUT, Lambda Invoke, DynamoDB item operations... | **Off**, enable on a trail (extra cost) |
| **Insights events** | Unusual API call rates or error rates | Optional |

- A **trail** delivers events to **S3** (long-term retention, optional CloudWatch Logs delivery), can be
  multi-Region and **organization-wide**, with **log file integrity validation**.
- **CloudTrail Lake**: store and query events with SQL.
- **EventBridge** receives CloudTrail management events, so you can react to API calls (e.g. alert when a security group opens port 22).

> **Exam tip** — "**Who** deleted / changed this resource?" → **CloudTrail**. "Why is the app slow?" →
> CloudWatch metrics + **X-Ray**. "Log every S3 object download" → CloudTrail **data events** (or S3 server access logs).

## Notification alerts for specific actions

| Alert on | How |
|---|---|
| Approaching a **service quota** | Service Quotas usage metrics (`AWS/Usage`) + CloudWatch alarms; Trusted Advisor checks |
| **Deployment** finished/failed | EventBridge events from CodeDeploy / CodePipeline / CloudFormation → SNS or chat |
| An AWS service issue affecting you | **AWS Health** events via EventBridge |
| Cost overrun | **AWS Budgets** alerts, billing alarms |
| A specific API call (e.g. root login, policy change) | CloudTrail → EventBridge rule → SNS/Lambda |
| An application error pattern | Metric filter → alarm → SNS |

## Hands-on

| Exercise | Skill |
|---|---|
| `cw_1` | Custom metrics with dimensions, units, high resolution, batching |
| `cw_2` | Embedded Metric Format log lines |
| `cw_3` | Alarms: M out of N, TreatMissingData, actions, a DLQ alarm |
| `cw_4` | Logs Insights queries and a metric filter |
| `cw_5` | Structured JSON logging with correlation ids |

Optional lab: `labs/lab05-observability`.

## Summary

- Metrics: namespace + name + dimensions. Percentiles for latency. 1-minute standard, 1-second high resolution. EC2 memory needs the agent.
- Custom metrics via PutMetricData (batched) or **EMF** (asynchronous, from logs).
- Alarms: M out of N, TreatMissingData, SNS/ASG/EC2 actions, composite alarms.
- Logs: set retention (default never expires), metric filters → metrics, subscription filters → Lambda/Kinesis/Firehose, Logs Insights queries.
- CloudTrail = API audit (management events 90 days free, data events opt-in). EventBridge for deployment/quota/health alerts.

## Check yourself

1. An alarm fires on a single error at 3 a.m. and wakes the on-call engineer. How do you make it less noisy without missing real incidents?
2. Which EC2 metrics are not available without the CloudWatch agent?
3. Write a Logs Insights query returning the number of log events containing "Timeout" per 10 minutes.
4. A Lambda function must publish a metric per customer tier with minimal latency. Which approach?
5. A table was deleted in production. Where do you find who did it?

<details><summary>Answers</summary>

1. Use **M out of N** evaluation (e.g. 3 of 5 periods), a sensible threshold or an error **rate** (metric math),
   `TreatMissingData=notBreaching`, or a **composite alarm** combining several signals.
2. Memory utilization, disk space usage (and other OS-level metrics such as processes).
3. `filter @message like /Timeout/ | stats count(*) by bin(10m)`
4. **Embedded Metric Format** (print a JSON log line with the `_aws` metadata). CloudWatch extracts the metric asynchronously.
5. **CloudTrail** (event history for the last 90 days, or the trail in S3/CloudTrail Lake): the `DeleteTable` event shows the identity.

</details>

## Further reading

- [CloudWatch user guide](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html)
- [Embedded Metric Format specification](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Embedded_Metric_Format_Specification.html)
- [Logs Insights query syntax](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax.html)
- [Using CloudWatch alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html)
- [CloudTrail concepts](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-concepts.html)
