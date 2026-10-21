"""
Exercise ddb_5 — Optimistic locking with a version number
=========================================================
Book: chapter 7, "Conditional writes and optimistic locking" (book/src/ch07-dynamodb.md)
Exam: Domain 1 · Task 1.3 (using and maintaining data stores), Domain 4 · Task 4.1 (debugging)

Two users edit the same profile at the same time. Without protection, the
last write silently overwrites the first one (a "lost update").

Optimistic locking: every item carries a `version` number. A writer
  1. reads the item (version N),
  2. writes the new data with version N+1 ONLY IF the stored version is
     still N (a condition expression),
  3. if the condition fails, someone else won the race: reload and retry,
     or report a conflict.
(The DynamoDBMapper / Enhanced Client in Java does this with @Version.)

Your task
---------
Implement `save_profile(table, profile)`. `profile["version"]` is the
version that was read (0 for a brand-new profile). Return the new version
number, or raise ConflictError if the stored version changed.
"""

# I AM NOT DONE

from botocore.exceptions import ClientError


class ConflictError(Exception):
    pass


def save_profile(table, profile: dict) -> int:
    expected = profile["version"]
    item = {**profile, "version": expected + 1}
    table.put_item(Item=item)  # TODO: only if nobody changed the item since we read it
    return expected + 1


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run ddb_5
# =============================================================================
import boto3  # noqa: E402
import pytest  # noqa: E402


@pytest.fixture
def table(aws):
    return boto3.resource("dynamodb").create_table(
        TableName="Profiles",
        BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}],
        KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
    )


def test_create_then_update(table):
    assert save_profile(table, {"pk": "u-1", "name": "Ada", "version": 0}) == 1
    assert save_profile(table, {"pk": "u-1", "name": "Ada L.", "version": 1}) == 2
    item = table.get_item(Key={"pk": "u-1"})["Item"]
    assert item["name"] == "Ada L." and item["version"] == 2


def test_lost_update_is_detected(table):
    save_profile(table, {"pk": "u-1", "name": "Ada", "version": 0})
    save_profile(table, {"pk": "u-1", "name": "Ada (tab 1)", "version": 1})
    with pytest.raises(ConflictError):
        save_profile(table, {"pk": "u-1", "name": "Ada (tab 2, stale)", "version": 1})
    assert table.get_item(Key={"pk": "u-1"})["Item"]["name"] == "Ada (tab 1)"


def test_cannot_create_twice(table):
    save_profile(table, {"pk": "u-1", "name": "Ada", "version": 0})
    with pytest.raises(ConflictError):
        save_profile(table, {"pk": "u-1", "name": "Impostor", "version": 0})
