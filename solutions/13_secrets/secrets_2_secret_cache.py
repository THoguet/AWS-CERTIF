"""
Exercise secrets_2 — Caching secrets in a Lambda function
=========================================================
Book: chapter 14, "AWS Secrets Manager" (book/src/ch14-secrets-config.md)
Exam: Domain 2 · Task 2.3 (using secret management services), Domain 4 · Task 4.3

Calling GetSecretValue on every invocation adds latency, costs money
($0.05 per 10,000 API calls) and can hit API quotas. Instead, cache the
secret in the execution environment for a few minutes:
  * AWS provides caching clients (e.g. aws-secretsmanager-caching for
    Python and Java) and the "AWS Parameters and Secrets Lambda
    Extension", a local HTTP cache available as a Lambda layer,
  * the TTL keeps rotation working: after a rotation, the new value is
    picked up within one TTL. On an authentication error, force a refresh.

Your task
---------
Implement SecretCache.get(secret_id) (JSON-decoded secret, cached `ttl`
seconds) and SecretCache.refresh(secret_id).
"""

import json
import time


class SecretCache:
    def __init__(self, client, ttl: float = 300, clock=time.monotonic):
        self.client, self.ttl, self.clock = client, ttl, clock
        self._entries: dict[str, tuple[dict, float]] = {}

    def get(self, secret_id: str) -> dict:
        entry = self._entries.get(secret_id)
        if entry is None or self.clock() - entry[1] >= self.ttl:
            value = json.loads(self.client.get_secret_value(SecretId=secret_id)["SecretString"])
            entry = (value, self.clock())
            self._entries[secret_id] = entry
        return entry[0]

    def refresh(self, secret_id: str) -> None:
        self._entries.pop(secret_id, None)


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run secrets_2
# =============================================================================
import boto3  # noqa: E402
import pytest  # noqa: E402


class CountingClient:
    def __init__(self, real):
        self.real, self.calls = real, 0

    def get_secret_value(self, **kwargs):
        self.calls += 1
        return self.real.get_secret_value(**kwargs)


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


@pytest.fixture
def env(aws):
    sm = boto3.client("secretsmanager")
    sm.create_secret(Name="prod/db", SecretString=json.dumps({"username": "app", "password": "v1"}))
    return sm, CountingClient(sm), Clock()


def test_cached_within_ttl(env):
    _, client, clock = env
    cache = SecretCache(client, ttl=300, clock=clock)
    for _ in range(5):
        assert cache.get("prod/db")["password"] == "v1"
        clock.now += 30
    assert client.calls == 1


def test_expires_after_ttl(env):
    sm, client, clock = env
    cache = SecretCache(client, ttl=300, clock=clock)
    cache.get("prod/db")
    sm.put_secret_value(SecretId="prod/db", SecretString=json.dumps({"username": "app", "password": "v2"}))
    clock.now += 299
    assert cache.get("prod/db")["password"] == "v1"
    clock.now += 1
    assert cache.get("prod/db")["password"] == "v2"
    assert client.calls == 2


def test_refresh(env):
    sm, client, clock = env
    cache = SecretCache(client, ttl=300, clock=clock)
    cache.get("prod/db")
    sm.put_secret_value(SecretId="prod/db", SecretString=json.dumps({"username": "app", "password": "v2"}))
    cache.refresh("prod/db")
    assert cache.get("prod/db")["password"] == "v2"
