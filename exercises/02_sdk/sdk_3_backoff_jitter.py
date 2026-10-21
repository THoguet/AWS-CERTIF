"""
Exercise sdk_3 — Retries with exponential backoff and jitter
============================================================
Book: chapter 3, "Retries, backoff and jitter" and chapter 11, "Resilience patterns"
Exam: Domain 1 · Task 1.1 (fault-tolerant design patterns: retries with exponential backoff and jitter)

Throttling errors (ThrottlingException, ProvisionedThroughputExceededException,
TooManyRequestsException...) and 5xx errors are *transient*: retrying
usually works. Retrying immediately makes the overload worse, and
synchronised clients retrying at the same moment ("thundering herd") too.
The fix is exponential backoff (wait longer after each failure) plus
jitter (randomise the wait).

AWS SDKs already do this for you (retry modes "legacy", "standard",
"adaptive"). You will configure them in sdk_5. Here you build the
algorithm yourself, as you would around a third-party API.

Your task
---------
  * `backoff_delay(attempt, base, cap, rand)`: "full jitter" delay,
    i.e. a random value between 0 and min(cap, base * 2**attempt),
  * `call_with_retries(fn, max_attempts, sleep, rand)`: call `fn()`,
    retrying only retryable errors, sleeping `backoff_delay(n)` before
    retry n (n = 0, 1, 2...), and giving up after `max_attempts` calls.
"""

# I AM NOT DONE

import random
import time

from botocore.exceptions import ClientError

RETRYABLE_CODES = {
    "Throttling",
    "ThrottlingException",
    "TooManyRequestsException",
    "ProvisionedThroughputExceededException",
    "RequestLimitExceeded",
    "SlowDown",
    "InternalError",
    "ServiceUnavailable",
}


def backoff_delay(attempt: int, base: float = 0.1, cap: float = 5.0, rand=random.random) -> float:
    # TODO: exponential growth, capped, with full jitter
    raise NotImplementedError


def call_with_retries(fn, max_attempts: int = 5, sleep=time.sleep, rand=random.random):
    # TODO: retry fn() on retryable errors only
    return fn()


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run sdk_3
# =============================================================================
import pytest  # noqa: E402


def _error(code):
    return ClientError({"Error": {"Code": code, "Message": code}}, "SomeOperation")


class Flaky:
    def __init__(self, failures, code="ThrottlingException"):
        self.failures, self.code, self.calls = failures, code, 0

    def __call__(self):
        self.calls += 1
        if self.calls <= self.failures:
            raise _error(self.code)
        return "ok"


def test_delay_grows_exponentially_and_is_capped():
    full = lambda: 1.0  # noqa: E731  (always take the maximum)
    assert [backoff_delay(n, base=0.1, cap=5.0, rand=full) for n in range(8)] == pytest.approx(
        [0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 5.0, 5.0]
    )


def test_delay_has_jitter():
    assert backoff_delay(3, base=0.1, cap=5.0, rand=lambda: 0.5) == pytest.approx(0.4)
    assert backoff_delay(3, base=0.1, cap=5.0, rand=lambda: 0.0) == 0.0


def test_retries_then_succeeds():
    sleeps = []
    fn = Flaky(failures=2)
    assert call_with_retries(fn, max_attempts=5, sleep=sleeps.append, rand=lambda: 1.0) == "ok"
    assert fn.calls == 3
    assert sleeps == pytest.approx([0.1, 0.2])


def test_non_retryable_errors_are_raised_immediately():
    sleeps = []
    fn = Flaky(failures=1, code="AccessDeniedException")
    with pytest.raises(ClientError):
        call_with_retries(fn, sleep=sleeps.append, rand=lambda: 1.0)
    assert fn.calls == 1 and sleeps == []


def test_gives_up_after_max_attempts():
    sleeps = []
    fn = Flaky(failures=10, code="ProvisionedThroughputExceededException")
    with pytest.raises(ClientError):
        call_with_retries(fn, max_attempts=4, sleep=sleeps.append, rand=lambda: 1.0)
    assert fn.calls == 4
    assert len(sleeps) == 3
