"""
Exercise lambda_5 — Idempotent event processing
===============================================
Book: chapter 11, "Idempotency" and chapter 7, "Conditional writes"
Exam: Domain 1 · Task 1.1 (idempotency, fault-tolerant design patterns)

Most event sources deliver *at least once*: SQS standard queues, SNS,
EventBridge, S3 notifications and Lambda async retries can all deliver
the same event twice. A payment handler must not charge twice.

Pattern: before doing the side effect, atomically record the event id in
DynamoDB with a *conditional* put (`attribute_not_exists(pk)`). If the
condition fails, the event was already handled, so skip it. Give the
record a TTL so the table cleans itself up.

Your task
---------
Implement `handle_payment(table, event, now)`:
  * record {"pk": event["payment_id"], "expires_at": <now + 24 h, epoch seconds>}
    with a conditional put,
  * if it was already recorded, return "duplicate" WITHOUT charging,
  * otherwise call charge(event["amount"]) and return "charged".
"""

# I AM NOT DONE

import time

from botocore.exceptions import ClientError

IDEMPOTENCY_TTL_SECONDS = 24 * 3600
CHARGES = []


def charge(amount: int) -> None:
    CHARGES.append(amount)


def handle_payment(table, event: dict, now=time.time) -> str:
    charge(event["amount"])  # TODO: guard the side effect with a conditional write
    return "charged"


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run lambda_5
# =============================================================================
import boto3  # noqa: E402
import pytest  # noqa: E402


@pytest.fixture
def table(aws):
    CHARGES.clear()
    ddb = boto3.resource("dynamodb")
    return ddb.create_table(
        TableName="idempotency",
        BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}],
        KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
    )


def test_duplicate_event_is_charged_once(table):
    event = {"payment_id": "pay-1", "amount": 4200}
    assert handle_payment(table, event) == "charged"
    assert handle_payment(table, event) == "duplicate"
    assert CHARGES == [4200]


def test_different_events_are_both_charged(table):
    assert handle_payment(table, {"payment_id": "pay-1", "amount": 10}) == "charged"
    assert handle_payment(table, {"payment_id": "pay-2", "amount": 20}) == "charged"
    assert CHARGES == [10, 20]


def test_record_has_ttl_in_epoch_seconds(table):
    handle_payment(table, {"payment_id": "pay-9", "amount": 1}, now=lambda: 1_800_000_000.7)
    item = table.get_item(Key={"pk": "pay-9"})["Item"]
    assert int(item["expires_at"]) == 1_800_000_000 + 86_400
