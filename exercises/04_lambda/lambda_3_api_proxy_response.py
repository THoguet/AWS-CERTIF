"""
Exercise lambda_3 — Lambda proxy integration responses
======================================================
Book: chapter 6, "Integrations: proxy vs non-proxy" (book/src/ch06-api-gateway-appsync.md)
Exam: Domain 1 · Task 1.1 (creating APIs, overriding status codes), Domain 4 · Task 4.1 (HTTP errors)

With Lambda *proxy* integration, API Gateway passes the whole HTTP request
as the event and expects this exact response shape back:

    {"statusCode": 200, "headers": {"Content-Type": "application/json"}, "body": "<a string>"}

If the shape is wrong (body is a dict, statusCode missing...), the
client gets a **502 Bad Gateway** ("Malformed Lambda proxy response").
Two more traps:
  * `queryStringParameters` and `pathParameters` are None (not {}) when absent,
  * with proxy integration, CORS headers must come from YOUR code.

Your task
---------
  * `build_response(status_code, payload)`: proxy response with a JSON
    body, Content-Type application/json and Access-Control-Allow-Origin
    set to ALLOWED_ORIGIN,
  * `handler(event, context)`: GET /orders?status=OPEN|SHIPPED returns
    {"orders": [...]} filtered by status (all orders without a filter).
    An unknown status returns 400 with {"message": "invalid status"}.
"""

# I AM NOT DONE

import json

ALLOWED_ORIGIN = "https://app.example.com"
ORDERS = [
    {"id": "o-1", "status": "OPEN"},
    {"id": "o-2", "status": "SHIPPED"},
    {"id": "o-3", "status": "OPEN"},
]
VALID_STATUSES = {"OPEN", "SHIPPED"}


def build_response(status_code: int, payload: dict) -> dict:
    return {"status": status_code, "body": payload}  # TODO: this shape gives a 502 Bad Gateway


def handler(event, context):
    status = event["queryStringParameters"]["status"]  # TODO: crashes when there is no query string
    return build_response(200, {"orders": [o for o in ORDERS if o["status"] == status]})


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run lambda_3
# =============================================================================


def _event(query=None):
    return {"httpMethod": "GET", "path": "/orders", "queryStringParameters": query, "pathParameters": None, "body": None}


def _check_shape(response):
    assert isinstance(response["statusCode"], int)
    assert isinstance(response["body"], str), "the body must be a JSON *string*"
    assert response["headers"]["Content-Type"] == "application/json"
    assert response["headers"]["Access-Control-Allow-Origin"] == ALLOWED_ORIGIN
    return json.loads(response["body"])


def test_no_query_string_returns_everything():
    response = handler(_event(None), None)
    assert response["statusCode"] == 200
    assert len(_check_shape(response)["orders"]) == 3


def test_filter_by_status():
    response = handler(_event({"status": "OPEN"}), None)
    assert response["statusCode"] == 200
    assert [o["id"] for o in _check_shape(response)["orders"]] == ["o-1", "o-3"]


def test_invalid_status_is_a_client_error():
    response = handler(_event({"status": "LOST"}), None)
    assert response["statusCode"] == 400
    assert _check_shape(response) == {"message": "invalid status"}
