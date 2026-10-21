"""
Exercise s3_1 — Buckets, objects and metadata
=============================================
Book: chapter 4, "Buckets and objects" (book/src/ch04-s3.md)
Exam: Domain 1 · Task 1.3 (use, manage and maintain data stores)

Three everyday S3 operations, each with a trap:
  1. CreateBucket: in any region except us-east-1 you must pass a
     LocationConstraint (otherwise: IllegalLocationConstraintException).
     In us-east-1 you must NOT pass one.
  2. PutObject: Content-Type and user-defined metadata are set at upload
     time. Metadata cannot be changed in place later. You need a copy.
  3. HeadObject: read metadata without downloading the object.

Your task
---------
  * `create_bucket(s3, name, region)`: works in every region,
  * `upload_report(s3, bucket, key, body)`: Content-Type application/pdf,
    user metadata owner=finance, returns the ETag,
  * `describe(s3, bucket, key)`: return {"content_type", "size", "owner"}
    WITHOUT downloading the object.
"""

# I AM NOT DONE


def create_bucket(s3, name: str, region: str) -> None:
    s3.create_bucket(Bucket=name)  # TODO: fails outside us-east-1


def upload_report(s3, bucket: str, key: str, body: bytes) -> str:
    # TODO: put_object with a Content-Type and user metadata, return the ETag
    raise NotImplementedError


def describe(s3, bucket: str, key: str) -> dict:
    obj = s3.get_object(Bucket=bucket, Key=key)  # TODO: this downloads the whole object!
    raise NotImplementedError


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run s3_1
# =============================================================================
from unittest import mock  # noqa: E402

import boto3  # noqa: E402


def test_create_bucket_in_paris_and_virginia(aws):
    paris = boto3.client("s3", region_name="eu-west-3")
    create_bucket(paris, "reports-paris-123", "eu-west-3")
    assert paris.get_bucket_location(Bucket="reports-paris-123")["LocationConstraint"] == "eu-west-3"
    virginia = boto3.client("s3", region_name="us-east-1")
    create_bucket(virginia, "reports-virginia-123", "us-east-1")
    assert virginia.get_bucket_location(Bucket="reports-virginia-123")["LocationConstraint"] in (None, "us-east-1")


def test_upload_sets_content_type_and_metadata(aws):
    s3 = boto3.client("s3")
    create_bucket(s3, "reports-paris-123", "eu-west-3")
    etag = upload_report(s3, "reports-paris-123", "2026/q3.pdf", b"%PDF-1.7 fake")
    assert etag.strip('"')
    head = s3.head_object(Bucket="reports-paris-123", Key="2026/q3.pdf")
    assert head["ContentType"] == "application/pdf"
    assert head["Metadata"] == {"owner": "finance"}


def test_describe_uses_head_object(aws):
    s3 = boto3.client("s3")
    create_bucket(s3, "reports-paris-123", "eu-west-3")
    upload_report(s3, "reports-paris-123", "2026/q3.pdf", b"%PDF-1.7 fake")
    with mock.patch.object(s3, "get_object", side_effect=AssertionError("do not download the object")):
        info = describe(s3, "reports-paris-123", "2026/q3.pdf")
    assert info == {"content_type": "application/pdf", "size": 13, "owner": "finance"}
