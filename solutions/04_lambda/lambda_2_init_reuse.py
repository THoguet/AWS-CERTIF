"""
Exercise lambda_2 — Reuse the execution environment
===================================================
Book: chapter 5, "Execution environment lifecycle" (book/src/ch05-lambda.md)
Exam: Domain 1 · Task 1.2 / Domain 4 · Task 4.3 (tuning Lambda functions for optimal performance)

Lambda runs your code in an execution environment. On a cold start it
loads your module (the INIT phase), then calls the handler. Following
invocations routed to the same warm environment only call the handler.

So:
  * create SDK clients, database connections and caches OUTSIDE the
    handler (module scope / lazily cached), so warm invocations reuse them,
  * never keep request-specific data in globals (another request will see it),
  * `/tmp` (512 MB to 10 GB) also survives between warm invocations.

The current code creates a new DynamoDB Table object on every call.

Your task
---------
Implement `get_table()` so that the table object is created at most once
per execution environment, and use it in the handler.
"""

import os

import boto3

TABLE_NAME = os.environ.get("TABLE_NAME", "visits")
TABLE_FACTORY = boto3.resource("dynamodb", region_name="eu-west-3").Table
_table = None


def get_table():
    global _table
    if _table is None:
        _table = TABLE_FACTORY(TABLE_NAME)
    return _table


def handler(event, context):
    table = get_table()
    table.put_item(Item={"pk": event["visitor"]})
    return {"ok": True}


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run lambda_2
# =============================================================================
import sys  # noqa: E402


class FakeTable:
    def __init__(self, name):
        self.name, self.items = name, []

    def put_item(self, Item):
        self.items.append(Item)


def test_table_created_once(monkeypatch):
    module = sys.modules[__name__]
    created = []

    def factory(name):
        created.append(name)
        return FakeTable(name)

    monkeypatch.setattr(module, "TABLE_FACTORY", factory)
    monkeypatch.setattr(module, "_table", None)
    for visitor in ("ada", "grace", "linus"):
        assert handler({"visitor": visitor}, None) == {"ok": True}
    assert created == ["visits"], "the table object must be created only once (cold start), then reused"
    assert [item["pk"] for item in get_table().items] == ["ada", "grace", "linus"]
