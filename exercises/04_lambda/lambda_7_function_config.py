"""
Exercise lambda_7 — Configure a function and its async error handling
=====================================================================
Book: chapter 5, "Configuration" and "Asynchronous invocation, DLQs and destinations"
Exam: Domain 1 · Task 1.2 (configuring Lambda: memory, timeout, env vars, destinations, tracing)

The `thumbnailer` function must be deployed with:
  * runtime python3.12, handler app.handler, role `role_arn`,
  * 1024 MB of memory (CPU is allocated proportionally to memory),
  * a 60 s timeout (the maximum is 900 s),
  * environment variables BUCKET=thumbs and LOG_LEVEL=INFO,
  * X-Ray active tracing,
  * 2048 MB of /tmp (ephemeral storage, 512 MB default, up to 10,240 MB),
  * arm64 (Graviton2: usually better price/performance).

It is invoked ASYNCHRONOUSLY by S3. On failure Lambda retries (2 times by
default), then drops the event unless you configure an on-failure
destination (or a DLQ). Requirements: retry at most once, discard events
older than 1 hour, send failures to the SQS queue `failure_queue_arn`.

Your task
---------
Implement `deploy(lambda_client, role_arn, zip_bytes, failure_queue_arn)`
and return the function configuration (get_function_configuration).
"""

# I AM NOT DONE


def deploy(lambda_client, role_arn: str, zip_bytes: bytes, failure_queue_arn: str) -> dict:
    lambda_client.create_function(
        FunctionName="thumbnailer",
        Runtime="python3.12",
        Role=role_arn,
        Handler="app.handler",
        Code={"ZipFile": zip_bytes},
        # TODO: memory, timeout, environment, tracing, ephemeral storage, architecture
    )
    # TODO: asynchronous invocation config (retries, max event age, on-failure destination)
    return lambda_client.get_function_configuration(FunctionName="thumbnailer")


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run lambda_7
# =============================================================================
import json  # noqa: E402

import boto3  # noqa: E402
import pytest  # noqa: E402

from awslings.testing import lambda_zip  # noqa: E402

FAILURES = "arn:aws:sqs:eu-west-3:123456789012:thumbnailer-failures"


@pytest.fixture
def deployed(aws):
    iam = boto3.client("iam")
    trust = {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}]}
    role = iam.create_role(RoleName="thumbnailer-role", AssumeRolePolicyDocument=json.dumps(trust))["Role"]["Arn"]
    client = boto3.client("lambda")
    return client, deploy(client, role, lambda_zip(), FAILURES)


def test_compute_settings(deployed):
    _, config = deployed
    assert config["MemorySize"] == 1024
    assert config["Timeout"] == 60
    assert config["EphemeralStorage"]["Size"] == 2048
    assert config["Architectures"] == ["arm64"]


def test_environment_and_tracing(deployed):
    _, config = deployed
    assert config["Environment"]["Variables"] == {"BUCKET": "thumbs", "LOG_LEVEL": "INFO"}
    assert config["TracingConfig"]["Mode"] == "Active"


def test_async_error_handling(deployed):
    client, _ = deployed
    invoke_config = client.get_function_event_invoke_config(FunctionName="thumbnailer")
    assert invoke_config["MaximumRetryAttempts"] == 1
    assert invoke_config["MaximumEventAgeInSeconds"] == 3600
    assert invoke_config["DestinationConfig"]["OnFailure"]["Destination"] == FAILURES
