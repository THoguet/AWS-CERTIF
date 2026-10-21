"""Shared pytest configuration for awslings exercises and solutions.

Every exercise test runs against moto, an in-memory mock of AWS. The settings
below guarantee that no test can ever reach a real AWS account, even if you
have credentials or profiles configured on your machine.
"""

import os
from pathlib import Path

import pytest

_FAKE_ENV = {
    "AWS_ACCESS_KEY_ID": "testing",
    "AWS_SECRET_ACCESS_KEY": "testing",
    "AWS_SECURITY_TOKEN": "testing",
    "AWS_SESSION_TOKEN": "testing",
    "AWS_DEFAULT_REGION": "eu-west-3",
}
for _key in ("AWS_PROFILE", "AWS_DEFAULT_PROFILE", "AWS_REGION"):
    os.environ.pop(_key, None)
os.environ.update(_FAKE_ENV)
# Never read ~/.aws/config or ~/.aws/credentials during tests.
_NOWHERE = str(Path(__file__).parent / ".awslings" / "no-aws-config")
os.environ["AWS_CONFIG_FILE"] = _NOWHERE
os.environ["AWS_SHARED_CREDENTIALS_FILE"] = _NOWHERE

from moto import mock_aws  # noqa: E402  (import after the environment is sanitised)

REGION = "eu-west-3"  # Paris


@pytest.fixture
def aws():
    """Start moto: every boto3 call made during the test hits the local mock."""
    with mock_aws():
        yield


@pytest.fixture
def region():
    return REGION
