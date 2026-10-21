"""
Exercise sns_1 — Fan-out with subscription filter policies
==========================================================
Book: chapter 9, "Amazon SNS" (book/src/ch09-messaging.md)
Exam: Domain 1 · Task 1.1 (fanout pattern), Domain 4 · Task 4.3 (using subscription filter policies)

The "orders" topic fans out to three SQS queues (the SNS + SQS fan-out
pattern: every service gets its own durable copy):
  * billing   — only events of type order_placed or order_refunded,
  * shipping  — only order_placed events for France or Belgium,
  * analytics — every event, delivered RAW (just the message body,
                without the SNS JSON envelope).

Filter policies move the filtering into SNS: consumers stop receiving and
discarding irrelevant messages, which saves compute and money. Policies
match message ATTRIBUTES by default (FilterPolicyScope can also be set to
MessageBody).

In real AWS, each queue also needs an access policy that lets the topic
send messages to it (sqs:SendMessage with aws:SourceArn = topic ARN).

Your task
---------
  * `wire(sns, sqs)`: create the topic and the three subscriptions,
    return {"topic": topic_arn, "billing": url, "shipping": url, "analytics": url},
  * `publish(sns, topic_arn, event_type, country, payload)`.
"""

import json

QUEUES = ("billing", "shipping", "analytics")


def _queue(sqs, name: str) -> tuple[str, str]:
    url = sqs.create_queue(QueueName=name)["QueueUrl"]
    arn = sqs.get_queue_attributes(QueueUrl=url, AttributeNames=["QueueArn"])["Attributes"]["QueueArn"]
    return url, arn


def wire(sns, sqs) -> dict:
    topic_arn = sns.create_topic(Name="orders")["TopicArn"]
    result = {"topic": topic_arn}
    filters = {
        "billing": {"event_type": ["order_placed", "order_refunded"]},
        "shipping": {"event_type": ["order_placed"], "country": ["FR", "BE"]},
    }
    for name in QUEUES:
        url, arn = _queue(sqs, name)
        result[name] = url
        attributes = {"FilterPolicy": json.dumps(filters[name])} if name in filters else {"RawMessageDelivery": "true"}
        sns.subscribe(TopicArn=topic_arn, Protocol="sqs", Endpoint=arn, Attributes=attributes)
    return result


def publish(sns, topic_arn: str, event_type: str, country: str, payload: dict) -> None:
    sns.publish(
        TopicArn=topic_arn,
        Message=json.dumps(payload),
        MessageAttributes={
            "event_type": {"DataType": "String", "StringValue": event_type},
            "country": {"DataType": "String", "StringValue": country},
        },
    )


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run sns_1
# =============================================================================
import boto3  # noqa: E402
import pytest  # noqa: E402


def _drain(sqs, url):
    return sqs.receive_message(QueueUrl=url, MaxNumberOfMessages=10).get("Messages", [])


@pytest.fixture
def wired(aws):
    sns, sqs = boto3.client("sns"), boto3.client("sqs")
    return sns, sqs, wire(sns, sqs)


def test_routing(wired):
    sns, sqs, w = wired
    publish(sns, w["topic"], "order_placed", "FR", {"id": 1})
    publish(sns, w["topic"], "order_refunded", "US", {"id": 2})
    publish(sns, w["topic"], "order_placed", "US", {"id": 3})
    publish(sns, w["topic"], "cart_abandoned", "BE", {"id": 4})

    def ids(name):
        out = []
        for message in _drain(sqs, w[name]):
            body = json.loads(message["Body"])
            out.append(json.loads(body["Message"])["id"] if "Message" in body and "TopicArn" in body else body["id"])
        return sorted(out)

    assert ids("billing") == [1, 2, 3]
    assert ids("shipping") == [1]
    assert ids("analytics") == [1, 2, 3, 4]


def test_analytics_receives_raw_messages(wired):
    sns, sqs, w = wired
    publish(sns, w["topic"], "order_placed", "FR", {"id": 7})
    body = json.loads(_drain(sqs, w["analytics"])[0]["Body"])
    assert body == {"id": 7}, "raw delivery: no SNS envelope"
