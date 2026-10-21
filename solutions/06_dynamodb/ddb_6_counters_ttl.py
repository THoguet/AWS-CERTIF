"""
Exercise ddb_6 — Atomic counters and Time To Live
=================================================
Book: chapter 7, "Update expressions" and "TTL" (book/src/ch07-dynamodb.md)
Exam: Domain 1 · Task 1.3 (managing data lifecycles, caching strategies / TTL)

1) Atomic counter. Reading a value, adding 1 in code and writing it back
   loses increments under concurrency. `UpdateExpression="ADD view_count :one"`
   (or "SET view_count = if_not_exists(view_count, :zero) + :one") increments
   atomically on the server. (The attribute is not simply called "views"
   because VIEWS is one of DynamoDB's hundreds of reserved words!)

2) TTL. DynamoDB deletes items whose TTL attribute (a Number holding an
   epoch timestamp in SECONDS) is in the past. Deletion is free (no WCU),
   happens in the background (typically within a few days, so filter out
   expired items in reads if it matters), and shows up in DynamoDB
   Streams as a deletion made by the service. Typical uses: sessions,
   idempotency keys, temporary data.

Your task
---------
  * `increment_views(table, page_id)`: atomic +1, return the new count (int),
  * `store_session(table, session_id, user, ttl_seconds, now)`: put the
    session with an `expires_at` attribute,
  * `enable_ttl(client, table_name)`: turn TTL on for `expires_at`.
"""

import time


def increment_views(table, page_id: str) -> int:
    response = table.update_item(
        Key={"pk": page_id},
        UpdateExpression="ADD view_count :one",
        ExpressionAttributeValues={":one": 1},
        ReturnValues="UPDATED_NEW",
    )
    return int(response["Attributes"]["view_count"])


def store_session(table, session_id: str, user: str, ttl_seconds: int = 3600, now=time.time) -> None:
    table.put_item(Item={"pk": session_id, "user": user, "expires_at": int(now()) + ttl_seconds})


def enable_ttl(client, table_name: str) -> None:
    client.update_time_to_live(TableName=table_name, TimeToLiveSpecification={"Enabled": True, "AttributeName": "expires_at"})


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run ddb_6
# =============================================================================
from unittest import mock  # noqa: E402

import boto3  # noqa: E402
import pytest  # noqa: E402


@pytest.fixture
def table(aws):
    return boto3.resource("dynamodb").create_table(
        TableName="Site",
        BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}],
        KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
    )


def test_counter_is_atomic(table):
    with mock.patch.object(table, "get_item", side_effect=AssertionError("no read-modify-write")):
        assert [increment_views(table, "home") for _ in range(3)] == [1, 2, 3]
    assert increment_views(table, "about") == 1


def test_session_ttl_in_seconds(table):
    store_session(table, "s-1", "ada", ttl_seconds=3600, now=lambda: 1_800_000_000.9)
    item = table.get_item(Key={"pk": "s-1"})["Item"]
    assert int(item["expires_at"]) == 1_800_003_600
    assert item["expires_at"] < 10**10, "epoch seconds, not milliseconds"


def test_ttl_enabled(table):
    enable_ttl(boto3.client("dynamodb"), "Site")
    ttl = boto3.client("dynamodb").describe_time_to_live(TableName="Site")["TimeToLiveDescription"]
    assert ttl["TimeToLiveStatus"] in ("ENABLED", "ENABLING")
    assert ttl["AttributeName"] == "expires_at"
