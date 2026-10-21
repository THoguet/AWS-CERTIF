"""
Exercise res_1 — Circuit breaker for a third-party API
======================================================
Book: chapter 11, "Resilience patterns" (book/src/ch11-application-patterns.md)
Exam: Domain 1 · Task 1.1 (resilient code for third-party integrations: retries, circuit breakers)

Retries help with TRANSIENT failures. When a dependency is DOWN, retries
only add load and make every request slow (each one waits for timeouts).
A circuit breaker fails fast instead:

  CLOSED ──(failure_threshold consecutive failures)──► OPEN
  OPEN   ──(reset_timeout elapsed)──► HALF_OPEN (let ONE trial call through)
  HALF_OPEN ──success──► CLOSED     HALF_OPEN ──failure──► OPEN (timer restarts)

While OPEN, calls raise CircuitOpenError immediately, so the caller can
use a fallback (cached data, a default answer, a queue for later).

Your task
---------
Implement CircuitBreaker.call(fn, *args, **kwargs) and the `state` property.
"""

# I AM NOT DONE

import time


class CircuitOpenError(Exception):
    pass


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, reset_timeout: float = 30.0, clock=time.monotonic):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.clock = clock
        self._state = "closed"
        self._failures = 0
        self._opened_at = 0.0

    @property
    def state(self) -> str:
        return self._state

    def call(self, fn, *args, **kwargs):
        return fn(*args, **kwargs)  # TODO


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run res_1
# =============================================================================
import pytest  # noqa: E402


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class Dependency:
    def __init__(self):
        self.healthy, self.calls = True, 0

    def __call__(self):
        self.calls += 1
        if not self.healthy:
            raise TimeoutError("payment provider timeout")
        return "ok"


def _breaker():
    clock = Clock()
    return CircuitBreaker(failure_threshold=3, reset_timeout=30, clock=clock), clock


def test_stays_closed_on_success():
    breaker, _ = _breaker()
    assert breaker.call(Dependency()) == "ok"
    assert breaker.state == "closed"


def test_opens_after_threshold_and_fails_fast():
    breaker, _ = _breaker()
    dep = Dependency()
    dep.healthy = False
    for _ in range(3):
        with pytest.raises(TimeoutError):
            breaker.call(dep)
    assert breaker.state == "open"
    with pytest.raises(CircuitOpenError):
        breaker.call(dep)
    assert dep.calls == 3, "an open circuit must not call the dependency"


def test_success_resets_failure_count():
    breaker, _ = _breaker()
    dep = Dependency()
    for healthy in (False, False, True, False, False):
        dep.healthy = healthy
        try:
            breaker.call(dep)
        except TimeoutError:
            pass
    assert breaker.state == "closed", "failures must be consecutive"


def test_half_open_trial_then_close():
    breaker, clock = _breaker()
    dep = Dependency()
    dep.healthy = False
    for _ in range(3):
        with pytest.raises(TimeoutError):
            breaker.call(dep)
    clock.now = 31
    dep.healthy = True
    assert breaker.call(dep) == "ok"
    assert breaker.state == "closed"


def test_half_open_failure_reopens():
    breaker, clock = _breaker()
    dep = Dependency()
    dep.healthy = False
    for _ in range(3):
        with pytest.raises(TimeoutError):
            breaker.call(dep)
    clock.now = 31
    with pytest.raises(TimeoutError):
        breaker.call(dep)
    assert breaker.state == "open"
    clock.now = 45
    with pytest.raises(CircuitOpenError):
        breaker.call(dep)
