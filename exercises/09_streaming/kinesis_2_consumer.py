"""
Exercise kinesis_2 — Reading a stream
=====================================
Book: chapter 10, "Kinesis Data Streams" (book/src/ch10-streaming-orchestration.md)
Exam: Domain 1 · Task 1.1 (handling data streaming)

Low-level consumers read shard by shard with SHARD ITERATORS:
  * TRIM_HORIZON          — from the oldest record still retained (24 h by
                            default, up to 365 days),
  * LATEST                — only records written after the iterator was created,
  * AT_SEQUENCE_NUMBER /
    AFTER_SEQUENCE_NUMBER — resume from a checkpoint,
  * AT_TIMESTAMP          — from a point in time.
Each GetRecords call returns records plus NextShardIterator. In production
you would use the KCL (which checkpoints in a DynamoDB table and balances
shards across workers) or a Lambda event source mapping instead.

Your task
---------
  * `iterator_type(requirement)`: map "replay-all", "new-only",
    "resume-after-checkpoint" and "since-timestamp" to the right type,
  * `read_all(kinesis, stream)`: every record of every shard, decoded from JSON.
"""

# I AM NOT DONE

import json


def iterator_type(requirement: str) -> str:
    raise NotImplementedError  # TODO


def read_all(kinesis, stream: str) -> list[dict]:
    # TODO
    raise NotImplementedError


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run kinesis_2
# =============================================================================
import boto3  # noqa: E402


def test_iterator_types():
    assert iterator_type("replay-all") == "TRIM_HORIZON"
    assert iterator_type("new-only") == "LATEST"
    assert iterator_type("resume-after-checkpoint") == "AFTER_SEQUENCE_NUMBER"
    assert iterator_type("since-timestamp") == "AT_TIMESTAMP"


def test_reads_every_shard(aws):
    kinesis = boto3.client("kinesis")
    kinesis.create_stream(StreamName="clicks", ShardCount=3)
    for i in range(30):
        kinesis.put_record(StreamName="clicks", Data=json.dumps({"n": i}).encode(), PartitionKey=f"user-{i}")
    records = read_all(kinesis, "clicks")
    assert sorted(r["n"] for r in records) == list(range(30))
