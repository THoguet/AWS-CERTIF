"""
Exercise secrets_3 — Write a Secrets Manager rotation function
==============================================================
Book: chapter 14, "Rotation" (book/src/ch14-secrets-config.md)
Exam: Domain 2 · Task 2.3 (using secret management services to secure sensitive data)

Secrets Manager rotates a secret by invoking a Lambda function FOUR times,
with event {"SecretId": arn, "ClientRequestToken": token, "Step": ...}:

  1. createSecret — generate a new value, store it as a new version
                    labelled AWSPENDING (version id = the token),
  2. setSecret    — apply the pending password to the database,
  3. testSecret   — log in with the pending password,
  4. finishSecret — move the AWSCURRENT label to the new version
                    (AWSPREVIOUS then labels the old one automatically).

Each step must be IDEMPOTENT (Secrets Manager may retry it). For RDS,
Aurora, Redshift and DocumentDB, AWS provides ready-made rotation
functions (and managed rotation for some services). You only write one
for custom secrets.

Your task
---------
Implement the four steps. `db` is a fake database with
set_password(user, password) and can_login(user, password).
(The functions are not called test_*, because pytest would collect them as tests.)
"""

# I AM NOT DONE

import json


def create_pending(sm, arn: str, token: str, generate_password) -> None:
    raise NotImplementedError  # TODO


def _pending(sm, arn: str, token: str) -> dict:
    return json.loads(sm.get_secret_value(SecretId=arn, VersionId=token, VersionStage="AWSPENDING")["SecretString"])


def set_pending(sm, arn: str, token: str, db) -> None:
    raise NotImplementedError  # TODO


def verify_pending(sm, arn: str, token: str, db) -> None:
    raise NotImplementedError  # TODO


def finish_rotation(sm, arn: str, token: str) -> None:
    raise NotImplementedError  # TODO


def handler(event, context, sm, db, generate_password):
    arn, token, step = event["SecretId"], event["ClientRequestToken"], event["Step"]
    if step == "createSecret":
        create_pending(sm, arn, token, generate_password)
    elif step == "setSecret":
        set_pending(sm, arn, token, db)
    elif step == "testSecret":
        verify_pending(sm, arn, token, db)
    elif step == "finishSecret":
        finish_rotation(sm, arn, token)
    else:
        raise ValueError(f"unknown step {step}")


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run secrets_3
# =============================================================================
import boto3  # noqa: E402
import pytest  # noqa: E402

TOKEN = "11111111-2222-3333-4444-555555555555"


class FakeDb:
    def __init__(self):
        self.passwords = {"app": "old-password"}

    def set_password(self, user, password):
        self.passwords[user] = password

    def can_login(self, user, password):
        return self.passwords.get(user) == password


@pytest.fixture
def env(aws):
    sm = boto3.client("secretsmanager")
    arn = sm.create_secret(Name="prod/db", SecretString=json.dumps({"username": "app", "password": "old-password"}))["ARN"]
    return sm, arn, FakeDb()


def _rotate(sm, arn, db):
    for step in ("createSecret", "setSecret", "testSecret", "finishSecret"):
        handler({"SecretId": arn, "ClientRequestToken": TOKEN, "Step": step}, None, sm, db, lambda: "new-password")


def test_full_rotation(env):
    sm, arn, db = env
    _rotate(sm, arn, db)
    current = json.loads(sm.get_secret_value(SecretId=arn, VersionStage="AWSCURRENT")["SecretString"])
    previous = json.loads(sm.get_secret_value(SecretId=arn, VersionStage="AWSPREVIOUS")["SecretString"])
    assert current == {"username": "app", "password": "new-password"}
    assert previous["password"] == "old-password"
    assert db.can_login("app", "new-password")


def test_create_step_is_idempotent(env):
    sm, arn, db = env
    passwords = iter(["first", "second"])
    event = {"SecretId": arn, "ClientRequestToken": TOKEN, "Step": "createSecret"}
    handler(event, None, sm, db, lambda: next(passwords))
    handler(event, None, sm, db, lambda: next(passwords))
    pending = json.loads(sm.get_secret_value(SecretId=arn, VersionId=TOKEN, VersionStage="AWSPENDING")["SecretString"])
    assert pending["password"] == "first"


def test_bad_pending_secret_fails_the_test_step(env):
    sm, arn, db = env
    handler({"SecretId": arn, "ClientRequestToken": TOKEN, "Step": "createSecret"}, None, sm, db, lambda: "new-password")
    with pytest.raises(RuntimeError):
        handler({"SecretId": arn, "ClientRequestToken": TOKEN, "Step": "testSecret"}, None, sm, db, None)
    assert json.loads(sm.get_secret_value(SecretId=arn, VersionStage="AWSCURRENT")["SecretString"])["password"] == "old-password"
