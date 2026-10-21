"""
Exercise iam_1 — Write a least-privilege identity policy
========================================================
Book: chapter 2, "Policy anatomy" (book/src/ch02-iam.md)
Exam: Domain 2 · Task 2.1 (principle of least privilege, defining permissions for principals)

The `orders-api` Lambda function only needs to *read* single orders and to
*query* the `Orders` table and its indexes (account 123456789012, eu-west-3).
The current draft policy is far too broad.

Your task
---------
Fix ORDERS_READ_POLICY so that it:
  * uses the current policy language version,
  * contains a single Allow statement with Sid "ReadOrders",
  * allows exactly dynamodb:GetItem and dynamodb:Query (nothing else, no wildcards),
  * applies to the table ARN AND to all of its indexes (and nothing else).
"""

# I AM NOT DONE

TABLE_ARN = "arn:aws:dynamodb:eu-west-3:123456789012:table/Orders"

ORDERS_READ_POLICY = {
    "Version": "2008-10-17",  # TODO: is this the right version?
    "Statement": [
        {
            "Sid": "ReadOrders",
            "Effect": "Allow",
            "Action": "dynamodb:*",  # TODO: least privilege!
            "Resource": "*",  # TODO: the table and its indexes only
        }
    ],
}


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run iam_1
# =============================================================================
import json  # noqa: E402

import boto3  # noqa: E402


def _statements():
    statements = ORDERS_READ_POLICY["Statement"]
    return statements if isinstance(statements, list) else [statements]


def _as_list(value):
    return value if isinstance(value, list) else [value]


def test_version():
    assert ORDERS_READ_POLICY["Version"] == "2012-10-17"


def test_single_allow_statement():
    statements = _statements()
    assert len(statements) == 1
    assert statements[0]["Effect"] == "Allow"
    assert statements[0].get("Sid") == "ReadOrders"


def test_only_read_actions():
    actions = set(_as_list(_statements()[0]["Action"]))
    assert actions == {"dynamodb:GetItem", "dynamodb:Query"}, "exactly GetItem and Query, no wildcards"


def test_resources_are_table_and_indexes():
    resources = set(_as_list(_statements()[0]["Resource"]))
    assert resources == {TABLE_ARN, TABLE_ARN + "/index/*"}


def test_policy_is_accepted_by_iam(aws):
    iam = boto3.client("iam")
    iam.create_policy(PolicyName="orders-read", PolicyDocument=json.dumps(ORDERS_READ_POLICY))
