"""
Exercise cw_4 — CloudWatch Logs Insights and metric filters
===========================================================
Book: chapter 20, "CloudWatch Logs" (book/src/ch20-monitoring-logging.md)
Exam: Domain 4 · Task 4.1 (languages for log queries, querying logs to find relevant data)

Logs Insights queries are pipelines of commands:
    fields, filter, stats ... by ..., sort, limit, parse, dedup, display
With automatic fields such as @timestamp, @message, @logStream, and for
Lambda's REPORT lines @type, @requestId, @duration, @billedDuration,
@maxMemoryUsed and @initDuration (only present on cold starts).

A METRIC FILTER turns matching log events into a CloudWatch metric (that
you can alarm on). It only applies to events ingested AFTER its creation.

Your task
---------
Write three queries:
  * SLOWEST_INVOCATIONS: the 10 slowest invocations (request id + duration),
  * ERRORS_PER_5_MIN: number of log events containing "ERROR" per 5-minute bin,
  * COLD_STARTS_PER_HOUR: count of cold starts and average init duration per hour,
and implement `create_error_metric(logs, log_group)`: metric filter
"app-errors" counting events containing ERROR as metric AppErrors
(namespace Shop, value 1).
"""

SLOWEST_INVOCATIONS = """
filter @type = "REPORT"
| fields @requestId, @duration
| sort @duration desc
| limit 10
"""

ERRORS_PER_5_MIN = """
filter @message like /ERROR/
| stats count(*) as errors by bin(5m)
"""

COLD_STARTS_PER_HOUR = """
filter @type = "REPORT" and ispresent(@initDuration)
| stats count(*) as coldStarts, avg(@initDuration) as avgInit by bin(1h)
"""


def create_error_metric(logs, log_group: str) -> None:
    logs.put_metric_filter(
        logGroupName=log_group,
        filterName="app-errors",
        filterPattern='"ERROR"',
        metricTransformations=[{"metricName": "AppErrors", "metricNamespace": "Shop", "metricValue": "1"}],
    )


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run cw_4
# =============================================================================
import re  # noqa: E402

import boto3  # noqa: E402


def _norm(query):
    return re.sub(r"\s+", " ", query).strip()


def test_slowest_invocations():
    q = _norm(SLOWEST_INVOCATIONS)
    assert re.search(r'filter @type\s*=\s*"REPORT"', q)
    assert re.search(r"sort @duration desc", q)
    assert re.search(r"limit 10\b", q)


def test_errors_per_5_min():
    q = _norm(ERRORS_PER_5_MIN)
    assert re.search(r"filter @message like /ERROR/", q)
    assert re.search(r"stats count\(\*\).* by bin\(5m\)", q)


def test_cold_starts():
    q = _norm(COLD_STARTS_PER_HOUR)
    assert re.search(r"ispresent\(@initDuration\)", q)
    assert re.search(r"avg\(@initDuration\)", q)
    assert re.search(r"by bin\(1h\)", q)


def test_metric_filter(aws):
    logs = boto3.client("logs")
    logs.create_log_group(logGroupName="/aws/lambda/checkout")
    create_error_metric(logs, "/aws/lambda/checkout")
    flt = logs.describe_metric_filters(logGroupName="/aws/lambda/checkout")["metricFilters"][0]
    assert flt["filterName"] == "app-errors"
    assert "ERROR" in flt["filterPattern"]
    assert flt["metricTransformations"][0]["metricName"] == "AppErrors"
    assert flt["metricTransformations"][0]["metricNamespace"] == "Shop"
