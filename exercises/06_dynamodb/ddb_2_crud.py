"""
Exercise ddb_2 — CRUD with the DynamoDB Table resource
======================================================
Book: chapter 7, "Items, keys and the core API" (book/src/ch07-dynamodb.md)
Exam: Domain 1 · Task 1.3 (CRUD operations, DynamoDB keys)

Table `Orders`:
  * partition key `customer_id` (string), sort key `order_id` (string),
  * on-demand capacity (PAY_PER_REQUEST).

Things to remember:
  * only KEY attributes are declared in AttributeDefinitions (schemaless otherwise),
  * GetItem needs the FULL primary key (partition + sort key),
  * GetItem is eventually consistent unless ConsistentRead=True,
  * UpdateItem creates the item if it does not exist (an "upsert"),
  * many words are RESERVED (status, name, date, data, count...). Use
    ExpressionAttributeNames placeholders (#s) for them.

Your task
---------
Complete the five functions below.
"""

# I AM NOT DONE

from datetime import datetime, timezone


def create_orders_table(client) -> None:
    # TODO: composite primary key, on-demand billing
    raise NotImplementedError


def put_order(table, order: dict) -> None:
    raise NotImplementedError  # TODO


def get_order(table, customer_id: str, order_id: str, consistent: bool = False) -> dict | None:
    response = table.get_item(Key={"customer_id": customer_id})  # TODO: full key? consistency?
    return response["Item"]  # TODO: what if the item does not exist?


def mark_shipped(table, customer_id: str, order_id: str) -> dict:
    shipped_at = datetime.now(timezone.utc).isoformat()
    response = table.update_item(
        Key={"customer_id": customer_id, "order_id": order_id},
        UpdateExpression="SET status = :s, shipped_at = :t",  # TODO: "status" is a reserved word
        ExpressionAttributeValues={":s": "SHIPPED", ":t": shipped_at},
    )
    return response["Attributes"]  # TODO: ask for the new values


def delete_order(table, customer_id: str, order_id: str) -> dict | None:
    raise NotImplementedError  # TODO: return the deleted item (or None)


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run ddb_2
# =============================================================================
import boto3  # noqa: E402
import pytest  # noqa: E402


@pytest.fixture
def table(aws):
    create_orders_table(boto3.client("dynamodb"))
    return boto3.resource("dynamodb").Table("Orders")


def test_table_schema(table):
    desc = boto3.client("dynamodb").describe_table(TableName="Orders")["Table"]
    assert {k["AttributeName"]: k["KeyType"] for k in desc["KeySchema"]} == {"customer_id": "HASH", "order_id": "RANGE"}
    assert desc["BillingModeSummary"]["BillingMode"] == "PAY_PER_REQUEST"


def test_put_and_get(table):
    put_order(table, {"customer_id": "c-1", "order_id": "o-1", "status": "NEW", "total": 42})
    assert get_order(table, "c-1", "o-1", consistent=True)["status"] == "NEW"
    assert get_order(table, "c-1", "missing") is None


def test_update_reserved_word(table):
    put_order(table, {"customer_id": "c-1", "order_id": "o-1", "status": "NEW"})
    updated = mark_shipped(table, "c-1", "o-1")
    assert updated["status"] == "SHIPPED"
    assert "shipped_at" in updated
    assert updated["customer_id"] == "c-1", "ALL_NEW returns the whole item"


def test_delete_returns_old_item(table):
    put_order(table, {"customer_id": "c-1", "order_id": "o-1", "status": "NEW"})
    assert delete_order(table, "c-1", "o-1")["status"] == "NEW"
    assert delete_order(table, "c-1", "o-1") is None
