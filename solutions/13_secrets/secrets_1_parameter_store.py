"""
Exercise secrets_1 — Configuration from SSM Parameter Store
===========================================================
Book: chapter 14, "Systems Manager Parameter Store" (book/src/ch14-secrets-config.md)
Exam: Domain 2 · Task 2.3 (secrets management), Domain 3 · Task 3.1 (accessing application configuration)

Parameter Store holds configuration and secrets in a HIERARCHY:
    /shop/prod/db/host        String
    /shop/prod/db/password    SecureString (encrypted with KMS)
    /shop/prod/features       StringList
  * GetParametersByPath + Recursive=True loads a whole subtree,
  * WithDecryption=True decrypts SecureStrings (the caller also needs
    kms:Decrypt on the key!),
  * tiers: Standard (free, 4 KB values, 10,000 parameters) and Advanced
    (paid, 8 KB, parameter policies such as expiration),
  * no built-in rotation (that is Secrets Manager's job).

Your task
---------
  * `put_secret(ssm, name, value, key_id)`: store (or overwrite) a
    SecureString encrypted with `key_id`,
  * `load_config(ssm, app, env)`: return {"db/host": ..., "db/password": ...}
    for every parameter under /<app>/<env>/ (all levels, decrypted,
    across pages).
"""


def put_secret(ssm, name: str, value: str, key_id: str) -> None:
    ssm.put_parameter(Name=name, Value=value, Type="SecureString", KeyId=key_id, Overwrite=True)


def load_config(ssm, app: str, env: str) -> dict[str, str]:
    prefix = f"/{app}/{env}/"
    config = {}
    for page in ssm.get_paginator("get_parameters_by_path").paginate(Path=prefix, Recursive=True, WithDecryption=True):
        for parameter in page["Parameters"]:
            config[parameter["Name"][len(prefix):]] = parameter["Value"]
    return config


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run secrets_1
# =============================================================================
import boto3  # noqa: E402
import pytest  # noqa: E402


@pytest.fixture
def env(aws):
    ssm, kms = boto3.client("ssm"), boto3.client("kms")
    key_id = kms.create_key(Description="config")["KeyMetadata"]["KeyId"]
    ssm.put_parameter(Name="/shop/prod/db/host", Value="db.internal", Type="String")
    ssm.put_parameter(Name="/shop/dev/db/host", Value="localhost", Type="String")
    for i in range(12):
        ssm.put_parameter(Name=f"/shop/prod/flags/flag{i:02d}", Value="on", Type="String")
    return ssm, key_id


def test_secure_string(env):
    ssm, key_id = env
    put_secret(ssm, "/shop/prod/db/password", "s3cr3t!", key_id)
    put_secret(ssm, "/shop/prod/db/password", "n3w-s3cr3t!", key_id)
    parameter = ssm.get_parameter(Name="/shop/prod/db/password", WithDecryption=True)["Parameter"]
    assert parameter["Type"] == "SecureString"
    assert parameter["Value"] == "n3w-s3cr3t!"


def test_load_whole_tree(env):
    ssm, key_id = env
    put_secret(ssm, "/shop/prod/db/password", "s3cr3t!", key_id)
    config = load_config(ssm, "shop", "prod")
    assert config["db/host"] == "db.internal"
    assert config["db/password"] == "s3cr3t!", "SecureStrings must be decrypted"
    assert len([k for k in config if k.startswith("flags/")]) == 12, "follow pagination (10 parameters per page)"
    assert "localhost" not in config.values(), "only the prod environment"
