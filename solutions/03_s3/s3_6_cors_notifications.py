"""
Exercise s3_6 — CORS and event notifications
============================================
Book: chapter 4, "CORS" and "Event notifications" (book/src/ch04-s3.md)
Exam: Domain 1 · Task 1.1 (event-driven architecture), Domain 4 · Task 4.1 (troubleshooting)

1) CORS. The single-page app served from https://app.example.com uploads
   photos straight to the `photo-inbox` bucket from the browser. Browsers
   block cross-origin calls unless the bucket's CORS configuration allows
   that origin. The JS code also needs to read the ETag response header.

2) Event notifications. Every new `.jpg` under `uploads/` must produce a
   message in the `thumbnail-jobs` SQS queue. Exam trap: S3 must be
   ALLOWED to send to the queue through the queue's resource policy
   (same for SNS topics and Lambda functions). Without it, notifications
   silently never arrive (in real AWS the configuration call itself
   fails validation).

Your task
---------
  * `configure_cors(s3, bucket, origin)`,
  * `allow_s3_to_send(sqs, queue_url, queue_arn, bucket)`,
  * `notify_uploads(s3, bucket, queue_arn)`.
"""

import json


def configure_cors(s3, bucket: str, origin: str) -> None:
    s3.put_bucket_cors(
        Bucket=bucket,
        CORSConfiguration={
            "CORSRules": [
                {
                    "AllowedOrigins": [origin],
                    "AllowedMethods": ["GET", "PUT"],
                    "AllowedHeaders": ["*"],
                    "ExposeHeaders": ["ETag"],
                    "MaxAgeSeconds": 3000,
                }
            ]
        },
    )


def allow_s3_to_send(sqs, queue_url: str, queue_arn: str, bucket: str) -> None:
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowS3Notifications",
                "Effect": "Allow",
                "Principal": {"Service": "s3.amazonaws.com"},
                "Action": "sqs:SendMessage",
                "Resource": queue_arn,
                "Condition": {"ArnLike": {"aws:SourceArn": f"arn:aws:s3:::{bucket}"}},
            }
        ],
    }
    sqs.set_queue_attributes(QueueUrl=queue_url, Attributes={"Policy": json.dumps(policy)})


def notify_uploads(s3, bucket: str, queue_arn: str) -> None:
    s3.put_bucket_notification_configuration(
        Bucket=bucket,
        NotificationConfiguration={
            "QueueConfigurations": [
                {
                    "QueueArn": queue_arn,
                    "Events": ["s3:ObjectCreated:*"],
                    "Filter": {
                        "Key": {"FilterRules": [{"Name": "prefix", "Value": "uploads/"}, {"Name": "suffix", "Value": ".jpg"}]}
                    },
                }
            ]
        },
    )


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run s3_6
# =============================================================================
import boto3  # noqa: E402
import pytest  # noqa: E402


@pytest.fixture
def env(aws, region):
    s3, sqs = boto3.client("s3"), boto3.client("sqs")
    s3.create_bucket(Bucket="photo-inbox", CreateBucketConfiguration={"LocationConstraint": region})
    url = sqs.create_queue(QueueName="thumbnail-jobs")["QueueUrl"]
    arn = sqs.get_queue_attributes(QueueUrl=url, AttributeNames=["QueueArn"])["Attributes"]["QueueArn"]
    return s3, sqs, url, arn


def test_cors(env):
    s3, *_ = env
    configure_cors(s3, "photo-inbox", "https://app.example.com")
    rule = s3.get_bucket_cors(Bucket="photo-inbox")["CORSRules"][0]
    assert rule["AllowedOrigins"] == ["https://app.example.com"]
    assert set(rule["AllowedMethods"]) == {"GET", "PUT"}
    assert rule["ExposeHeaders"] == ["ETag"]
    assert rule["MaxAgeSeconds"] == 3000


def test_queue_policy(env):
    _, sqs, url, arn = env
    allow_s3_to_send(sqs, url, arn, "photo-inbox")
    policy = json.loads(sqs.get_queue_attributes(QueueUrl=url, AttributeNames=["Policy"])["Attributes"]["Policy"])
    statement = policy["Statement"][0]
    assert statement["Principal"] == {"Service": "s3.amazonaws.com"}
    assert statement["Action"] in ("sqs:SendMessage", ["sqs:SendMessage"])
    assert statement["Condition"]["ArnLike"]["aws:SourceArn"] == "arn:aws:s3:::photo-inbox"


def test_notifications_are_filtered(env):
    s3, sqs, url, arn = env
    allow_s3_to_send(sqs, url, arn, "photo-inbox")
    notify_uploads(s3, "photo-inbox", arn)
    for key in ("uploads/cat.jpg", "uploads/notes.txt", "archive/dog.jpg"):
        s3.put_object(Bucket="photo-inbox", Key=key, Body=b"x")
    messages = sqs.receive_message(QueueUrl=url, MaxNumberOfMessages=10).get("Messages", [])
    keys = [r["s3"]["object"]["key"] for m in messages for r in json.loads(m["Body"]).get("Records", [])]
    assert [k.replace("%2F", "/") for k in keys] == ["uploads/cat.jpg"]
