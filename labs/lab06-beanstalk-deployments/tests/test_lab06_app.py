"""Offline tests for lab06. Run from the repo root: uv run pytest labs/lab06-beanstalk-deployments"""

import importlib.util
import json
from pathlib import Path

import yaml

LAB = Path(__file__).resolve().parents[1]


def load_app():
    spec = importlib.util.spec_from_file_location("lab06_application", LAB / "app" / "application.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def call(app, path="/"):
    seen = {}

    def start_response(status, headers):
        seen["status"], seen["headers"] = status, dict(headers)

    body = b"".join(app.application({"PATH_INFO": path, "REQUEST_METHOD": "GET"}, start_response))
    return seen["status"], seen["headers"], json.loads(body)


def test_healthy_release(monkeypatch):
    monkeypatch.setenv("COLOR", "blue")
    status, headers, body = call(load_app())
    assert status == "200 OK" and headers["Content-Type"] == "application/json"
    assert body["version"] == "1" and body["color"] == "blue" and body["instance"]


def test_broken_release_fails_health_checks():
    app = load_app()
    app.BROKEN = True
    status, _, body = call(app)
    assert status.startswith("500") and "broken" in body["error"]


def test_ebextensions_settings():
    config = yaml.safe_load((LAB / "app" / ".ebextensions" / "01-environment.config").read_text())
    settings = config["option_settings"]
    assert settings["aws:elasticbeanstalk:command"]["DeploymentPolicy"] == "Rolling"
    assert settings["aws:autoscaling:asg"] == {"MinSize": 2, "MaxSize": 2}
    assert settings["aws:elasticbeanstalk:application:environment"]["COLOR"] == "blue"
