"""
Exercise s3_5 — Versioning and lifecycle management
===================================================
Book: chapter 4, "Storage classes and lifecycle" (book/src/ch04-s3.md)
Exam: Domain 1 · Task 1.3 (S3 tiers and lifecycle management, managing data lifecycles)

The `app-logs` bucket must keep costs low:
  * versioning ON (protects against accidental deletes/overwrites),
  * objects under `logs/`:
      - move to STANDARD_IA after 30 days,
      - move to GLACIER (Flexible Retrieval) after 90 days,
      - expire (delete) after 365 days,
  * old (noncurrent) versions are deleted 30 days after they stop being current,
  * incomplete multipart uploads are aborted after 7 days.

S3 refuses to transition objects from STANDARD to STANDARD_IA or
ONEZONE_IA before they are 30 days old. Your validator catches that
before you call the API.

Your task
---------
  * `validate_transitions(transitions)`: raise ValueError when an IA class
    is used before day 30 or when days do not strictly increase,
  * `configure_logs_bucket(s3, bucket)`: versioning + the lifecycle rule
    (ID "logs-retention").
"""

# I AM NOT DONE

LOG_TRANSITIONS = [
    {"Days": 30, "StorageClass": "STANDARD_IA"},
    {"Days": 90, "StorageClass": "GLACIER"},
]
MIN_DAYS = {"STANDARD_IA": 30, "ONEZONE_IA": 30}


def validate_transitions(transitions: list[dict]) -> None:
    # TODO
    raise NotImplementedError


def configure_logs_bucket(s3, bucket: str) -> None:
    validate_transitions(LOG_TRANSITIONS)
    # TODO 1: enable versioning
    # TODO 2: put_bucket_lifecycle_configuration with the rule "logs-retention"
    raise NotImplementedError


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run s3_5
# =============================================================================
import boto3  # noqa: E402
import pytest  # noqa: E402


def test_validator_rejects_early_ia():
    with pytest.raises(ValueError):
        validate_transitions([{"Days": 10, "StorageClass": "STANDARD_IA"}])
    with pytest.raises(ValueError):
        validate_transitions([{"Days": 29, "StorageClass": "ONEZONE_IA"}])


def test_validator_rejects_unordered_days():
    with pytest.raises(ValueError):
        validate_transitions([{"Days": 90, "StorageClass": "GLACIER"}, {"Days": 60, "StorageClass": "DEEP_ARCHIVE"}])


def test_validator_accepts_valid_rules():
    validate_transitions(LOG_TRANSITIONS)
    validate_transitions([{"Days": 0, "StorageClass": "GLACIER"}])  # Glacier has no 30-day minimum


def test_bucket_configuration(aws, region):
    s3 = boto3.client("s3")
    s3.create_bucket(Bucket="app-logs-123", CreateBucketConfiguration={"LocationConstraint": region})
    configure_logs_bucket(s3, "app-logs-123")
    assert s3.get_bucket_versioning(Bucket="app-logs-123")["Status"] == "Enabled"
    rules = s3.get_bucket_lifecycle_configuration(Bucket="app-logs-123")["Rules"]
    assert len(rules) == 1
    rule = rules[0]
    assert rule["ID"] == "logs-retention" and rule["Status"] == "Enabled"
    assert rule["Filter"] == {"Prefix": "logs/"}
    assert [(t["Days"], t["StorageClass"]) for t in rule["Transitions"]] == [(30, "STANDARD_IA"), (90, "GLACIER")]
    assert rule["Expiration"]["Days"] == 365
    assert rule["NoncurrentVersionExpiration"]["NoncurrentDays"] == 30
    assert rule["AbortIncompleteMultipartUpload"]["DaysAfterInitiation"] == 7
