"""
Exercise ddb_1 — Read and write capacity units
==============================================
Book: chapter 7, "Capacity modes and capacity math" (book/src/ch07-dynamodb.md)
Exam: Domain 1 · Task 1.3 (DynamoDB, consistency models)

These calculations appear in almost every DVA exam:
  * 1 RCU = 1 strongly consistent read per second of an item up to 4 KB
          = 2 eventually consistent reads per second (up to 4 KB each)
          = 0.5 transactional read per second
  * 1 WCU = 1 write per second of an item up to 1 KB
          (transactional writes cost 2 WCU per KB)
  * item sizes are ROUNDED UP: 4 KB blocks for reads, 1 KB blocks for writes.

Example: 10 strongly consistent reads/s of 6 KB items → ceil(6/4) = 2
units per read → 20 RCU. Eventually consistent → 10 RCU.

Your task
---------
  * `rcu(item_kb, reads_per_second, mode)` with mode "strong", "eventual" or "transactional",
  * `wcu(item_kb, writes_per_second, transactional=False)`.
"""

import math


def rcu(item_kb: float, reads_per_second: int, mode: str = "eventual") -> int:
    units = math.ceil(item_kb / 4)
    if mode == "strong":
        return units * reads_per_second
    if mode == "eventual":
        return math.ceil(units * reads_per_second / 2)
    if mode == "transactional":
        return 2 * units * reads_per_second
    raise ValueError(f"unknown mode {mode}")


def wcu(item_kb: float, writes_per_second: int, transactional: bool = False) -> int:
    units = math.ceil(item_kb) * writes_per_second
    return 2 * units if transactional else units


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run ddb_1
# =============================================================================


def test_strongly_consistent_reads():
    assert rcu(6, 10, "strong") == 20
    assert rcu(4, 10, "strong") == 10
    assert rcu(4.1, 10, "strong") == 20


def test_eventually_consistent_reads():
    assert rcu(6, 10, "eventual") == 10
    assert rcu(1, 3, "eventual") == 2  # 1.5 rounded up
    assert rcu(16, 100, "eventual") == 200


def test_transactional_reads():
    assert rcu(6, 10, "transactional") == 40


def test_writes():
    assert wcu(1, 100) == 100
    assert wcu(2.5, 10) == 30
    assert wcu(0.5, 10) == 10
    assert wcu(2.5, 10, transactional=True) == 60
