"""
Exercise events_1 — EventBridge event patterns
==============================================
Book: chapter 9, "Amazon EventBridge" (book/src/ch09-messaging.md)
Exam: Domain 1 · Task 1.1 (event-driven patterns with Amazon EventBridge)

An event bus receives events, and RULES route them to targets (Lambda,
SQS, SNS, Step Functions, API destinations... up to 5 targets per rule)
when the event matches the rule's PATTERN.

Event envelope (what a pattern can match):
    {"source": "shop.orders", "detail-type": "OrderPlaced", "account": "...",
     "region": "...", "time": "...", "resources": [...], "detail": {...}}

Pattern rules: every field you list must match; values are arrays (OR);
content filters include prefix, suffix, anything-but, numeric ranges,
exists, wildcard...

Your task
---------
Write two patterns:
  * UPLOAD_PATTERN: S3 "Object Created" events (source "aws.s3") for the
    bucket "media-uploads" whose object key starts with "raw/",
  * BIG_ORDER_PATTERN: events from source "shop.orders" with detail-type
    "OrderPlaced", detail.amount >= 100 and detail.country not "TEST".
Then implement `route(events, sqs, bus, rule_name, pattern, queue_url)`.
"""

# I AM NOT DONE

import json

UPLOAD_PATTERN = {
    "source": ["aws.s3"],
    # TODO: detail-type, bucket name, key prefix
}

BIG_ORDER_PATTERN = {
    "source": "shop.orders",  # TODO: values must be lists
    # TODO: detail-type, amount >= 100, country is not TEST
}


def route(events, sqs, bus: str, rule_name: str, pattern: dict, queue_url: str) -> None:
    queue_arn = sqs.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["QueueArn"])["Attributes"]["QueueArn"]
    # TODO: create the rule on the bus, then add the queue as a target
    raise NotImplementedError


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run events_1
# =============================================================================
import boto3  # noqa: E402
import pytest  # noqa: E402


@pytest.fixture
def env(aws):
    events, sqs = boto3.client("events"), boto3.client("sqs")
    events.create_event_bus(Name="app")
    return events, sqs


def _received(sqs, url):
    return [json.loads(m["Body"])["detail"] for m in sqs.receive_message(QueueUrl=url, MaxNumberOfMessages=10).get("Messages", [])]


def test_upload_pattern(env):
    events, sqs = env
    url = sqs.create_queue(QueueName="uploads")["QueueUrl"]
    route(events, sqs, "app", "raw-uploads", UPLOAD_PATTERN, url)
    samples = [
        {"bucket": {"name": "media-uploads"}, "object": {"key": "raw/clip.mp4"}},
        {"bucket": {"name": "media-uploads"}, "object": {"key": "processed/clip.mp4"}},
        {"bucket": {"name": "other-bucket"}, "object": {"key": "raw/clip.mp4"}},
    ]
    for detail in samples:
        events.put_events(Entries=[{"EventBusName": "app", "Source": "aws.s3", "DetailType": "Object Created", "Detail": json.dumps(detail)}])
    events.put_events(Entries=[{"EventBusName": "app", "Source": "aws.s3", "DetailType": "Object Deleted", "Detail": json.dumps(samples[0])}])
    assert _received(sqs, url) == [samples[0]]


def test_big_order_pattern(env):
    events, sqs = env
    url = sqs.create_queue(QueueName="big-orders")["QueueUrl"]
    route(events, sqs, "app", "big-orders", BIG_ORDER_PATTERN, url)
    samples = [
        {"id": 1, "amount": 250, "country": "FR"},
        {"id": 2, "amount": 99.5, "country": "FR"},
        {"id": 3, "amount": 100, "country": "TEST"},
        {"id": 4, "amount": 100, "country": "DE"},
    ]
    for detail in samples:
        events.put_events(Entries=[{"EventBusName": "app", "Source": "shop.orders", "DetailType": "OrderPlaced", "Detail": json.dumps(detail)}])
    assert sorted(d["id"] for d in _received(sqs, url)) == [1, 4]
