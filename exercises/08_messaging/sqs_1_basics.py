"""
Exercise sqs_1 — Producer and consumer basics
=============================================
Book: chapter 9, "Amazon SQS" (book/src/ch09-messaging.md)
Exam: Domain 1 · Task 1.1 (writing code to use messaging services), Domain 4 · Task 4.3

SQS in 5 facts:
  * a consumer RECEIVES a message, processes it, then DELETES it with the
    receipt handle. Otherwise the message reappears after the visibility
    timeout (default 30 s, max 12 h) and is processed again,
  * short polling returns immediately (often empty, costs requests).
    LONG polling (WaitTimeSeconds 1-20) waits for messages: fewer empty
    responses, lower cost. Set it per call or as the queue default
    ReceiveMessageWaitTimeSeconds,
  * receive up to 10 messages per call,
  * retention: 4 days by default, 1 minute to 14 days,
  * standard queues: at-least-once delivery, best-effort ordering.

Your task
---------
  * `create_orders_queue(sqs)`: queue "orders" with 20 s long polling,
    120 s visibility timeout, 7 days retention. Return its URL,
  * `send_order(sqs, url, order)`: JSON body + message attribute
    "type" = "order" (String). Return the message id,
  * `consume_once(sqs, url, process)`: ONE long-polling receive of up to
    10 messages. Call process(order_dict) for each and delete only the
    successful ones. Return the number of messages processed successfully.
"""

# I AM NOT DONE

import json


def create_orders_queue(sqs) -> str:
    return sqs.create_queue(QueueName="orders")["QueueUrl"]  # TODO: attributes


def send_order(sqs, url: str, order: dict) -> str:
    raise NotImplementedError  # TODO


def consume_once(sqs, url: str, process) -> int:
    response = sqs.receive_message(QueueUrl=url)  # TODO: long polling, up to 10 messages
    for message in response.get("Messages", []):
        process(json.loads(message["Body"]))  # TODO: delete on success, survive failures
    return len(response.get("Messages", []))


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run sqs_1
# =============================================================================
import boto3  # noqa: E402
import pytest  # noqa: E402


@pytest.fixture
def sqs(aws):
    return boto3.client("sqs")


def _attr(sqs, url, name):
    return sqs.get_queue_attributes(QueueUrl=url, AttributeNames=[name])["Attributes"][name]


def test_queue_attributes(sqs):
    url = create_orders_queue(sqs)
    assert _attr(sqs, url, "ReceiveMessageWaitTimeSeconds") == "20"
    assert _attr(sqs, url, "VisibilityTimeout") == "120"
    assert _attr(sqs, url, "MessageRetentionPeriod") == "604800"


def test_send_with_attribute(sqs):
    url = create_orders_queue(sqs)
    message_id = send_order(sqs, url, {"id": "o-1"})
    message = sqs.receive_message(QueueUrl=url, MessageAttributeNames=["All"])["Messages"][0]
    assert message["MessageId"] == message_id
    assert json.loads(message["Body"]) == {"id": "o-1"}
    assert message["MessageAttributes"]["type"]["StringValue"] == "order"


def test_consumer_deletes_only_successes(sqs):
    url = create_orders_queue(sqs)
    for i in range(3):
        send_order(sqs, url, {"id": f"o-{i}", "ok": i != 1})
    seen = []

    def process(order):
        seen.append(order["id"])
        if not order["ok"]:
            raise ValueError("payment declined")

    assert consume_once(sqs, url, process) == 2
    assert sorted(seen) == ["o-0", "o-1", "o-2"]
    assert _attr(sqs, url, "ApproximateNumberOfMessagesNotVisible") == "1", "the failed message must stay in the queue"
    assert _attr(sqs, url, "ApproximateNumberOfMessages") == "0"
