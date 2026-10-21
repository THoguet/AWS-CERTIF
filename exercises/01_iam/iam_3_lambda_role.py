"""
Exercise iam_3 — An execution role for Lambda
=============================================
Book: chapter 2, "Roles: trust policy vs permissions policy" (book/src/ch02-iam.md)
Exam: Domain 2 · Task 2.1 (assuming an IAM role, defining permissions for principals)

A role has two independent policies, and mixing them up is a classic exam trap:
  * the TRUST policy (AssumeRolePolicyDocument) says WHO can assume the role,
  * PERMISSIONS policies say WHAT the role can do once assumed.

Your task
---------
Implement `create_lambda_execution_role(iam, role_name, table_arn, logs_policy_arn)`:
  1. create the role with a trust policy that lets the Lambda service
     (lambda.amazonaws.com) call sts:AssumeRole,
  2. attach the managed policy `logs_policy_arn` (it lets the function
     write its logs to CloudWatch Logs),
  3. add an inline policy named "dynamodb-write" that allows only
     dynamodb:PutItem on `table_arn`,
  4. return the role ARN.
"""

# I AM NOT DONE

import json


def create_lambda_execution_role(iam, role_name: str, table_arn: str, logs_policy_arn: str) -> str:
    # TODO 1: trust policy for the Lambda service + create_role
    # TODO 2: attach the logs managed policy
    # TODO 3: inline policy "dynamodb-write" (dynamodb:PutItem on table_arn only)
    # TODO 4: return the role ARN
    raise NotImplementedError


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run iam_3
# =============================================================================
import boto3  # noqa: E402
import pytest  # noqa: E402

TABLE = "arn:aws:dynamodb:eu-west-3:123456789012:table/Orders"


@pytest.fixture
def setup(aws):
    iam = boto3.client("iam")
    logs_policy = iam.create_policy(
        PolicyName="LambdaBasicLogs",
        PolicyDocument=json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
                        "Resource": "*",
                    }
                ],
            }
        ),
    )["Policy"]["Arn"]
    arn = create_lambda_execution_role(iam, "orders-writer", TABLE, logs_policy)
    return iam, arn, logs_policy


def _as_list(value):
    return value if isinstance(value, list) else [value]


def test_returns_role_arn(setup):
    _, arn, _ = setup
    assert arn == "arn:aws:iam::123456789012:role/orders-writer"


def test_trust_policy_allows_lambda_service(setup):
    iam, _, _ = setup
    trust = iam.get_role(RoleName="orders-writer")["Role"]["AssumeRolePolicyDocument"]
    if isinstance(trust, str):
        trust = json.loads(trust)
    statements = _as_list(trust["Statement"])
    assert any(
        s["Effect"] == "Allow"
        and "lambda.amazonaws.com" in _as_list(s["Principal"].get("Service", []))
        and "sts:AssumeRole" in _as_list(s["Action"])
        for s in statements
    ), "the Lambda service must be allowed to assume the role"


def test_logs_policy_attached(setup):
    iam, _, logs_policy = setup
    attached = [p["PolicyArn"] for p in iam.list_attached_role_policies(RoleName="orders-writer")["AttachedPolicies"]]
    assert attached == [logs_policy]


def test_inline_write_policy_is_least_privilege(setup):
    iam, _, _ = setup
    assert iam.list_role_policies(RoleName="orders-writer")["PolicyNames"] == ["dynamodb-write"]
    doc = iam.get_role_policy(RoleName="orders-writer", PolicyName="dynamodb-write")["PolicyDocument"]
    if isinstance(doc, str):
        doc = json.loads(doc)
    statements = _as_list(doc["Statement"])
    assert len(statements) == 1
    assert _as_list(statements[0]["Action"]) == ["dynamodb:PutItem"]
    assert _as_list(statements[0]["Resource"]) == [TABLE]
