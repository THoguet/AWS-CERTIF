"""
Exercise lambda_1 — The handler and the context object
======================================================
Book: chapter 5, "Anatomy of a function" (book/src/ch05-lambda.md)
Exam: Domain 1 · Task 1.2 (develop code for Lambda, handling the event lifecycle)

A Python handler is a function `handler(event, context)`:
  * `event`   is the JSON payload (already a dict) sent by the caller or
              by the event source (S3, SQS, API Gateway...),
  * `context` carries runtime information: aws_request_id,
              function_name, memory_limit_in_mb, log_group_name and
              get_remaining_time_in_millis().

Long batch jobs should watch the remaining time and stop cleanly before
the timeout (max 900 s = 15 min) kills them mid-item.

Your task
---------
  * `handler(event, context)`: return
        {"greeting": "Hello, <name>!", "request_id": ..., "function": ...}
    where <name> is event["name"], or "world" when missing or empty,
  * `process_batch(items, context, work, safety_ms)`: call work(item) for
    each item, but stop as soon as less than `safety_ms` milliseconds
    remain. Return the list of items that were NOT processed.
"""


def handler(event, context):
    name = event.get("name") or "world"
    return {"greeting": f"Hello, {name}!", "request_id": context.aws_request_id, "function": context.function_name}


def process_batch(items: list, context, work, safety_ms: int = 10_000) -> list:
    for index, item in enumerate(items):
        if context.get_remaining_time_in_millis() < safety_ms:
            return items[index:]
        work(item)
    return []


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run lambda_1
# =============================================================================
from awslings.testing import FakeContext  # noqa: E402


class CountdownContext(FakeContext):
    """Each call to get_remaining_time_in_millis() consumes 5 seconds."""

    def __init__(self, start_ms):
        super().__init__(remaining_ms=start_ms)

    def get_remaining_time_in_millis(self):
        value = self._remaining_ms
        self._remaining_ms -= 5_000
        return value


def test_greeting_uses_event_and_context():
    ctx = FakeContext(function_name="greeter", request_id="req-123")
    assert handler({"name": "Ada"}, ctx) == {"greeting": "Hello, Ada!", "request_id": "req-123", "function": "greeter"}


def test_default_name():
    ctx = FakeContext()
    assert handler({}, ctx)["greeting"] == "Hello, world!"
    assert handler({"name": ""}, ctx)["greeting"] == "Hello, world!"


def test_processes_everything_when_time_allows():
    done = []
    assert process_batch([1, 2, 3], FakeContext(remaining_ms=60_000), done.append) == []
    assert done == [1, 2, 3]


def test_stops_before_timeout():
    done = []
    left = process_batch(list(range(10)), CountdownContext(start_ms=30_000), done.append, safety_ms=10_000)
    assert done == [0, 1, 2, 3, 4]
    assert left == [5, 6, 7, 8, 9]
