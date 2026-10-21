"""
Exercise sqs_2 — Dead-letter queues
===================================
Book: chapter 9, "Dead-letter queues and redrive" (book/src/ch09-messaging.md)
Exam: Domain 1 · Task 1.1 (fault-tolerant design patterns: dead-letter queues)

A "poison pill" message (one that always fails) would otherwise be
received forever, wasting money and blocking a FIFO message group. With a
REDRIVE POLICY, after `maxReceiveCount` receives without a delete, SQS
moves the message to the dead-letter queue (DLQ), where you can inspect
it, alarm on it, and later redrive it back to the source queue.

Rules to remember:
  * the DLQ must be the same type as the source (FIFO DLQ for a FIFO queue)
    and live in the same account and Region,
  * for standard queues, the message keeps its ORIGINAL enqueue timestamp.
    Give the DLQ a longer retention than the source queue, otherwise
    messages may expire soon after they arrive in the DLQ,
  * alarm on the DLQ's ApproximateNumberOfMessagesVisible > 0.

Your task
---------
Implement `create_queue_with_dlq(sqs, name, max_receives)`: create
"<name>-dlq" (14 days retention) and "<name>" (4 days retention, 30 s
visibility timeout, redrive to the DLQ after `max_receives` receives).
Return (queue_url, dlq_url).
"""

# I AM NOT DONE

import json


def create_queue_with_dlq(sqs, name: str, max_receives: int = 3) -> tuple[str, str]:
    dlq_url = sqs.create_queue(QueueName=f"{name}-dlq")["QueueUrl"]  # TODO: retention
    queue_url = sqs.create_queue(QueueName=name)["QueueUrl"]  # TODO: retention, visibility timeout, redrive policy
    return queue_url, dlq_url


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run sqs_2
# =============================================================================
import boto3  # noqa: E402


def test_redrive_policy(aws):
    sqs = boto3.client("sqs")
    queue_url, dlq_url = create_queue_with_dlq(sqs, "payments", 3)
    attrs = sqs.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["All"])["Attributes"]
    dlq_attrs = sqs.get_queue_attributes(QueueUrl=dlq_url, AttributeNames=["All"])["Attributes"]
    policy = json.loads(attrs["RedrivePolicy"])
    assert policy["deadLetterTargetArn"] == dlq_attrs["QueueArn"]
    assert int(policy["maxReceiveCount"]) == 3
    assert int(dlq_attrs["MessageRetentionPeriod"]) == 1209600
    assert int(dlq_attrs["MessageRetentionPeriod"]) > int(attrs["MessageRetentionPeriod"])


def test_poison_message_ends_in_dlq(aws):
    sqs = boto3.client("sqs")
    queue_url, dlq_url = create_queue_with_dlq(sqs, "payments", 3)
    sqs.send_message(QueueUrl=queue_url, MessageBody="poison")
    receives = 0
    for _ in range(6):  # a consumer that always fails (never deletes)
        receives += len(sqs.receive_message(QueueUrl=queue_url, VisibilityTimeout=0).get("Messages", []))
    assert receives == 3
    dead = sqs.receive_message(QueueUrl=dlq_url).get("Messages", [])
    assert [m["Body"] for m in dead] == ["poison"]
