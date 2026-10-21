"""
Exercise ddb_8 — Transactions
=============================
Book: chapter 7, "Transactions" (book/src/ch07-dynamodb.md)
Exam: Domain 1 · Task 1.3

Moving points from one account to another touches two items. If the
process crashes between the debit and the credit, points vanish.

TransactWriteItems applies up to 100 actions (Put, Update, Delete,
ConditionCheck) on items in one or more tables ALL-OR-NOTHING (ACID).
Transactions cost twice the capacity of normal writes (2 WCU per KB).
If any condition fails, the whole transaction is cancelled with
TransactionCanceledException, whose CancellationReasons tell you which
action failed.

Your task
---------
Implement `transfer(client, from_id, to_id, amount, transfer_id)` on
table "Accounts" (key "pk", numeric attribute "balance"):
  1. debit `from_id` only if its balance >= amount,
  2. credit `to_id` (the account must exist: attribute_exists(pk)),
  3. write a ledger item {"pk": "transfer#<transfer_id>", "amount": ...}
     that must not exist yet (so a retried request is not applied twice),
  4. raise InsufficientFunds when the debit condition fails.
"""

from botocore.exceptions import ClientError


class InsufficientFunds(Exception):
    pass


def transfer(client, from_id: str, to_id: str, amount: int, transfer_id: str) -> None:
    value = {":amount": {"N": str(amount)}}
    try:
        client.transact_write_items(
            TransactItems=[
                {
                    "Update": {
                        "TableName": "Accounts",
                        "Key": {"pk": {"S": from_id}},
                        "UpdateExpression": "SET balance = balance - :amount",
                        "ConditionExpression": "balance >= :amount",
                        "ExpressionAttributeValues": value,
                    }
                },
                {
                    "Update": {
                        "TableName": "Accounts",
                        "Key": {"pk": {"S": to_id}},
                        "UpdateExpression": "SET balance = balance + :amount",
                        "ConditionExpression": "attribute_exists(pk)",
                        "ExpressionAttributeValues": value,
                    }
                },
                {
                    "Put": {
                        "TableName": "Accounts",
                        "Item": {"pk": {"S": f"transfer#{transfer_id}"}, "amount": {"N": str(amount)}},
                        "ConditionExpression": "attribute_not_exists(pk)",
                    }
                },
            ]
        )
    except ClientError as error:
        reasons = error.response.get("CancellationReasons", [])
        if reasons and reasons[0].get("Code") == "ConditionalCheckFailed":
            raise InsufficientFunds(from_id) from error
        raise


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run ddb_8
# =============================================================================
import boto3  # noqa: E402
import pytest  # noqa: E402


@pytest.fixture
def client(aws):
    c = boto3.client("dynamodb")
    c.create_table(
        TableName="Accounts",
        BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}],
        KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
    )
    c.put_item(TableName="Accounts", Item={"pk": {"S": "alice"}, "balance": {"N": "100"}})
    c.put_item(TableName="Accounts", Item={"pk": {"S": "bob"}, "balance": {"N": "0"}})
    return c


def _balance(client, pk):
    return int(client.get_item(TableName="Accounts", Key={"pk": {"S": pk}})["Item"]["balance"]["N"])


def test_successful_transfer(client):
    transfer(client, "alice", "bob", 30, "t-1")
    assert (_balance(client, "alice"), _balance(client, "bob")) == (70, 30)
    ledger = client.get_item(TableName="Accounts", Key={"pk": {"S": "transfer#t-1"}})
    assert ledger["Item"]["amount"]["N"] == "30"


def test_insufficient_funds_changes_nothing(client):
    with pytest.raises(InsufficientFunds):
        transfer(client, "bob", "alice", 10, "t-2")
    assert (_balance(client, "alice"), _balance(client, "bob")) == (100, 0)
    assert "Item" not in client.get_item(TableName="Accounts", Key={"pk": {"S": "transfer#t-2"}})


def test_replayed_transfer_is_rejected(client):
    transfer(client, "alice", "bob", 30, "t-1")
    with pytest.raises(ClientError):
        transfer(client, "alice", "bob", 30, "t-1")
    assert (_balance(client, "alice"), _balance(client, "bob")) == (70, 30)


def test_unknown_recipient_is_rejected(client):
    with pytest.raises(ClientError):
        transfer(client, "alice", "mallory", 10, "t-3")
    assert _balance(client, "alice") == 100
