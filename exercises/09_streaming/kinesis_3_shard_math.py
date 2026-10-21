"""
Exercise kinesis_3 — Shard capacity math
========================================
Book: chapter 10, "Shards and capacity" (book/src/ch10-streaming-orchestration.md)
Exam: Domain 1 · Task 1.1, Domain 4 · Task 4.3

Provisioned-mode limits PER SHARD:
  * writes: 1 MB/s or 1,000 records/s (whichever is hit first),
  * reads (shared throughput): 2 MB/s shared by ALL consumers
    (and 5 GetRecords calls/s),
  * reads with ENHANCED FAN-OUT: 2 MB/s per shard PER registered consumer,
    pushed over HTTP/2 (SubscribeToShard), with lower latency.
(On-demand mode scales shards for you.)
Here 1 MB = 1,024 KB.

Your task
---------
  * `shards_for_writes(records_per_s, record_kb)`,
  * `shards_for_reads(records_per_s, record_kb, consumers, enhanced_fan_out)`,
  * `shards_needed(...)`: enough shards for both.
"""

# I AM NOT DONE

import math


def shards_for_writes(records_per_s: int, record_kb: float) -> int:
    raise NotImplementedError  # TODO


def shards_for_reads(records_per_s: int, record_kb: float, consumers: int, enhanced_fan_out: bool = False) -> int:
    raise NotImplementedError  # TODO


def shards_needed(records_per_s: int, record_kb: float, consumers: int, enhanced_fan_out: bool = False) -> int:
    raise NotImplementedError  # TODO


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run kinesis_3
# =============================================================================


def test_writes_limited_by_records():
    assert shards_for_writes(5000, 0.1) == 5  # 5,000 records/s of 100 bytes: the 1,000 rec/s limit dominates


def test_writes_limited_by_bandwidth():
    assert shards_for_writes(100, 50) == 5  # 100 × 50 KB = 5,000 KB/s ≈ 4.9 MB/s


def test_shared_reads():
    assert shards_for_reads(1024, 2, consumers=3) == 3  # 2 MB/s produced × 3 consumers = 6 MB/s


def test_enhanced_fan_out():
    assert shards_for_reads(1024, 2, consumers=3, enhanced_fan_out=True) == 1


def test_total():
    assert shards_needed(1024, 2, consumers=5) == 5
    assert shards_needed(1024, 2, consumers=5, enhanced_fan_out=True) == 2
