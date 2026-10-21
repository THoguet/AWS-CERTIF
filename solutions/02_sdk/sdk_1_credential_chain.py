"""
Exercise sdk_1 — The default credential provider chain
======================================================
Book: chapter 3, "Where do credentials come from?" (book/src/ch03-cli-sdk-sts.md)
Exam: Domain 2 · Task 2.1 (configuring programmatic access to AWS, secure credential handling)

When you create a client without credentials, the SDK walks a chain of
providers and uses the FIRST one that returns credentials. A simplified
version of the chain used by boto3 / the AWS CLI:

  1. "explicit"                credentials passed in code (avoid in real apps!)
  2. "env"                     AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY (+ AWS_SESSION_TOKEN)
  3. "shared-credentials-file" ~/.aws/credentials, profile = $AWS_PROFILE or "default"
  4. "config-file"             ~/.aws/config, same profile
  5. "container-role"          ECS/EKS task role (AWS_CONTAINER_CREDENTIALS_RELATIVE_URI)
  6. "instance-profile"        EC2 instance profile via the instance metadata service (IMDS)

Exam favourites: an environment variable with stale keys "wins" over the
instance profile, and on EC2/ECS/Lambda you should rely on roles (5 and 6),
never on access keys baked into code or images.

Your task
---------
Implement `resolve(...)` returning a tuple `(source_name, credentials_dict)`.
Raise `LookupError` when no source has credentials.
"""


def resolve(
    explicit: dict | None = None,
    env: dict | None = None,
    credentials_file: dict | None = None,
    config_file: dict | None = None,
    container_credentials: dict | None = None,
    instance_metadata: dict | None = None,
) -> tuple[str, dict]:
    """
    explicit:              {"key": ..., "secret": ...} or None
    env:                   a dict of environment variables (may be empty)
    credentials_file:      {profile_name: {"key": ..., "secret": ...}}
    config_file:           {profile_name: {"key": ..., "secret": ...}}
    container_credentials: {"key": ..., "secret": ..., "token": ...} or None
    instance_metadata:     {"key": ..., "secret": ..., "token": ...} or None
    """
    env = env or {}
    credentials_file = credentials_file or {}
    config_file = config_file or {}
    if explicit:
        return "explicit", explicit
    if env.get("AWS_ACCESS_KEY_ID") and env.get("AWS_SECRET_ACCESS_KEY"):
        creds = {"key": env["AWS_ACCESS_KEY_ID"], "secret": env["AWS_SECRET_ACCESS_KEY"]}
        if env.get("AWS_SESSION_TOKEN"):
            creds["token"] = env["AWS_SESSION_TOKEN"]
        return "env", creds
    profile = env.get("AWS_PROFILE") or "default"
    if profile in credentials_file:
        return "shared-credentials-file", credentials_file[profile]
    if profile in config_file:
        return "config-file", config_file[profile]
    if container_credentials:
        return "container-role", container_credentials
    if instance_metadata:
        return "instance-profile", instance_metadata
    raise LookupError("Unable to locate credentials")


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run sdk_1
# =============================================================================
import pytest  # noqa: E402

FILE = {"default": {"key": "AKIADEFAULT", "secret": "s1"}, "prod": {"key": "AKIAPROD", "secret": "s2"}}
IMDS = {"key": "ASIAINSTANCE", "secret": "s3", "token": "t3"}


def test_explicit_wins():
    assert resolve(explicit={"key": "AKIAX", "secret": "x"}, env={"AWS_ACCESS_KEY_ID": "A", "AWS_SECRET_ACCESS_KEY": "B"})[0] == "explicit"


def test_environment_beats_files_and_instance_profile():
    source, creds = resolve(
        env={"AWS_ACCESS_KEY_ID": "AKIAENV", "AWS_SECRET_ACCESS_KEY": "envsecret", "AWS_SESSION_TOKEN": "tok"},
        credentials_file=FILE,
        instance_metadata=IMDS,
    )
    assert source == "env"
    assert creds == {"key": "AKIAENV", "secret": "envsecret", "token": "tok"}


def test_incomplete_environment_is_ignored():
    assert resolve(env={"AWS_ACCESS_KEY_ID": "AKIAENV"}, credentials_file=FILE)[0] == "shared-credentials-file"


def test_profile_selection():
    assert resolve(credentials_file=FILE)[1]["key"] == "AKIADEFAULT"
    assert resolve(env={"AWS_PROFILE": "prod"}, credentials_file=FILE)[1]["key"] == "AKIAPROD"


def test_config_file_after_credentials_file():
    config = {"default": {"key": "AKIACONFIG", "secret": "c"}}
    assert resolve(credentials_file={}, config_file=config)[0] == "config-file"
    assert resolve(credentials_file=FILE, config_file=config)[0] == "shared-credentials-file"


def test_container_before_instance_profile():
    container = {"key": "ASIATASK", "secret": "s", "token": "t"}
    assert resolve(container_credentials=container, instance_metadata=IMDS)[0] == "container-role"
    assert resolve(instance_metadata=IMDS) == ("instance-profile", IMDS)


def test_no_credentials():
    with pytest.raises(LookupError):
        resolve(env={"AWS_PROFILE": "missing"}, credentials_file=FILE)
