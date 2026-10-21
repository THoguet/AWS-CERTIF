"""
Exercise sdk_5 — Client configuration and waiters
=================================================
Book: chapter 3, "Retries, backoff and jitter" and "Pagination and waiters"
Exam: Domain 1 · Task 1.1 / Domain 4 · Task 4.3

1) Retry modes. botocore supports three retry modes:
   * legacy   — old default, few error codes retried,
   * standard — consistent retry rules across SDKs, exponential backoff
                with jitter, default 3 attempts,
   * adaptive — standard + client-side rate limiting (experimental).
   Careful with the vocabulary: in a botocore `Config`, "max_attempts"
   is the number of RETRIES, while "total_max_attempts" includes the
   initial call. (In ~/.aws/config and AWS_MAX_ATTEMPTS, max_attempts
   means total attempts.)
   Timeouts matter too: a Lambda function with a 3 s timeout should not
   wait 60 s for a socket read.

2) Waiters. Resources such as DynamoDB tables are created
   asynchronously (status CREATING → ACTIVE). Instead of a hand-written
   polling loop, use a waiter.

Your task
---------
  * `make_dynamodb_client()`: DynamoDB client (eu-west-3) with standard
    retry mode, at most 10 attempts IN TOTAL (the first call included),
    2 s connect timeout, 5 s read timeout,
  * `create_table_and_wait(client, name)`: create an on-demand table with
    a string partition key "pk", wait until it exists, return its status.
"""

import boto3
from botocore.config import Config


def make_dynamodb_client():
    config = Config(retries={"mode": "standard", "total_max_attempts": 10}, connect_timeout=2, read_timeout=5)
    return boto3.client("dynamodb", region_name="eu-west-3", config=config)


def create_table_and_wait(client, name: str) -> str:
    client.create_table(
        TableName=name,
        BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}],
        KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
    )
    client.get_waiter("table_exists").wait(TableName=name)
    return client.describe_table(TableName=name)["Table"]["TableStatus"]


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run sdk_5
# =============================================================================
from unittest import mock  # noqa: E402


def test_retry_configuration():
    client = make_dynamodb_client()
    retries = client.meta.config.retries
    assert retries.get("mode") == "standard"
    assert retries.get("total_max_attempts") == 10, "10 attempts in total = 1 call + 9 retries"


def test_timeouts():
    client = make_dynamodb_client()
    assert client.meta.config.connect_timeout == 2
    assert client.meta.config.read_timeout == 5


def test_region():
    assert make_dynamodb_client().meta.region_name == "eu-west-3"


def test_waits_for_table(aws):
    client = make_dynamodb_client()
    real_get_waiter = client.get_waiter
    with mock.patch.object(client, "get_waiter", side_effect=real_get_waiter) as spy:
        status = create_table_and_wait(client, "sessions")
    assert status == "ACTIVE"
    spy.assert_called_with("table_exists")
