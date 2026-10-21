"""
Exercise kinesis_1 — A resilient Kinesis producer
=================================================
Book: chapter 10, "Kinesis Data Streams" (book/src/ch10-streaming-orchestration.md)
Exam: Domain 1 · Task 1.1 (handling data streaming by using AWS services)

Click events go to a Kinesis data stream:
  * the PARTITION KEY decides the shard. Records with the same key go to
    the same shard, IN ORDER. Use the user id to keep each user's clicks ordered,
  * PutRecords sends up to 500 records per call (5 MiB),
  * PutRecords is NOT all-or-nothing: some records can fail
    (ProvisionedThroughputExceededException when a shard is hot, i.e. above
    1 MB/s or 1,000 records/s) while others succeed. The response gives
    FailedRecordCount and a per-record result (same order as the request).

Your task
---------
Implement `put_clicks(kinesis, stream, clicks, sleep, max_attempts)`:
send all clicks (JSON-encoded) in batches of at most 500, partition key =
click["user_id"], and resend ONLY the failed records with exponential
backoff. Return the number of PutRecords calls made.
"""

import json
import time

MAX_BATCH = 500
BASE_DELAY = 0.1


def put_clicks(kinesis, stream: str, clicks: list[dict], sleep=time.sleep, max_attempts: int = 5) -> int:
    records = [{"Data": json.dumps(c).encode(), "PartitionKey": c["user_id"]} for c in clicks]
    calls = 0
    for start in range(0, len(records), MAX_BATCH):
        pending = records[start : start + MAX_BATCH]
        for attempt in range(max_attempts):
            response = kinesis.put_records(StreamName=stream, Records=pending)
            calls += 1
            if response.get("FailedRecordCount", 0) == 0:
                break
            pending = [rec for rec, res in zip(pending, response["Records"]) if "ErrorCode" in res]
            if attempt == max_attempts - 1:
                raise RuntimeError(f"{len(pending)} records could not be written")
            sleep(BASE_DELAY * 2**attempt)
    return calls


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run kinesis_1
# =============================================================================
import boto3  # noqa: E402
import pytest  # noqa: E402


def _clicks(n):
    return [{"user_id": f"u-{i % 7}", "page": f"/p/{i}"} for i in range(n)]


class HotShardClient:
    """Fails every 3rd record on the first call, then accepts everything."""

    def __init__(self):
        self.calls, self.sizes, self.written = 0, [], []

    def put_records(self, StreamName, Records):
        assert len(Records) <= 500
        self.calls += 1
        self.sizes.append(len(Records))
        results = []
        for i, record in enumerate(Records):
            if self.calls == 1 and i % 3 == 0:
                results.append({"ErrorCode": "ProvisionedThroughputExceededException", "ErrorMessage": "slow down"})
            else:
                self.written.append(record)
                results.append({"SequenceNumber": str(len(self.written)), "ShardId": "shardId-000000000000"})
        return {"FailedRecordCount": sum("ErrorCode" in r for r in results), "Records": results}


def test_batches_of_500_with_moto(aws):
    kinesis = boto3.client("kinesis")
    kinesis.create_stream(StreamName="clicks", ShardCount=2)
    assert put_clicks(kinesis, "clicks", _clicks(1200), sleep=lambda s: None) == 3


def test_only_failed_records_are_retried():
    client, sleeps = HotShardClient(), []
    put_clicks(client, "clicks", _clicks(9), sleep=sleeps.append)
    assert client.sizes == [9, 3], "the retry must contain only the 3 failed records"
    assert len(client.written) == 9
    assert sleeps == pytest.approx([0.1])


def test_partition_key_is_user_id():
    client = HotShardClient()
    put_clicks(client, "clicks", [{"user_id": "u-42", "page": "/"}], sleep=lambda s: None)
    put_clicks(client, "clicks", [{"user_id": "u-42", "page": "/cart"}], sleep=lambda s: None)
    assert {r["PartitionKey"] for r in client.written} == {"u-42"}
