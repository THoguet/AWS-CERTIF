"""
Exercise s3_4 — Server-side encryption with KMS
===============================================
Book: chapter 4, "Encryption" and chapter 13, "KMS"
Exam: Domain 2 · Task 2.2 (encryption at rest, server-side vs client-side encryption)

Since January 2023 every new S3 object is encrypted at rest by default
with SSE-S3 (keys managed by S3). Compliance often requires SSE-KMS
instead: you get a key policy, CloudTrail audit of every key use, and
the ability to disable the key.

With SSE-KMS, every object operation calls KMS, and KMS request quotas
can throttle very busy buckets. *S3 Bucket Keys* reduce KMS calls (and
cost) by up to 99% by generating a bucket-level key from KMS.

Your task
---------
  * `put_encrypted(s3, bucket, key, body, kms_key_id)`: upload ONE object
    with SSE-KMS using the given key,
  * `enforce_default_encryption(s3, bucket, kms_key_id)`: make SSE-KMS
    with that key the bucket default, with S3 Bucket Keys enabled,
  * `encryption_of(s3, bucket, key)`: return (algorithm, kms_key_id or None).
"""

# I AM NOT DONE


def put_encrypted(s3, bucket: str, key: str, body: bytes, kms_key_id: str) -> None:
    s3.put_object(Bucket=bucket, Key=key, Body=body)  # TODO: request SSE-KMS with this key


def enforce_default_encryption(s3, bucket: str, kms_key_id: str) -> None:
    # TODO: put_bucket_encryption
    raise NotImplementedError


def encryption_of(s3, bucket: str, key: str) -> tuple[str, str | None]:
    # TODO: use head_object
    raise NotImplementedError


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run s3_4
# =============================================================================
import boto3  # noqa: E402
import pytest  # noqa: E402


@pytest.fixture
def env(aws, region):
    s3 = boto3.client("s3")
    s3.create_bucket(Bucket="hr-documents", CreateBucketConfiguration={"LocationConstraint": region})
    key_id = boto3.client("kms").create_key(Description="hr documents")["KeyMetadata"]["KeyId"]
    return s3, key_id


def test_single_object_with_sse_kms(env):
    s3, key_id = env
    put_encrypted(s3, "hr-documents", "contracts/alice.pdf", b"contract", key_id)
    algorithm, used_key = encryption_of(s3, "hr-documents", "contracts/alice.pdf")
    assert algorithm == "aws:kms"
    assert key_id in used_key


def test_default_encryption_with_bucket_key(env):
    s3, key_id = env
    enforce_default_encryption(s3, "hr-documents", key_id)
    rule = s3.get_bucket_encryption(Bucket="hr-documents")["ServerSideEncryptionConfiguration"]["Rules"][0]
    assert rule["ApplyServerSideEncryptionByDefault"]["SSEAlgorithm"] == "aws:kms"
    assert rule.get("BucketKeyEnabled") is True
    s3.put_object(Bucket="hr-documents", Key="payslips/2026-10.pdf", Body=b"payslip")
    head = s3.head_object(Bucket="hr-documents", Key="payslips/2026-10.pdf")
    assert head["ServerSideEncryption"] == "aws:kms"
    assert encryption_of(s3, "hr-documents", "payslips/2026-10.pdf")[0] == "aws:kms"
