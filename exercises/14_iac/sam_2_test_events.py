"""
Exercise sam_2 — Build test events for local testing
====================================================
Book: chapter 19, "Testing serverless applications" (book/src/ch19-testing.md)
Exam: Domain 3 · Task 3.3 (creating application test events: JSON payloads for Lambda, API Gateway, SAM)

`sam local invoke -e event.json` and `sam local generate-event apigateway aws-proxy`
let you test functions with realistic payloads. Your unit tests need the
same payloads. These helpers build them. They should match what AWS
really sends, including the surprising parts.

Your task
---------
  * `api_event(method, path, body, query, path_params, headers)`: a REST
    API (v1.0) Lambda proxy event with: resource, path, httpMethod,
    headers, queryStringParameters, pathParameters, body, isBase64Encoded,
    and requestContext {"stage": "test", "httpMethod": ..., "path": ...,
    "requestId": ...},
  * `sqs_event(*bodies)`: an SQS event with one record per body (dict
    bodies are JSON-encoded), messageId "msg-<i>".
The tests feed your events to a real handler.
"""

# I AM NOT DONE

import json
import uuid


def api_event(method: str, path: str, body: dict | None = None, query: dict | None = None,
              path_params: dict | None = None, headers: dict | None = None) -> dict:
    return {"httpMethod": method, "path": path, "body": body, "queryStringParameters": query or {}}  # TODO


def sqs_event(*bodies) -> dict:
    raise NotImplementedError  # TODO


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run sam_2
# =============================================================================


def orders_api(event, context):
    """A real handler: POST /orders creates, GET /orders/{id} reads."""
    if event["httpMethod"] == "POST":
        order = json.loads(event["body"])
        return {"statusCode": 201, "body": json.dumps({"created": order["sku"]})}
    order_id = (event.get("pathParameters") or {}).get("id")
    verbose = (event.get("queryStringParameters") or {}).get("verbose") == "true"
    return {"statusCode": 200, "body": json.dumps({"id": order_id, "verbose": verbose})}


def queue_worker(event, context):
    return [json.loads(record["body"])["sku"] for record in event["Records"] if record["eventSource"] == "aws:sqs"]


def test_post_event():
    event = api_event("POST", "/orders", body={"sku": "MUG-1"})
    assert isinstance(event["body"], str)
    assert event["queryStringParameters"] is None and event["pathParameters"] is None
    assert event["isBase64Encoded"] is False
    assert event["requestContext"]["stage"] == "test"
    assert orders_api(event, None) == {"statusCode": 201, "body": '{"created": "MUG-1"}'}


def test_get_event_with_parameters():
    event = api_event("GET", "/orders/{id}", path_params={"id": "o-7"}, query={"verbose": "true"})
    assert event["body"] is None
    assert json.loads(orders_api(event, None)["body"]) == {"id": "o-7", "verbose": True}


def test_sqs_event():
    event = sqs_event({"sku": "A"}, {"sku": "B"})
    assert [r["messageId"] for r in event["Records"]] == ["msg-0", "msg-1"]
    assert all(isinstance(r["body"], str) for r in event["Records"])
    assert queue_worker(event, None) == ["A", "B"]
