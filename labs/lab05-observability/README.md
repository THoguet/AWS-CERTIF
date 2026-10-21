# Lab 05 — Observability: traces, logs and metrics

> **Goal**: instrument a checkout API and use the three pillars together: **X-Ray traces** (where
> does the time go, which component fails), **structured logs** queried with Logs Insights (what
> exactly happened), and **metrics** from Embedded Metric Format, with an **alarm** fed by a metric
> filter and a **dashboard**.
>
> **Book**: ch20 (CloudWatch metrics, logs, alarms, EMF), ch21 (X-Ray) · **Exercises**: `cw_2`,
> `cw_3`, `cw_4`, `cw_5`, `xray_1` · **Time**: 1.5 h · **Cost**: < $0.20 if deleted the same day

```text
curl ─► API Gateway (REST, stage dev, X-Ray tracing on) ─► Lambda (active tracing)
            └ subsegment "checkout" (annotations: customer_tier, correlation_id)
                 ├ subsegment "payment-provider" (simulated latency / failure)
                 └ DynamoDB PutItem (boto3 patched by the X-Ray SDK)
logs ─► /aws/lambda/dva-lab05-checkout (7-day retention) ─► metric filter {$.level = "ERROR"} ─► alarm (2 of 3 min) ─► SNS
EMF log lines ─► metrics DvaLab05 OrderValue / PaymentLatency (Service, Tier) ─► dashboard
```

Files: `template.yaml`, `src/app.py` (+ `requirements.txt` for the X-Ray SDK), `scripts/traffic.sh`,
`sampling-rule.json`, `tests/`.

> The X-Ray SDKs entered maintenance mode in February 2026 (end of support February 2027). AWS
> recommends OpenTelemetry (ADOT) for new code. The concepts this lab shows (segments, subsegments,
> annotations, sampling, the trace map) are the same, and they are what the DVA-C02 exam asks about.

## 1. Read before you deploy

- `template.yaml`: `TracingEnabled` on the API stage, `Tracing: Active` on the function, a log group
  with a retention period, the metric filter, the alarm (M out of N, `TreatMissingData`), the dashboard.
- `src/app.py`: the JSON `log()` lines, the EMF line, and the two subsegments. Annotations go on the
  `checkout` subsegment because Lambda owns the function segment: the SDK cannot add annotations to it.

## 2. Deploy

```bash
cd labs/lab05-observability
sam build && sam deploy --guided     # stack dva-lab05, Region eu-west-3, AlarmEmail = your email
```

Confirm the SNS subscription email, then:

```bash
out() { aws cloudformation describe-stacks --stack-name dva-lab05 \
        --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }
API=$(out ApiUrl); LOGS=$(out LogGroupName); ALARM=$(out AlarmName)

curl -s -i -X POST "$API/checkout?tier=gold&amount=42.5&delay=0.3" -H "X-Correlation-Id: first-order"
bash scripts/traffic.sh "$API" 120     # about 1 minute: mixed tiers, slow payments, ~10% failures (HTTP 502)
```

## 3. Traces

Open **CloudWatch → X-Ray traces → Trace map**:

- Nodes for the client, the API Gateway stage, the Lambda service and function, and DynamoDB, with
  average latency, request rate and the share of errors and faults (red = 5xx faults).
- Open **Traces** and filter with these expressions:

  ```text
  annotation.customer_tier = "gold"
  annotation.customer_tier = "gold" AND fault
  responsetime > 2
  annotation.correlation_id = "lab05-7"
  ```

- Open a slow trace: the timeline shows the `payment-provider` subsegment taking 2.5 s, next to the
  short DynamoDB call. Open a failed trace: the exception is recorded on the subsegment.

The same search from the CLI:

```bash
START=$(python3 -c 'import time; print(int(time.time()) - 1800)'); END=$(python3 -c 'import time; print(int(time.time()))')
aws xray get-trace-summaries --start-time "$START" --end-time "$END" \
    --filter-expression 'annotation.customer_tier = "gold" AND fault' \
    --query 'TraceSummaries[].[Id, ResponseTime, HasFault]' --output table
```

With the **default sampling rule** (the first request each second, then 5% of the rest) and this low
traffic, almost every request is traced. To trace everything during an investigation, add a rule
without redeploying:

```bash
aws xray create-sampling-rule --cli-input-json file://sampling-rule.json
aws xray get-sampling-rules --query 'SamplingRuleRecords[].SamplingRule.[RuleName, Priority, FixedRate, ReservoirSize]' --output table
```

## 4. Logs

Open **CloudWatch → Logs Insights**, choose the `/aws/lambda/dva-lab05-checkout` log group, and run:

```text
# slowest payments
filter message = "order placed" | fields @timestamp, tier, latency_ms, correlation_id | sort latency_ms desc | limit 10

# errors per tier
filter level = "ERROR" | stats count(*) as errors by tier

# orders per tier every 5 minutes
filter message = "order placed" | stats count(*) by tier, bin(5m)

# one request, end to end (use a correlation id from the traffic script)
filter correlation_id = "lab05-7" | fields @timestamp, level, message, trace_id

# Lambda's own REPORT lines: duration percentiles and cold starts
filter @type = "REPORT" | stats avg(@duration), pct(@duration, 99), count(@initDuration) as coldStarts by bin(5m)
```

Copy a `trace_id` from a log line and paste it into the X-Ray console search: logs and traces point
to each other. From the terminal: `aws logs tail "$LOGS" --follow --filter-pattern '{ $.level = "ERROR" }'`.

## 5. Metrics and the alarm

- **CloudWatch → Metrics → All metrics → DvaLab05 → Service, Tier**: `OrderValue` and
  `PaymentLatency` were created from the EMF log lines, with no `PutMetricData` call in the code.
  `aws cloudwatch list-metrics --namespace DvaLab05` lists them.
- Trigger the alarm: errors in at least 2 of 3 consecutive minutes.

  ```bash
  for i in 1 2 3 4 5 6 7 8; do curl -s -o /dev/null -X POST "$API/checkout?fail=true"; sleep 15; done
  aws cloudwatch describe-alarms --alarm-names "$ALARM" --query 'MetricAlarms[0].[StateValue, StateReason]'
  ```

  You receive an `ALARM` email, then an `OK` email a few minutes after you stop (no error lines =
  missing data, treated as not breaching).
- **CloudWatch → Dashboards → dva-lab05**: latency percentiles, order value per tier, both error
  counts, and a Logs Insights table.

## 6. Explore

- Compare the two error metrics on the dashboard: `AWS/Lambda Errors` counts failed invocations, and
  `CheckoutErrors` counts log lines matching a pattern. Which one can tell *why* it failed?
- Why does p99 look so different from p50 after the traffic script?
- In the function's IAM role, find the X-Ray permissions that `Tracing: Active` added
  (`xray:PutTraceSegments`, `xray:PutTelemetryRecords`).

## Teardown

```bash
aws xray delete-sampling-rule --rule-name dva-lab05-all-checkouts   # only if you created it
sam delete --stack-name dva-lab05
```

The stack owns the log group, so it is deleted with it. Traces expire on their own after 30 days.
Custom metrics stop costing anything once no new data arrives.

## What to remember for the exam

- Tracing needs **both** sides: enable it (API Gateway stage, `Tracing: Active` on Lambda, the daemon
  or collector elsewhere) **and** IAM permissions to send segments. Downstream calls become
  subsegments only if the clients are instrumented (`patch_all`, OpenTelemetry auto-instrumentation).
- **Annotations** are indexed and searchable with filter expressions. **Metadata** is not. In Lambda,
  add them to a subsegment.
- Default sampling: 1 request per second + 5%. Sampling rules change without redeploying.
- **EMF** publishes metrics asynchronously from log lines (no latency, no throttling). Metric
  filters turn log patterns into metrics, but only for events ingested **after** the filter exists.
- Alarms: M out of N (`DatapointsToAlarm` / `EvaluationPeriods`), `TreatMissingData`, `AlarmActions`
  and `OKActions`. Use percentiles for latency.
- Set log **retention**: by default, CloudWatch Logs keeps logs forever.
