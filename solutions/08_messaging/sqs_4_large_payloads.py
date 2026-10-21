"""
Exercise sqs_4 — Large payloads: the claim-check pattern
========================================================
Book: chapter 9, "Message size and the claim-check pattern" (book/src/ch09-messaging.md)
Exam: Domain 1 · Task 1.1 (writing code to use messaging services)

SQS messages have a maximum size. For years it was 256 KB, and that is
the number you will meet in most exam questions. (AWS raised it to 1 MiB
in August 2025.) The pattern for bigger payloads stays the same:
store the payload in S3 and send only a POINTER in the message. The
"Amazon SQS Extended Client Library" (Java, Python...) does exactly this.

Your task
---------
  * `send_payload(sqs, s3, url, bucket, payload)`: inline when
    len(payload) <= MAX_INLINE_BYTES, otherwise claim check via S3,
  * `receive_payload(sqs, s3, url)`: receive ONE message, return the
    original bytes, delete the message.
"""

import json
import uuid

MAX_INLINE_BYTES = 256 * 1024


def send_payload(sqs, s3, url: str, bucket: str, payload: bytes) -> None:
    if len(payload) <= MAX_INLINE_BYTES:
        sqs.send_message(QueueUrl=url, MessageBody=payload.decode("utf-8"))
        return
    key = f"payloads/{uuid.uuid4()}"
    s3.put_object(Bucket=bucket, Key=key, Body=payload)
    sqs.send_message(
        QueueUrl=url,
        MessageBody=json.dumps({"s3_bucket": bucket, "s3_key": key}),
        MessageAttributes={"claim-check": {"DataType": "String", "StringValue": "true"}},
    )


def receive_payload(sqs, s3, url: str) -> bytes:
    message = sqs.receive_message(QueueUrl=url, MaxNumberOfMessages=1, MessageAttributeNames=["All"])["Messages"][0]
    if message.get("MessageAttributes", {}).get("claim-check", {}).get("StringValue") == "true":
        pointer = json.loads(message["Body"])
        payload = s3.get_object(Bucket=pointer["s3_bucket"], Key=pointer["s3_key"])["Body"].read()
    else:
        payload = message["Body"].encode("utf-8")
    sqs.delete_message(QueueUrl=url, ReceiptHandle=message["ReceiptHandle"])
    return payload


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run sqs_4
# =============================================================================
import boto3  # noqa: E402
import pytest  # noqa: E402


@pytest.fixture
def env(aws, region):
    sqs, s3 = boto3.client("sqs"), boto3.client("s3")
    url = sqs.create_queue(QueueName="reports")["QueueUrl"]
    s3.create_bucket(Bucket="report-payloads", CreateBucketConfiguration={"LocationConstraint": region})
    return sqs, s3, url


def test_small_payload_is_inline(env):
    sqs, s3, url = env
    send_payload(sqs, s3, url, "report-payloads", b'{"rows": 3}')
    assert s3.list_objects_v2(Bucket="report-payloads").get("KeyCount", 0) == 0
    assert receive_payload(sqs, s3, url) == b'{"rows": 3}'


def test_large_payload_goes_through_s3(env):
    sqs, s3, url = env
    big = b"x" * (300 * 1024)
    send_payload(sqs, s3, url, "report-payloads", big)
    assert s3.list_objects_v2(Bucket="report-payloads")["KeyCount"] == 1
    body = sqs.receive_message(QueueUrl=url, VisibilityTimeout=0)["Messages"][0]["Body"]
    assert len(body) < 1024, "only a pointer should travel through SQS"
    assert receive_payload(sqs, s3, url) == big


def test_message_is_deleted(env):
    sqs, s3, url = env
    send_payload(sqs, s3, url, "report-payloads", b"hello")
    receive_payload(sqs, s3, url)
    attrs = sqs.get_queue_attributes(QueueUrl=url, AttributeNames=["All"])["Attributes"]
    assert attrs["ApproximateNumberOfMessages"] == "0" and attrs["ApproximateNumberOfMessagesNotVisible"] == "0"
