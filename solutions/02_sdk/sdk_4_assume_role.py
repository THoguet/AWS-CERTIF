"""
Exercise sdk_4 — Assume a role with STS
=======================================
Book: chapter 3, "AWS STS" (book/src/ch03-cli-sdk-sts.md)
Exam: Domain 2 · Task 2.1 (assuming an IAM role, making authenticated calls to AWS services)

An auditing script runs with its own identity but must read data through
the `auditor` role, possibly in another account. STS AssumeRole returns
temporary credentials: an access key id (starting with ASIA), a secret key,
a session token, and an expiration.

The session name appears in the assumed-role ARN
(arn:aws:sts::<account>:assumed-role/<role>/<session-name>) and in
CloudTrail. Use it to identify who did what.

Your task
---------
  * `assume(role_arn, session_name, duration_seconds)`: call STS and return
    the "Credentials" dict,
  * `client_as(role_arn, session_name, service)`: return a boto3 client for
    `service` (region eu-west-3) that uses the role's temporary credentials,
    with a 15 minute (900 s) session.
"""

import boto3


def assume(role_arn: str, session_name: str, duration_seconds: int = 900) -> dict:
    sts = boto3.client("sts", region_name="eu-west-3")
    response = sts.assume_role(RoleArn=role_arn, RoleSessionName=session_name, DurationSeconds=duration_seconds)
    return response["Credentials"]


def client_as(role_arn: str, session_name: str, service: str):
    creds = assume(role_arn, session_name, 900)
    return boto3.client(
        service,
        region_name="eu-west-3",
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
    )


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run sdk_4
# =============================================================================
import json  # noqa: E402
from datetime import datetime, timezone  # noqa: E402
from unittest import mock  # noqa: E402

import pytest  # noqa: E402


@pytest.fixture
def role_arn(aws):
    trust = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Principal": {"AWS": "arn:aws:iam::123456789012:root"}, "Action": "sts:AssumeRole"}],
    }
    return boto3.client("iam").create_role(RoleName="auditor", AssumeRolePolicyDocument=json.dumps(trust))["Role"]["Arn"]


def test_assume_returns_temporary_credentials(role_arn):
    creds = assume(role_arn, "nightly-audit", 900)
    assert set(creds) >= {"AccessKeyId", "SecretAccessKey", "SessionToken", "Expiration"}
    lifetime = (creds["Expiration"] - datetime.now(timezone.utc)).total_seconds()
    assert 800 < lifetime <= 900


def test_client_uses_assumed_role(role_arn):
    sts = client_as(role_arn, "nightly-audit", "sts")
    assert sts.get_caller_identity()["Arn"] == "arn:aws:sts::123456789012:assumed-role/auditor/nightly-audit"


def test_session_token_is_passed(role_arn):
    real_client = boto3.client
    with mock.patch.object(boto3, "client", side_effect=real_client) as spy:
        client_as(role_arn, "nightly-audit", "s3")
    service_calls = [c for c in spy.call_args_list if c.args and c.args[0] == "s3"]
    assert service_calls, "create the service client with boto3.client(...)"
    kwargs = service_calls[-1].kwargs
    assert kwargs.get("aws_session_token"), "temporary credentials need the session token"
    assert kwargs.get("aws_access_key_id") and kwargs.get("aws_secret_access_key")
