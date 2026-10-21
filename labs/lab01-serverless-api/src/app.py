"""lab01: a tiny items API.

API Gateway (REST, Lambda proxy integration) -> this function -> DynamoDB.
"""

import json
import logging
import os
import random
import uuid

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Created once per execution environment and reused by every invocation it serves.
TABLE = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
# The version that is running: lets you see the canary split from the client side.
VERSION = os.environ.get("AWS_LAMBDA_FUNCTION_VERSION", "$LATEST")
FAILURE_RATE = float(os.environ.get("FAILURE_RATE", "0"))


def response(status: int, body: dict) -> dict:
    """A Lambda proxy integration must return statusCode, headers and a *string* body."""
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json", "X-Function-Version": VERSION},
        "body": json.dumps(body),
    }


def create_item(event: dict) -> dict:
    try:
        data = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return response(400, {"message": "the body must be JSON"})
    name = data.get("name") if isinstance(data, dict) else None
    if not isinstance(name, str) or not name.strip():
        return response(400, {"message": "'name' is required"})
    item = {"id": str(uuid.uuid4()), "name": name.strip()}
    TABLE.put_item(Item=item)
    logger.info("created item %s", item["id"])
    return response(201, item)


def get_item(event: dict) -> dict:
    item_id = (event.get("pathParameters") or {}).get("id", "")
    item = TABLE.get_item(Key={"id": item_id}).get("Item")
    if item is None:
        return response(404, {"message": f"item {item_id} not found"})
    return response(200, item)


def handler(event, context):
    if random.random() < FAILURE_RATE:
        # An unhandled exception: Lambda reports an error, API Gateway answers 502.
        raise RuntimeError("simulated failure (FailureRate parameter)")
    method = event.get("httpMethod")
    if method == "POST":
        return create_item(event)
    if method == "GET":
        return get_item(event)
    return response(405, {"message": f"method {method} is not allowed"})
