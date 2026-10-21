"""
Exercise sdk_2 — Pagination
===========================
Book: chapter 3, "Pagination and waiters" (book/src/ch03-cli-sdk-sts.md)
Exam: Domain 1 · Task 1.1 (write code that interacts with AWS services by using APIs and SDKs)

Most "List*" and "Describe*" APIs return results in pages. S3
ListObjectsV2 returns at most 1,000 keys per call plus a continuation
token. Code that makes a single call silently misses data, which is a
common bug and a common exam distractor.

SDK *paginators* hide the token loop for you. The CLI paginates
automatically, and `--max-items` / `--page-size` control it.

Your task
---------
  * `list_all_keys(s3, bucket, prefix)`: return ALL keys under the prefix,
  * `count_pages(s3, bucket, page_size)`: return how many pages the
    paginator fetches when pages hold `page_size` keys.
"""

# I AM NOT DONE


def list_all_keys(s3, bucket: str, prefix: str = "") -> list[str]:
    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)  # TODO: only the first page!
    return [obj["Key"] for obj in response.get("Contents", [])]


def count_pages(s3, bucket: str, page_size: int) -> int:
    # TODO: use a paginator with PaginationConfig
    raise NotImplementedError


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run sdk_2
# =============================================================================
import boto3  # noqa: E402
import pytest  # noqa: E402


@pytest.fixture
def s3(aws, region):
    client = boto3.client("s3")
    client.create_bucket(Bucket="data-lake", CreateBucketConfiguration={"LocationConstraint": region})
    for i in range(1050):
        client.put_object(Bucket="data-lake", Key=f"raw/{i:05d}.json", Body=b"{}")
    for i in range(5):
        client.put_object(Bucket="data-lake", Key=f"curated/{i}.parquet", Body=b"x")
    return client


def test_lists_more_than_one_page(s3):
    keys = list_all_keys(s3, "data-lake", "raw/")
    assert len(keys) == 1050, "a single ListObjectsV2 call returns at most 1,000 keys"
    assert keys[0] == "raw/00000.json" and keys[-1] == "raw/01049.json"


def test_prefix_filter(s3):
    assert len(list_all_keys(s3, "data-lake", "curated/")) == 5
    assert list_all_keys(s3, "data-lake", "nothing/") == []


def test_page_size(s3):
    assert count_pages(s3, "data-lake", 100) == 11  # 1,055 keys / 100 per page
    assert count_pages(s3, "data-lake", 1000) == 2
