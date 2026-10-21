"""Offline tests for lab05 (moto + a fake X-Ray SDK). Run from the repo root: uv run pytest labs/lab05-observability"""

import contextlib
import importlib.util
import json
import sys
import types
from pathlib import Path

import boto3
import pytest

LAB = Path(__file__).resolve().parents[1]


class FakeSubsegment:
    def __init__(self, name, recorder):
        self.name, self.recorder = name, recorder

    def put_annotation(self, key, value):
        self.recorder.annotations[key] = value

    def put_metadata(self, key, value, namespace="default"):
        self.recorder.metadata[(namespace, key)] = value


class FakeRecorder:
    def __init__(self):
        self.annotations, self.metadata, self.subsegments = {}, {}, []

    @contextlib.contextmanager
    def in_subsegment(self, name):
        self.subsegments.append(name)
        yield FakeSubsegment(name, self)


@pytest.fixture
def app(aws, monkeypatch):
    """Load src/app.py with a fake aws_xray_sdk (the real one is installed by `sam build`)."""
    recorder = FakeRecorder()
    core = types.ModuleType("aws_xray_sdk.core")
    core.xray_recorder, core.patch_all = recorder, lambda: None
    monkeypatch.setitem(sys.modules, "aws_xray_sdk", types.ModuleType("aws_xray_sdk"))
    monkeypatch.setitem(sys.modules, "aws_xray_sdk.core", core)
    monkeypatch.setenv("TABLE_NAME", "orders")
    monkeypatch.setenv("_X_AMZN_TRACE_ID", "Root=1-6716a2f1-3f1c8a1e9b2d4c5e6f708192;Parent=53995c3f42cd8ad8;Sampled=1")
    boto3.resource("dynamodb").create_table(
        TableName="orders", BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
    )
    spec = importlib.util.spec_from_file_location("lab05_app", LAB / "src" / "app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.recorder = recorder
    return module


def event(**params):
    return {"httpMethod": "POST", "resource": "/checkout", "headers": {"X-Correlation-Id": "abc-123"},
            "queryStringParameters": {k: str(v) for k, v in params.items()} or None}


def json_lines(out):
    return [json.loads(line) for line in out.splitlines() if line.startswith("{")]


def test_successful_checkout_logs_traces_and_metrics(app, capsys):
    result = app.handler(event(tier="gold", amount=42.5, delay=0), None)
    assert result["statusCode"] == 200
    assert result["headers"]["X-Correlation-Id"] == "abc-123"
    assert app.recorder.annotations == {"customer_tier": "gold", "correlation_id": "abc-123"}
    assert app.recorder.subsegments == ["checkout", "payment-provider"]

    emf, log = json_lines(capsys.readouterr().out)
    metrics = emf["_aws"]["CloudWatchMetrics"][0]
    assert metrics["Namespace"] == "DvaLab05"
    for dimension in metrics["Dimensions"][0]:
        assert dimension in emf                       # every dimension must be a top-level key
    for metric in metrics["Metrics"]:
        assert isinstance(emf[metric["Name"]], (int, float))
    assert log["level"] == "INFO" and log["trace_id"] == "1-6716a2f1-3f1c8a1e9b2d4c5e6f708192"

    item_id = json.loads(result["body"])["order_id"]
    item = boto3.resource("dynamodb").Table("orders").get_item(Key={"id": item_id})["Item"]
    assert item["tier"] == "gold" and str(item["amount"]) == "42.5"


def test_failed_payment_logs_an_error_and_raises(app, capsys):
    with pytest.raises(RuntimeError):
        app.handler(event(tier="silver", delay=0, fail="true"), None)
    (log,) = json_lines(capsys.readouterr().out)
    assert log["level"] == "ERROR" and log["correlation_id"] == "abc-123"


def test_bad_parameters_fall_back_to_defaults(app):
    assert app.parse(event(tier="platinum", amount="abc", delay=99)) == ("free", 25.0, 0.1, False)
    assert app.parse({"queryStringParameters": None}) == ("free", 25.0, 0.1, False)
    assert app.parse(event(delay=99))[2] == 5.0
