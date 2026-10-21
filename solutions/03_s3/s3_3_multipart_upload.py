"""
Exercise s3_3 — Multipart upload
================================
Book: chapter 4, "Uploading large objects" (book/src/ch04-s3.md)
Exam: Domain 1 · Task 1.3, Domain 4 · Task 4.3 (optimize applications)

Multipart upload splits an object into parts uploaded independently (in
parallel, retried individually):
  * recommended above ~100 MB, REQUIRED above 5 GB (the single PUT limit),
  * parts are 5 MiB to 5 GiB (the last part can be smaller), max 10,000 parts,
  * maximum object size: 5 TiB,
  * parts of uploads you never complete or abort stay stored AND billed.
    A lifecycle rule "AbortIncompleteMultipartUpload" cleans them up.

boto3's managed transfer (`upload_file` + `TransferConfig`) does all of
this automatically. Here you use the low-level API to understand it.

Your task
---------
  * `multipart_upload(s3, bucket, key, data, part_size)`: upload `data`
    in parts of `part_size` bytes, return the number of parts. If any
    step fails, abort the upload and re-raise the error,
  * `transfer_config()`: a TransferConfig that switches to multipart at
    100 MiB, uses 16 MiB chunks and 10 threads.
"""

from boto3.s3.transfer import TransferConfig

MiB = 1024 * 1024


def multipart_upload(s3, bucket: str, key: str, data: bytes, part_size: int = 5 * MiB) -> int:
    upload_id = s3.create_multipart_upload(Bucket=bucket, Key=key)["UploadId"]
    try:
        parts = []
        for number, start in enumerate(range(0, len(data), part_size), start=1):
            chunk = data[start : start + part_size]
            etag = s3.upload_part(Bucket=bucket, Key=key, UploadId=upload_id, PartNumber=number, Body=chunk)["ETag"]
            parts.append({"PartNumber": number, "ETag": etag})
        s3.complete_multipart_upload(Bucket=bucket, Key=key, UploadId=upload_id, MultipartUpload={"Parts": parts})
        return len(parts)
    except Exception:
        s3.abort_multipart_upload(Bucket=bucket, Key=key, UploadId=upload_id)
        raise


def transfer_config() -> TransferConfig:
    return TransferConfig(multipart_threshold=100 * MiB, multipart_chunksize=16 * MiB, max_concurrency=10)


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run s3_3
# =============================================================================
import boto3  # noqa: E402
import pytest  # noqa: E402
from unittest import mock  # noqa: E402


@pytest.fixture
def s3(aws, region):
    client = boto3.client("s3")
    client.create_bucket(Bucket="video-uploads", CreateBucketConfiguration={"LocationConstraint": region})
    return client


def test_uploads_in_parts(s3):
    data = bytes(range(256)) * (12 * MiB // 256)  # 12 MiB
    assert multipart_upload(s3, "video-uploads", "raw/clip.mp4", data) == 3
    assert s3.get_object(Bucket="video-uploads", Key="raw/clip.mp4")["Body"].read() == data


def test_aborts_on_failure(s3):
    data = b"x" * (11 * MiB)
    real_upload_part = s3.upload_part
    calls = {"n": 0}

    def flaky_upload_part(**kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise ConnectionError("network down")
        return real_upload_part(**kwargs)

    with mock.patch.object(s3, "upload_part", side_effect=flaky_upload_part):
        with pytest.raises(ConnectionError):
            multipart_upload(s3, "video-uploads", "raw/broken.mp4", data)
    assert s3.list_multipart_uploads(Bucket="video-uploads").get("Uploads", []) == [], "abort the failed upload"


def test_transfer_config():
    config = transfer_config()
    assert config.multipart_threshold == 100 * MiB
    assert config.multipart_chunksize == 16 * MiB
    assert config.max_request_concurrency == 10
