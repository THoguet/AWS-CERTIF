"""
Exercise lambda_8 — Versions, aliases and canary releases
=========================================================
Book: chapter 16, "Lambda versions and aliases" (book/src/ch16-sam-serverless-deploy.md)
Exam: Domain 3 · Tasks 3.2 / 3.4 (Lambda versions and aliases, deployment strategies, rollbacks)

  * $LATEST is mutable. A published VERSION (1, 2, 3...) is an immutable
    snapshot of code + configuration, with its own ARN.
  * An ALIAS ("live", "beta") is a named pointer to a version. Clients and
    event sources call the alias, so you can switch versions without
    touching them.
  * An alias can split traffic between two versions (weighted alias):
    that is how SAM/CodeDeploy canary and linear deployments work.
    Rollback = point the alias back to the old version.

Your task
---------
  * `release(client, name, zip_bytes)`: upload new code, publish a version,
    return the version number (a string),
  * `start_canary(client, name, stable, candidate, weight)`: alias "live"
    keeps `stable` but sends `weight` (e.g. 0.1 = 10%) of traffic to `candidate`,
  * `promote(client, name, candidate)`: 100% of "live" on `candidate`.
"""


def release(client, name: str, zip_bytes: bytes) -> str:
    client.update_function_code(FunctionName=name, ZipFile=zip_bytes)
    return client.publish_version(FunctionName=name)["Version"]


def start_canary(client, name: str, stable: str, candidate: str, weight: float = 0.1) -> None:
    client.update_alias(
        FunctionName=name,
        Name="live",
        FunctionVersion=stable,
        RoutingConfig={"AdditionalVersionWeights": {candidate: weight}},
    )


def promote(client, name: str, candidate: str) -> None:
    client.update_alias(FunctionName=name, Name="live", FunctionVersion=candidate, RoutingConfig={"AdditionalVersionWeights": {}})


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run lambda_8
# =============================================================================
import json  # noqa: E402

import boto3  # noqa: E402
import pytest  # noqa: E402

from awslings.testing import lambda_zip  # noqa: E402


@pytest.fixture
def client(aws):
    iam = boto3.client("iam")
    role = iam.create_role(RoleName="r", AssumeRolePolicyDocument=json.dumps({"Version": "2012-10-17", "Statement": []}))["Role"]["Arn"]
    lam = boto3.client("lambda")
    lam.create_function(FunctionName="checkout", Runtime="python3.12", Role=role, Handler="app.handler", Code={"ZipFile": lambda_zip()})
    v1 = lam.publish_version(FunctionName="checkout")["Version"]
    lam.create_alias(FunctionName="checkout", Name="live", FunctionVersion=v1)
    return lam


def test_release_publishes_a_version(client):
    version = release(client, "checkout", lambda_zip({"app.py": "def handler(e, c):\n    return 2\n"}))
    assert version == "2"
    versions = [v["Version"] for v in client.list_versions_by_function(FunctionName="checkout")["Versions"]]
    assert "2" in versions


def test_canary_then_promote(client):
    candidate = release(client, "checkout", lambda_zip({"app.py": "def handler(e, c):\n    return 2\n"}))
    start_canary(client, "checkout", "1", candidate, 0.1)
    alias = client.get_alias(FunctionName="checkout", Name="live")
    assert alias["FunctionVersion"] == "1"
    assert alias["RoutingConfig"]["AdditionalVersionWeights"] == {candidate: 0.1}
    promote(client, "checkout", candidate)
    alias = client.get_alias(FunctionName="checkout", Name="live")
    assert alias["FunctionVersion"] == candidate
    assert not alias.get("RoutingConfig", {}).get("AdditionalVersionWeights")
