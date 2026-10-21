"""
Exercise ddb_9 — Processing DynamoDB Streams
============================================
Book: chapter 7, "DynamoDB Streams" (book/src/ch07-dynamodb.md)
Exam: Domain 1 · Tasks 1.2 / 1.3 (event-driven architecture, event source mapping)

A stream records every item-level change for 24 hours. A Lambda function
attached through an event source mapping receives batches of records,
in order per item (per partition key). The stream view type decides what
each record contains:
  * KEYS_ONLY          — only the key attributes,
  * NEW_IMAGE          — the item after the change,
  * OLD_IMAGE          — the item before the change,
  * NEW_AND_OLD_IMAGES — both (needed to detect WHAT changed).

Images use the low-level typed format ({"S": "..."}, {"N": "..."}).

Your task
---------
Implement `handler(event, context)` for a Users table stream
(NEW_AND_OLD_IMAGES), returning a list of actions:
  * INSERT                       → ("welcome", email)
  * MODIFY with a changed email  → ("confirm-email", new email)
  * MODIFY with the same email   → nothing
  * REMOVE                       → ("goodbye", old email)
"""

# I AM NOT DONE

from boto3.dynamodb.types import TypeDeserializer

_deserializer = TypeDeserializer()


def to_python(image: dict) -> dict:
    raise NotImplementedError  # TODO


def handler(event, context) -> list[tuple[str, str]]:
    # TODO
    raise NotImplementedError


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run ddb_9
# =============================================================================
from decimal import Decimal  # noqa: E402


def _record(name, new=None, old=None):
    change = {"Keys": {"pk": {"S": "u-1"}}, "StreamViewType": "NEW_AND_OLD_IMAGES"}
    if new:
        change["NewImage"] = new
    if old:
        change["OldImage"] = old
    return {"eventID": "1", "eventName": name, "eventSource": "aws:dynamodb", "dynamodb": change}


ADA = {"pk": {"S": "u-1"}, "email": {"S": "ada@example.com"}, "logins": {"N": "3"}}
ADA_NEW_EMAIL = {"pk": {"S": "u-1"}, "email": {"S": "ada@newmail.com"}, "logins": {"N": "3"}}
ADA_MORE_LOGINS = {"pk": {"S": "u-1"}, "email": {"S": "ada@example.com"}, "logins": {"N": "4"}}


def test_to_python():
    assert to_python(ADA) == {"pk": "u-1", "email": "ada@example.com", "logins": Decimal(3)}


def test_actions():
    event = {
        "Records": [
            _record("INSERT", new=ADA),
            _record("MODIFY", new=ADA_MORE_LOGINS, old=ADA),
            _record("MODIFY", new=ADA_NEW_EMAIL, old=ADA_MORE_LOGINS),
            _record("REMOVE", old=ADA_NEW_EMAIL),
        ]
    }
    assert handler(event, None) == [
        ("welcome", "ada@example.com"),
        ("confirm-email", "ada@newmail.com"),
        ("goodbye", "ada@newmail.com"),
    ]
