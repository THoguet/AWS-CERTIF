"""
Exercise cw_1 — Publishing custom metrics
=========================================
Book: chapter 20, "CloudWatch metrics" (book/src/ch20-monitoring-logging.md)
Exam: Domain 4 · Tasks 4.1 / 4.2 (implementing code that emits custom metrics)

  * a metric lives in a NAMESPACE (custom ones must not start with "AWS/")
    and is identified by its name + DIMENSIONS (up to 30 per metric),
  * standard resolution = 1-minute granularity. HIGH resolution
    (StorageResolution=1) keeps 1-second data points, useful for alarms
    every 10 or 30 s (and costs more),
  * always set a Unit (Milliseconds, Count, Bytes...),
  * batch data points: one PutMetricData call can carry many metrics.
    Each API call costs money and counts against the API quota.
(The asynchronous alternative is the Embedded Metric Format, next exercise.)

Your task
---------
  * `record_latency(cw, latency_ms, provider)`: CheckoutLatency in
    namespace Shop/Checkout, dimensions PaymentProvider=<provider> and
    Stage=prod, unit Milliseconds, high resolution,
  * `record_orders(cw, counts)`: metric OrdersPlaced (Count) with one
    data point per country (dimension Country), in ONE API call.
"""

# I AM NOT DONE

NAMESPACE = "Shop/Checkout"


def record_latency(cw, latency_ms: float, provider: str) -> None:
    cw.put_metric_data(Namespace=NAMESPACE, MetricData=[{"MetricName": "CheckoutLatency", "Value": latency_ms}])  # TODO


def record_orders(cw, counts: dict[str, int]) -> None:
    for country, count in counts.items():  # TODO: one call per country is slow and expensive
        cw.put_metric_data(
            Namespace=NAMESPACE,
            MetricData=[{"MetricName": "OrdersPlaced", "Dimensions": [{"Name": "Country", "Value": country}], "Value": count, "Unit": "Count"}],
        )


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run cw_1
# =============================================================================
from unittest import mock  # noqa: E402

import boto3  # noqa: E402


def test_latency_metric(aws):
    cw = boto3.client("cloudwatch")
    with mock.patch.object(cw, "put_metric_data", wraps=cw.put_metric_data) as spy:
        record_latency(cw, 412.5, "stripe")
    datum = spy.call_args.kwargs["MetricData"][0]
    assert datum["Unit"] == "Milliseconds" and datum["StorageResolution"] == 1
    metrics = cw.list_metrics(Namespace=NAMESPACE, MetricName="CheckoutLatency")["Metrics"]
    assert len(metrics) == 1
    assert {(d["Name"], d["Value"]) for d in metrics[0]["Dimensions"]} == {("PaymentProvider", "stripe"), ("Stage", "prod")}


def test_orders_batched(aws):
    cw = boto3.client("cloudwatch")
    with mock.patch.object(cw, "put_metric_data", wraps=cw.put_metric_data) as spy:
        record_orders(cw, {"FR": 12, "DE": 7, "BE": 3})
    assert spy.call_count == 1, "send all data points in one call"
    countries = {m["Dimensions"][0]["Value"] for m in cw.list_metrics(Namespace=NAMESPACE, MetricName="OrdersPlaced")["Metrics"]}
    assert countries == {"FR", "DE", "BE"}
