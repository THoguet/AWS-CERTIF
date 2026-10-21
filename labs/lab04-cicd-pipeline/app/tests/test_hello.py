"""Unit tests run by CodeBuild in the pre_build phase (and by `uv run pytest labs` locally)."""

import importlib.util
import json
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("lab04_hello", APP / "src" / "hello.py")
hello = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hello)


def test_greeting_defaults_to_world():
    assert hello.greeting("staging", None) == "Hello, world, from staging!"
    assert hello.greeting("staging", "  ") == "Hello, world, from staging!"


def test_greeting_uses_the_name():
    assert hello.greeting("prod", " Ada ") == "Hello, Ada, from prod!"


def test_handler_returns_a_proxy_response(monkeypatch):
    monkeypatch.setenv("STAGE", "staging")
    result = hello.handler({"queryStringParameters": {"name": "Ada"}}, None)
    assert result["statusCode"] == 200
    assert json.loads(result["body"]) == {"message": "Hello, Ada, from staging!", "release": hello.RELEASE}


def test_handler_without_query_string(monkeypatch):
    monkeypatch.setenv("STAGE", "prod")
    assert json.loads(hello.handler({}, None)["body"])["message"] == "Hello, world, from prod!"
