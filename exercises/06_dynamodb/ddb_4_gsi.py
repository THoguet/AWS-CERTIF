"""
Exercise ddb_4 — Global secondary indexes
=========================================
Book: chapter 7, "Secondary indexes: LSI vs GSI" (book/src/ch07-dynamodb.md)
Exam: Domain 1 · Task 1.3 (DynamoDB keys and indexing)

Table `Tickets` has partition key `ticket_id`. The support dashboard needs
"all OPEN tickets created since X". Without an index, that is a Scan.

A GLOBAL secondary index (GSI) gives the table an alternative key:
  * any partition/sort key, created at table creation OR later,
  * its own throughput (in provisioned mode a throttled GSI also throttles
    writes to the table!),
  * eventually consistent reads ONLY,
  * a projection (KEYS_ONLY, INCLUDE some attributes, or ALL) that
    controls which attributes are copied into the index.
A LOCAL secondary index (LSI) keeps the table's partition key with another
sort key, must be created with the table, and supports strong consistency.

Your task
---------
  * `create_tickets_table(client)`: on-demand table + GSI INDEX with
    partition key `status` and sort key `created_at`, projecting only the
    keys plus `title`,
  * `open_tickets_since(table, since)`: query the index.
"""

# I AM NOT DONE

from boto3.dynamodb.conditions import Key

INDEX = "status-created_at-index"


def create_tickets_table(client) -> None:
    client.create_table(
        TableName="Tickets",
        BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[{"AttributeName": "ticket_id", "AttributeType": "S"}],
        KeySchema=[{"AttributeName": "ticket_id", "KeyType": "HASH"}],
        # TODO: add the GSI (and the attribute definitions its keys need)
    )


def open_tickets_since(table, since: str) -> list[dict]:
    response = table.query(
        IndexName=INDEX,
        KeyConditionExpression=Key("status").eq("OPEN") & Key("created_at").gte(since),
        ConsistentRead=True,  # TODO: is this allowed on a GSI?
    )
    return response["Items"]


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run ddb_4
# =============================================================================
import boto3  # noqa: E402
import pytest  # noqa: E402


@pytest.fixture
def table(aws):
    create_tickets_table(boto3.client("dynamodb"))
    t = boto3.resource("dynamodb").Table("Tickets")
    tickets = [
        ("t-1", "OPEN", "2026-10-01", "Login broken"),
        ("t-2", "CLOSED", "2026-10-02", "Typo"),
        ("t-3", "OPEN", "2026-10-05", "Slow search"),
        ("t-4", "OPEN", "2026-09-20", "Old bug"),
    ]
    for ticket_id, status, created_at, title in tickets:
        t.put_item(Item={"ticket_id": ticket_id, "status": status, "created_at": created_at, "title": title, "body": "long text..."})
    return t


def test_index_definition(table):
    gsi = boto3.client("dynamodb").describe_table(TableName="Tickets")["Table"]["GlobalSecondaryIndexes"][0]
    assert gsi["IndexName"] == INDEX
    assert [(k["AttributeName"], k["KeyType"]) for k in gsi["KeySchema"]] == [("status", "HASH"), ("created_at", "RANGE")]
    assert gsi["Projection"] == {"ProjectionType": "INCLUDE", "NonKeyAttributes": ["title"]}


def test_query_index(table):
    result = open_tickets_since(table, "2026-10-01")
    assert [item["ticket_id"] for item in result] == ["t-1", "t-3"]
    assert "title" in result[0]
