"""
Exercise opt_1 — Right-size Lambda memory
=========================================
Book: chapter 23, "Optimizing Lambda" (book/src/ch23-optimization.md)
Exam: Domain 4 · Task 4.3 (determining minimum memory and compute power, profiling performance)

Lambda allocates CPU in proportion to memory (1,769 MB = 1 full vCPU,
up to 6 vCPUs at 10,240 MB). For CPU-bound code, doubling memory can
halve duration, so the cost (GB-seconds) stays flat or even DROPS while
latency improves. The "AWS Lambda Power Tuning" tool (a Step Functions
state machine) runs your function at several memory sizes and plots
cost against speed. Compute Optimizer gives similar recommendations.

Prices below are illustrative (x86, first pricing tier).

Your task
---------
  * `cost_per_million(memory_mb, duration_ms)`: dollars per million invocations,
  * `cheapest_memory(measurements, max_latency_ms)`: from {memory_mb: avg_duration_ms},
    the memory size with the lowest cost, among those meeting the latency
    target when one is given.
"""

import math

PRICE_PER_GB_SECOND = 0.0000166667
PRICE_PER_REQUEST = 0.20 / 1_000_000


def cost_per_million(memory_mb: int, duration_ms: float) -> float:
    gb_seconds = (memory_mb / 1024) * (math.ceil(duration_ms) / 1000)
    return 1_000_000 * (gb_seconds * PRICE_PER_GB_SECOND + PRICE_PER_REQUEST)


def cheapest_memory(measurements: dict[int, float], max_latency_ms: float | None = None) -> int:
    candidates = {m: d for m, d in measurements.items() if max_latency_ms is None or d <= max_latency_ms}
    if not candidates:
        raise ValueError("no configuration meets the latency target")
    return min(candidates, key=lambda m: cost_per_million(m, candidates[m]))


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run opt_1
# =============================================================================
import pytest  # noqa: E402

# Measured average duration of a CPU-bound image-resizing function at each memory size.
MEASURED = {128: 2000, 512: 450, 1024: 210, 2048: 205}


def test_cost_formula():
    # 1,024 MB for 1,000 ms = 1 GB-s → $16.67 per million + $0.20 for the requests
    assert cost_per_million(1024, 1000) == pytest.approx(16.8667, rel=1e-3)
    assert cost_per_million(128, 100) == pytest.approx(0.408, rel=1e-2)


def test_duration_is_rounded_up_to_the_millisecond():
    assert cost_per_million(1024, 100.2) == pytest.approx(cost_per_million(1024, 101))


def test_more_memory_can_be_cheaper():
    assert cost_per_million(1024, MEASURED[1024]) < cost_per_million(128, MEASURED[128])
    assert cheapest_memory(MEASURED) == 1024


def test_latency_target():
    assert cheapest_memory({128: 900, 256: 400, 512: 190}, max_latency_ms=200) == 512
    with pytest.raises(ValueError):
        cheapest_memory({128: 900}, max_latency_ms=100)
