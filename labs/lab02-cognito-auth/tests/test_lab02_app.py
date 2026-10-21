"""Offline tests for lab02. Run from the repo root: uv run pytest labs/lab02-cognito-auth"""

import base64
import importlib.util
import json
from pathlib import Path

import pytest

LAB = Path(__file__).resolve().parents[1]


def load(name, relpath):
    spec = importlib.util.spec_from_file_location(name, LAB / relpath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


app = load("lab02_app", "src/app.py")
jwt = load("lab02_decode_jwt", "scripts/decode_jwt.py")


def event(route, claims=None):
    context = {"stage": "dev", "requestId": "r-1"}
    if claims is not None:
        context["authorizer"] = {"claims": claims}
    return {"resource": route, "path": route, "httpMethod": "GET", "headers": {}, "requestContext": context}


CLAIMS = {"sub": "1234", "email": "dev@example.com", "token_use": "id",
          "iss": "https://cognito-idp.eu-west-3.amazonaws.com/eu-west-3_example"}


def test_health_needs_no_claims():
    assert app.handler(event("/health"), None)["statusCode"] == 200


def test_me_returns_the_verified_claims():
    body = json.loads(app.handler(event("/me", CLAIMS), None)["body"])
    assert body["email"] == "dev@example.com"
    assert body["token_use"] == "id"
    assert body["groups"] == []


@pytest.mark.parametrize("groups, status", [
    (None, 403), ("readers", 403), ("admins", 200), ("[readers, admins]", 200), (["admins"], 200),
])
def test_admin_requires_the_admins_group(groups, status):
    claims = dict(CLAIMS)
    if groups is not None:
        claims["cognito:groups"] = groups
    assert app.handler(event("/admin", claims), None)["statusCode"] == status


def test_decode_jwt_reads_header_and_claims(capsys):
    def part(obj):
        return base64.urlsafe_b64encode(json.dumps(obj).encode()).decode().rstrip("=")

    token = ".".join([part({"alg": "RS256", "kid": "k1"}), part({**CLAIMS, "exp": 1767225600}),
                      base64.urlsafe_b64encode(b"signature").decode().rstrip("=")])
    header, claims, signature = jwt.decode(token)
    assert header["kid"] == "k1" and claims["email"] == "dev@example.com" and signature == b"signature"
    assert jwt.main(["decode_jwt.py", token]) == 0
    assert "2026-01-01T00:00:00+00:00" in capsys.readouterr().out
