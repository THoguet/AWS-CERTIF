"""
Exercise res_2 — Serializing data for DynamoDB and JSON APIs
============================================================
Book: chapter 11, "Serialization" and chapter 7, "Data types"
Exam: Domain 1 · Task 1.3 (serializing and deserializing data to provide persistence to a data store)

Three classic serialization bugs with Python + DynamoDB:
  1. `TypeError: Float types are not supported. Use Decimal types instead.`
     boto3 maps DynamoDB numbers to decimal.Decimal, never float.
  2. `Decimal(0.1)` == 0.1000000000000000055511151231257827..., so build
     Decimals from strings.
  3. Returning a DynamoDB item from an API: `json.dumps` fails on Decimal.

Your task
---------
  * `to_item(order)`: Order → dict ready for table.put_item (floats as
    Decimal, created_at as an ISO 8601 UTC string, status as its value),
  * `from_item(item)`: dict from DynamoDB → Order,
  * `to_json(item)`: JSON string of a DynamoDB item (Decimal → int/float).
"""

# I AM NOT DONE

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum


class Status(Enum):
    NEW = "NEW"
    PAID = "PAID"


@dataclass
class Order:
    order_id: str
    total: float
    quantity: int
    created_at: datetime
    status: Status


def to_item(order: Order) -> dict:
    return dict(order.__dict__)  # TODO: floats, datetimes and enums are not valid DynamoDB values


def from_item(item: dict) -> Order:
    raise NotImplementedError  # TODO


def _json_default(value):
    raise TypeError(f"cannot serialize {type(value).__name__}")  # TODO: handle Decimal


def to_json(item: dict) -> str:
    return json.dumps(item, default=_json_default, sort_keys=True)


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run res_2
# =============================================================================
from datetime import timezone  # noqa: E402

import boto3  # noqa: E402

ORDER = Order("o-1", 19.99, 3, datetime(2026, 10, 21, 9, 30, tzinfo=timezone.utc), Status.PAID)


def test_to_item_types():
    item = to_item(ORDER)
    assert item["total"] == Decimal("19.99"), "build the Decimal from a string"
    assert item["created_at"] == "2026-10-21T09:30:00+00:00"
    assert item["status"] == "PAID"


def test_round_trip_through_dynamodb(aws):
    table = boto3.resource("dynamodb").create_table(
        TableName="Orders",
        BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[{"AttributeName": "order_id", "AttributeType": "S"}],
        KeySchema=[{"AttributeName": "order_id", "KeyType": "HASH"}],
    )
    table.put_item(Item=to_item(ORDER))
    assert from_item(table.get_item(Key={"order_id": "o-1"})["Item"]) == ORDER


def test_json_of_dynamodb_item():
    item = {"order_id": "o-1", "total": Decimal("19.99"), "quantity": Decimal("3")}
    assert to_json(item) == '{"order_id": "o-1", "quantity": 3, "total": 19.99}'
