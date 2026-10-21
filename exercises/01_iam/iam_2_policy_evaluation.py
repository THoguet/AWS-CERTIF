"""
Exercise iam_2 — Policy evaluation logic
========================================
Book: chapter 2, "How AWS evaluates policies" (book/src/ch02-iam.md)
Exam: Domain 2 · Task 2.1 (IAM, defining permissions for principals)

Within one account, AWS evaluates a request against every applicable policy:
  1. Everything starts as denied (implicit deny).
  2. An explicit Allow in any policy overrides the implicit deny.
  3. An explicit Deny in any policy overrides every Allow.

Actions and resources may contain wildcards: `*` (any sequence of
characters) and `?` (exactly one character). Action names are
case-insensitive (`s3:GetObject` == `S3:getobject`); resource ARNs are
case-sensitive.

Your task
---------
Implement:
  * `matches(pattern, value, case_sensitive)`: wildcard matching,
  * `evaluate(policies, action, resource)`: return one of
      "allowed", "explicitDeny", "implicitDeny"
    (the same decisions the IAM policy simulator reports).

`policies` is a list of identity-based policy documents. A policy's
"Statement" may be a single dict or a list, and "Action"/"Resource" may be
a string or a list. Conditions and NotAction are out of scope here.
"""

# I AM NOT DONE

import re


def matches(pattern: str, value: str, case_sensitive: bool = True) -> bool:
    # TODO: support the * and ? wildcards (hint: build a regular expression)
    raise NotImplementedError


def _as_list(value):
    return value if isinstance(value, list) else [value]


def evaluate(policies: list[dict], action: str, resource: str) -> str:
    # TODO: implicit deny by default, explicit Allow overrides it, explicit Deny always wins
    raise NotImplementedError


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run iam_2
# =============================================================================

READ_REPORTS = {
    "Version": "2012-10-17",
    "Statement": [
        {"Effect": "Allow", "Action": "s3:Get*", "Resource": "arn:aws:s3:::reports/*"},
        {"Effect": "Allow", "Action": ["s3:ListBucket"], "Resource": ["arn:aws:s3:::reports"]},
    ],
}
DENY_SECRET = {
    "Version": "2012-10-17",
    "Statement": {"Effect": "Deny", "Action": "s3:*", "Resource": "arn:aws:s3:::reports/secret/*"},
}


def test_wildcards():
    assert matches("s3:Get*", "s3:GetObject")
    assert not matches("s3:Get*", "s3:PutObject")
    assert matches("arn:aws:s3:::logs-202?", "arn:aws:s3:::logs-2026")
    assert not matches("arn:aws:s3:::logs-202?", "arn:aws:s3:::logs-20266")
    assert matches("arn:aws:s3:::a.b", "arn:aws:s3:::a.b")
    assert not matches("arn:aws:s3:::a.b", "arn:aws:s3:::aXb"), "a dot is not a wildcard"


def test_case_sensitivity():
    assert matches("s3:getobject", "S3:GetObject", case_sensitive=False)
    assert not matches("arn:aws:s3:::Reports/*", "arn:aws:s3:::reports/a.csv")


def test_implicit_deny_without_policies():
    assert evaluate([], "s3:GetObject", "arn:aws:s3:::reports/a.csv") == "implicitDeny"


def test_explicit_allow():
    assert evaluate([READ_REPORTS], "s3:GetObject", "arn:aws:s3:::reports/2026/q3.csv") == "allowed"
    assert evaluate([READ_REPORTS], "s3:ListBucket", "arn:aws:s3:::reports") == "allowed"


def test_not_covered_is_implicitly_denied():
    assert evaluate([READ_REPORTS], "s3:PutObject", "arn:aws:s3:::reports/a.csv") == "implicitDeny"
    # Object ARNs and bucket ARNs are different resources:
    assert evaluate([READ_REPORTS], "s3:GetObject", "arn:aws:s3:::reports") == "implicitDeny"


def test_explicit_deny_wins_over_allow_in_another_policy():
    assert evaluate([READ_REPORTS, DENY_SECRET], "s3:GetObject", "arn:aws:s3:::reports/secret/pay.csv") == "explicitDeny"
    assert evaluate([DENY_SECRET, READ_REPORTS], "s3:GetObject", "arn:aws:s3:::reports/secret/pay.csv") == "explicitDeny"
    assert evaluate([READ_REPORTS, DENY_SECRET], "s3:GetObject", "arn:aws:s3:::reports/public.csv") == "allowed"


def test_action_names_are_case_insensitive():
    assert evaluate([READ_REPORTS], "S3:getobject", "arn:aws:s3:::reports/a.csv") == "allowed"
