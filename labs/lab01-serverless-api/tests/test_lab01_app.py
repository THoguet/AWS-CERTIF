"""Offline tests for the lab01 function (moto). Run from the repo root: uv run pytest labs/lab01-serverless-api"""

import importlib.util
import json
from pathlib import Path

import boto3
import pytest

LAB = Path(__file__).resolve().parents[1]
EVENTS = LAB / "events"


def load_app(monkeypatch, failure_rate="0"):
    """Import src/app.py fresh, as Lambda would in a new execution environment."""
    monkeypatch.setenv("TABLE_NAME", "items")
    monkeypatch.setenv("FAILURE_RATE", failure_rate)
    monkeypatch.setenv("AWS_LAMBDA_FUNCTION_VERSION", "7")
    spec = importlib.util.spec_from_file_location("lab01_app", LAB / "src" / "app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def table(aws):
    ddb = boto3.resource("dynamodb")
    return ddb.create_table(
        TableName="items",
        BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
    )


def event(name):
    return json.loads((EVENTS / name).read_text())


def test_create_then_get(table, monkeypatch):
    app = load_app(monkeypatch)
    created = app.handler(event("create-item.json"), None)
    assert created["statusCode"] == 201
    assert created["headers"]["X-Function-Version"] == "7"
    item = json.loads(created["body"])
    assert item["name"] == "exam voucher"

    get = event("get-item.json")
    get["pathParameters"] = {"id": item["id"]}
    found = app.handler(get, None)
    assert found["statusCode"] == 200
    assert json.loads(found["body"]) == item


def test_unknown_item_is_404(table, monkeypatch):
    app = load_app(monkeypatch)
    assert app.handler(event("get-item.json"), None)["statusCode"] == 404


@pytest.mark.parametrize("body", [None, "not json", "[]", '{"name": ""}', '{"name": 42}'])
def test_invalid_bodies_are_400(table, monkeypatch, body):
    app = load_app(monkeypatch)
    request = event("create-item.json")
    request["body"] = body
    result = app.handler(request, None)
    assert result["statusCode"] == 400
    assert isinstance(result["body"], str)


def test_failure_rate_one_always_raises(table, monkeypatch):
    app = load_app(monkeypatch, failure_rate="1")
    with pytest.raises(RuntimeError):
        app.handler(event("get-item.json"), None)
