"""
Exercise sqs_3 — FIFO queues
============================
Book: chapter 9, "FIFO queues" (book/src/ch09-messaging.md)
Exam: Domain 1 · Task 1.1

Order events for the same customer must be processed in order and only
once. FIFO queues provide:
  * strict ordering WITHIN a message group (MessageGroupId). Different
    groups are processed in parallel. One group = one ordered lane,
  * exactly-once processing: duplicates sent within the 5-minute
    deduplication interval are dropped, using either an explicit
    MessageDeduplicationId or ContentBasedDeduplication (SHA-256 of the body),
  * throughput: 300 messages/s per API action without batching, 3,000 with
    batches of 10, much more in high-throughput mode,
  * the name MUST end with ".fifo". You cannot convert a standard queue
    to FIFO (create a new one).

Your task
---------
  * `create_fifo_queue(sqs, name)`: raise ValueError if the name does not
    end with ".fifo". Otherwise create the queue with content-based
    deduplication and return its URL,
  * `publish_event(sqs, url, customer_id, event)`: keep each customer's
    events ordered, return the message id.
"""

import json


def create_fifo_queue(sqs, name: str) -> str:
    if not name.endswith(".fifo"):
        raise ValueError("FIFO queue names must end with .fifo")
    return sqs.create_queue(QueueName=name, Attributes={"FifoQueue": "true", "ContentBasedDeduplication": "true"})["QueueUrl"]


def publish_event(sqs, url: str, customer_id: str, event: dict) -> str:
    return sqs.send_message(QueueUrl=url, MessageBody=json.dumps(event, sort_keys=True), MessageGroupId=customer_id)["MessageId"]


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run sqs_3
# =============================================================================
import boto3  # noqa: E402
import pytest  # noqa: E402


@pytest.fixture
def sqs(aws):
    return boto3.client("sqs")


def test_name_must_end_with_fifo(sqs):
    with pytest.raises(ValueError):
        create_fifo_queue(sqs, "orders")


def test_fifo_attributes(sqs):
    url = create_fifo_queue(sqs, "orders.fifo")
    attrs = sqs.get_queue_attributes(QueueUrl=url, AttributeNames=["All"])["Attributes"]
    assert attrs["FifoQueue"] == "true"
    assert attrs["ContentBasedDeduplication"] == "true"


def test_duplicates_are_dropped_and_order_kept(sqs):
    url = create_fifo_queue(sqs, "orders.fifo")
    publish_event(sqs, url, "c-1", {"type": "created", "order": "o-1"})
    publish_event(sqs, url, "c-1", {"order": "o-1", "type": "created"})  # same event, keys in another order
    publish_event(sqs, url, "c-1", {"type": "paid", "order": "o-1"})
    publish_event(sqs, url, "c-1", {"type": "shipped", "order": "o-1"})
    messages = sqs.receive_message(QueueUrl=url, MaxNumberOfMessages=10, AttributeNames=["MessageGroupId"])["Messages"]
    assert [json.loads(m["Body"])["type"] for m in messages] == ["created", "paid", "shipped"]
    assert {m["Attributes"]["MessageGroupId"] for m in messages} == {"c-1"}
