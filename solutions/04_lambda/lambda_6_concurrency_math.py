"""
Exercise lambda_6 — Concurrency math
====================================
Book: chapter 5, "Concurrency and scaling" (book/src/ch05-lambda.md)
Exam: Domain 1 · Task 1.2 (scalability), Domain 4 · Task 4.3 (concurrency)

Numbers to know:
  * concurrency needed ≈ requests per second × average duration (s),
  * default account limit: 1,000 concurrent executions per Region (soft limit),
  * reserved concurrency guarantees AND caps a function's concurrency.
    Lambda always keeps 100 units unreserved for the other functions,
  * throttled synchronous invocations get HTTP 429 (TooManyRequestsException),
  * for an SQS event source, set the queue visibility timeout to at least
    6 × the function timeout.

Your task
---------
  * `required_concurrency(rps, avg_duration_s)`,
  * `max_requests_per_second(concurrency, avg_duration_s)`,
  * `unreserved_pool(account_limit, reservations)`: what remains for the
    functions without reservation. Raise ValueError if fewer than 100 units remain,
  * `sqs_visibility_timeout(function_timeout_s)`.
"""

import math

ACCOUNT_LIMIT = 1000
MIN_UNRESERVED = 100


def required_concurrency(rps: float, avg_duration_s: float) -> int:
    return math.ceil(rps * avg_duration_s)


def max_requests_per_second(concurrency: int, avg_duration_s: float) -> float:
    return concurrency / avg_duration_s


def unreserved_pool(account_limit: int, reservations: dict[str, int]) -> int:
    remaining = account_limit - sum(reservations.values())
    if remaining < MIN_UNRESERVED:
        raise ValueError(f"at least {MIN_UNRESERVED} units must stay unreserved, only {remaining} left")
    return remaining


def sqs_visibility_timeout(function_timeout_s: int) -> int:
    return 6 * function_timeout_s


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run lambda_6
# =============================================================================
import pytest  # noqa: E402


def test_required_concurrency():
    assert required_concurrency(100, 0.5) == 50
    assert required_concurrency(250, 2) == 500
    assert required_concurrency(30, 0.25) == 8  # 7.5 rounded up


def test_max_rps():
    assert max_requests_per_second(1000, 0.2) == pytest.approx(5000)
    assert max_requests_per_second(50, 2) == pytest.approx(25)


def test_unreserved_pool():
    assert unreserved_pool(ACCOUNT_LIMIT, {"checkout": 300, "search": 200}) == 500
    with pytest.raises(ValueError):
        unreserved_pool(ACCOUNT_LIMIT, {"checkout": 600, "search": 350})


def test_visibility_timeout():
    assert sqs_visibility_timeout(30) == 180
    assert sqs_visibility_timeout(900) == 5400
