"""
Exercise lambda_4 — SQS batches and partial failures
====================================================
Book: chapter 5, "Event source mappings" (book/src/ch05-lambda.md)
Exam: Domain 1 · Task 1.2 (event source mapping, handling errors by using code)

Lambda polls the queue and invokes your function with a BATCH of messages
(up to 10 for FIFO queues, up to 10,000 for standard queues with a batching
window). By default, if the function raises, the WHOLE batch returns to
the queue and is retried, including the messages that were processed fine.
That means duplicates, and eventually everything ends up in the DLQ.

The fix: enable `ReportBatchItemFailures` on the event source mapping and
return only the IDs of the failed messages:

    {"batchItemFailures": [{"itemIdentifier": "<messageId>"}]}

Your task
---------
Implement `handler(event, context)`: process every record with
`process(order)` (order = the JSON-decoded body). Never let one bad
message fail the whole batch. Report only the failed message IDs.
"""

import json

PROCESSED = []


def process(order: dict) -> None:
    if order.get("quantity", 0) <= 0:
        raise ValueError(f"invalid quantity in order {order.get('id')}")
    PROCESSED.append(order["id"])


def handler(event, context):
    failures = []
    for record in event["Records"]:
        try:
            process(json.loads(record["body"]))
        except Exception:
            failures.append({"itemIdentifier": record["messageId"]})
    return {"batchItemFailures": failures}


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run lambda_4
# =============================================================================


def _sqs_event(*orders):
    return {
        "Records": [
            {
                "messageId": f"msg-{i}",
                "receiptHandle": f"handle-{i}",
                "body": json.dumps(order),
                "eventSource": "aws:sqs",
                "eventSourceARN": "arn:aws:sqs:eu-west-3:123456789012:orders",
            }
            for i, order in enumerate(orders)
        ]
    }


def setup_function():
    PROCESSED.clear()


def test_all_good():
    assert handler(_sqs_event({"id": "a", "quantity": 1}, {"id": "b", "quantity": 2}), None) == {"batchItemFailures": []}
    assert PROCESSED == ["a", "b"]


def test_reports_only_failed_messages():
    event = _sqs_event({"id": "a", "quantity": 1}, {"id": "b", "quantity": 0}, {"id": "c", "quantity": 5})
    assert handler(event, None) == {"batchItemFailures": [{"itemIdentifier": "msg-1"}]}
    assert PROCESSED == ["a", "c"], "good messages after a bad one must still be processed"


def test_malformed_json_is_a_failure_too():
    event = _sqs_event({"id": "a", "quantity": 1})
    event["Records"][0]["body"] = "not json"
    assert handler(event, None) == {"batchItemFailures": [{"itemIdentifier": "msg-0"}]}
