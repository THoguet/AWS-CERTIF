"""lab03: validate an uploaded CSV file of orders and summarize it.

Called by the state machine with {"bucket": ..., "key": ...}. Expected file format:

    order_id,amount
    o-1001,19.99
"""

import csv
import io
from decimal import Decimal, InvalidOperation

import boto3

s3 = boto3.client("s3")
EXPECTED_HEADER = ["order_id", "amount"]


class InvalidFile(Exception):
    """A business error: the state machine catches it by name and rejects the file (no retry)."""


def summarize(text: str) -> dict:
    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    if header != EXPECTED_HEADER:
        raise InvalidFile(f"expected header {EXPECTED_HEADER}, got {header}")
    rows, total = 0, Decimal("0")
    for line_number, row in enumerate(reader, start=2):
        if not row:
            continue
        try:
            _order_id, amount = row
            total += Decimal(amount)
        except (ValueError, InvalidOperation) as exc:
            raise InvalidFile(f"line {line_number} is invalid: {row}") from exc
        rows += 1
    if rows == 0:
        raise InvalidFile("the file contains no orders")
    total = total.quantize(Decimal("0.01"))
    # total as a string for DynamoDB ("N" values are strings), total_cents as an int for the Choice state
    return {"rows": rows, "total": str(total), "total_cents": int(total * 100)}


def handler(event, context):
    body = s3.get_object(Bucket=event["bucket"], Key=event["key"])["Body"].read()
    try:
        text = body.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise InvalidFile("the file is not UTF-8 text") from exc
    summary = summarize(text)
    print(f"{event['key']}: {summary}")
    return summary
