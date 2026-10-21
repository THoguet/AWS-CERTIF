"""
Exercise ddb_3 — Query (not Scan) and paginate
==============================================
Book: chapter 7, "Query vs Scan" (book/src/ch07-dynamodb.md)
Exam: Domain 1 · Task 1.3 (differences between query and scan operations)

  * Query reads ONE partition (one partition key value), optionally narrowed
    on the sort key (=, <, <=, >, >=, BETWEEN, begins_with). Results come
    back sorted by sort key (ScanIndexForward=False for descending).
  * Scan reads the WHOLE table and filters afterwards. A FilterExpression
    does NOT reduce consumed capacity, because it is applied after the read.
  * Both return at most 1 MB per call. Continue with LastEvaluatedKey →
    ExclusiveStartKey until LastEvaluatedKey is absent.

Table `Orders`: partition key customer_id, sort key order_date (ISO 8601
strings sort chronologically).

Your task
---------
Implement `orders_since(table, customer_id, since, page_size)`: every
order of the customer with order_date >= since, oldest first, using Query
and following pagination.
"""

# I AM NOT DONE

from boto3.dynamodb.conditions import Attr, Key  # noqa: F401


def orders_since(table, customer_id: str, since: str, page_size: int = 100) -> list[dict]:
    # TODO: this scans the whole table AND stops after the first page
    response = table.scan(FilterExpression=Attr("customer_id").eq(customer_id) & Attr("order_date").gte(since), Limit=page_size)
    return response["Items"]


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run ddb_3
# =============================================================================
import boto3  # noqa: E402
import pytest  # noqa: E402


class NoScanTable:
    """Wraps a Table and forbids Scan."""

    def __init__(self, table):
        self._table = table
        self.queries = 0

    def scan(self, **kwargs):
        raise AssertionError("use Query, not Scan")

    def query(self, **kwargs):
        self.queries += 1
        return self._table.query(**kwargs)


@pytest.fixture
def table(aws):
    ddb = boto3.resource("dynamodb")
    t = ddb.create_table(
        TableName="Orders",
        BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[{"AttributeName": "customer_id", "AttributeType": "S"}, {"AttributeName": "order_date", "AttributeType": "S"}],
        KeySchema=[{"AttributeName": "customer_id", "KeyType": "HASH"}, {"AttributeName": "order_date", "KeyType": "RANGE"}],
    )
    with t.batch_writer() as batch:
        for day in range(1, 31):
            batch.put_item(Item={"customer_id": "c-1", "order_date": f"2026-09-{day:02d}T10:00:00Z", "total": day})
            batch.put_item(Item={"customer_id": "c-2", "order_date": f"2026-09-{day:02d}T11:00:00Z", "total": day})
    return t


def test_returns_all_matching_orders_across_pages(table):
    wrapped = NoScanTable(table)
    result = orders_since(wrapped, "c-1", "2026-09-10", page_size=7)
    assert [item["total"] for item in result] == list(range(10, 31))
    assert wrapped.queries > 1, "with page_size=7 you need several Query calls"


def test_only_this_customer(table):
    result = orders_since(NoScanTable(table), "c-2", "2026-09-29")
    assert {item["customer_id"] for item in result} == {"c-2"}
    assert len(result) == 2
