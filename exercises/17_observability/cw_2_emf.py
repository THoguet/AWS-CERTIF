"""
Exercise cw_2 — CloudWatch Embedded Metric Format (EMF)
=======================================================
Book: chapter 20, "Embedded Metric Format" (book/src/ch20-monitoring-logging.md)
Exam: Domain 4 · Task 4.1 (implementing custom metrics, e.g. CloudWatch EMF)

From a Lambda function, calling PutMetricData adds latency and cost to
every invocation. With EMF you just PRINT a structured JSON log line.
CloudWatch Logs extracts the metrics asynchronously, and the log line
stays searchable in Logs Insights with all its context (request id...).

    {
      "_aws": {
        "Timestamp": 1767225600000,
        "CloudWatchMetrics": [{
          "Namespace": "Shop",
          "Dimensions": [["Service", "Operation"]],
          "Metrics": [{"Name": "Latency", "Unit": "Milliseconds"}]
        }]
      },
      "Service": "checkout", "Operation": "pay",   ← dimension values
      "Latency": 87,                                ← metric values
      "requestId": "abc-123"                        ← extra context (not a metric)
    }

(Libraries: aws-embedded-metrics, Powertools for AWS Lambda "Metrics".)

Your task
---------
Implement `emf_line(namespace, dimensions, metrics, timestamp_ms, **context)`:
  * dimensions: {"Service": "checkout", "Operation": "pay"},
  * metrics: {"Latency": (87, "Milliseconds"), "Items": (3, "Count")},
  * extra keyword arguments are added at the root as context,
and return the JSON string.
"""

# I AM NOT DONE

import json


def emf_line(namespace: str, dimensions: dict, metrics: dict, timestamp_ms: int, **context) -> str:
    return json.dumps({"namespace": namespace, **dimensions, **metrics})  # TODO: follow the EMF specification


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run cw_2
# =============================================================================


def test_emf_document():
    line = emf_line(
        "Shop",
        {"Service": "checkout", "Operation": "pay"},
        {"Latency": (87, "Milliseconds"), "Items": (3, "Count")},
        1767225600000,
        requestId="abc-123",
    )
    doc = json.loads(line)
    directive = doc["_aws"]["CloudWatchMetrics"][0]
    assert doc["_aws"]["Timestamp"] == 1767225600000
    assert directive["Namespace"] == "Shop"
    assert directive["Dimensions"] == [["Service", "Operation"]]
    assert directive["Metrics"] == [{"Name": "Latency", "Unit": "Milliseconds"}, {"Name": "Items", "Unit": "Count"}]
    assert (doc["Service"], doc["Operation"]) == ("checkout", "pay")
    assert (doc["Latency"], doc["Items"]) == (87, 3)
    assert doc["requestId"] == "abc-123"


def test_single_line():
    line = emf_line("Shop", {"Service": "a"}, {"Latency": (1, "Milliseconds")}, 0)
    assert "\n" not in line, "one log event = one line"
