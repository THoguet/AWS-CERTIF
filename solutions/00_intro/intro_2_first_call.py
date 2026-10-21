"""
Exercise intro_2 — Your first boto3 call
========================================
Book: chapter 3, "SDKs: clients, resources, sessions" (book/src/ch03-cli-sdk-sts.md)
Exam: Domain 1 · Task 1.1 (write code that interacts with AWS services by using APIs and SDKs)

boto3 is the AWS SDK for Python. A *client* maps 1:1 to the service API:
`boto3.client("sqs", region_name=...)` gives you methods such as
`create_queue`, `send_message`, `receive_message`...

The consumer of your queue runs in Ireland, so the queue must live in
**eu-west-1** (not in the default region configured on the machine).

Your task
---------
Complete `create_jobs_queue()` so that it:
  1. creates an SQS client for the region eu-west-1,
  2. creates a queue named `name` with a visibility timeout of 60 seconds,
  3. returns the queue URL.

Note: SQS queue attributes are passed as a dict of *strings*
(`{"VisibilityTimeout": "60"}`), a classic SDK gotcha.
"""

import boto3


def create_jobs_queue(name: str) -> str:
    sqs = boto3.client("sqs", region_name="eu-west-1")
    response = sqs.create_queue(QueueName=name, Attributes={"VisibilityTimeout": "60"})
    return response["QueueUrl"]


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run intro_2
# =============================================================================


def test_queue_is_created_in_ireland(aws):
    url = create_jobs_queue("jobs")
    assert "eu-west-1" in url
    queues = boto3.client("sqs", region_name="eu-west-1").list_queues()["QueueUrls"]
    assert url in queues


def test_visibility_timeout_is_60_seconds(aws):
    url = create_jobs_queue("jobs")
    attrs = boto3.client("sqs", region_name="eu-west-1").get_queue_attributes(
        QueueUrl=url, AttributeNames=["VisibilityTimeout"]
    )["Attributes"]
    assert attrs["VisibilityTimeout"] == "60"
