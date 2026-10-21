"""
Exercise iam_4 — Bucket policy with conditions
==============================================
Book: chapter 2, "Resource-based policies" and chapter 4, "Encryption"
Exam: Domain 2 · Tasks 2.1 / 2.2 (resource-based policies, encryption in transit and at rest)

The security team wants three guarantees on the `payroll-exports` bucket:
  1. requests that do not use TLS (HTTPS) are rejected, whatever the caller,
  2. uploads (s3:PutObject) are rejected unless they ask for SSE-KMS,
     i.e. the header `x-amz-server-side-encryption: aws:kms`,
  3. the reporting role (READER_ROLE_ARN) may download objects.

A *resource-based* policy (like a bucket policy) has a "Principal" element,
which identity-based policies never have.

Your task
---------
Complete BUCKET_POLICY (three statements with Sids "DenyInsecureTransport",
"DenyUnencryptedUploads" and "AllowReaderRole"), then `apply_policy()`.
"""

# I AM NOT DONE

import json

BUCKET = "payroll-exports"
BUCKET_ARN = f"arn:aws:s3:::{BUCKET}"
READER_ROLE_ARN = "arn:aws:iam::123456789012:role/reporting"

BUCKET_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "DenyInsecureTransport",
            # TODO: deny every S3 action, for everyone, on the bucket AND its objects, when TLS is not used
        },
        {
            "Sid": "DenyUnencryptedUploads",
            # TODO: deny PutObject unless the SSE header asks for aws:kms
        },
        {
            "Sid": "AllowReaderRole",
            # TODO: allow READER_ROLE_ARN to get objects
        },
    ],
}


def apply_policy(s3) -> None:
    """Attach BUCKET_POLICY to the bucket (the policy must be sent as a JSON string)."""
    # TODO
    raise NotImplementedError


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run iam_4
# =============================================================================
import boto3  # noqa: E402


def _by_sid(sid):
    for statement in BUCKET_POLICY["Statement"]:
        if statement.get("Sid") == sid:
            return statement
    raise AssertionError(f"no statement with Sid {sid}")


def _as_list(value):
    return value if isinstance(value, list) else [value]


def test_deny_insecure_transport():
    s = _by_sid("DenyInsecureTransport")
    assert s["Effect"] == "Deny"
    assert s["Principal"] in ("*", {"AWS": "*"})
    assert _as_list(s["Action"]) == ["s3:*"]
    assert set(_as_list(s["Resource"])) == {BUCKET_ARN, BUCKET_ARN + "/*"}, "cover the bucket AND its objects"
    assert s["Condition"] == {"Bool": {"aws:SecureTransport": "false"}}


def test_deny_unencrypted_uploads():
    s = _by_sid("DenyUnencryptedUploads")
    assert s["Effect"] == "Deny"
    assert _as_list(s["Action"]) == ["s3:PutObject"]
    assert _as_list(s["Resource"]) == [BUCKET_ARN + "/*"]
    assert s["Condition"] == {"StringNotEquals": {"s3:x-amz-server-side-encryption": "aws:kms"}}


def test_allow_reader_role():
    s = _by_sid("AllowReaderRole")
    assert s["Effect"] == "Allow"
    assert s["Principal"] == {"AWS": READER_ROLE_ARN}
    assert _as_list(s["Action"]) == ["s3:GetObject"]
    assert _as_list(s["Resource"]) == [BUCKET_ARN + "/*"]


def test_policy_applies(aws, region):
    s3 = boto3.client("s3")
    s3.create_bucket(Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": region})
    apply_policy(s3)
    stored = json.loads(s3.get_bucket_policy(Bucket=BUCKET)["Policy"])
    assert stored == BUCKET_POLICY
