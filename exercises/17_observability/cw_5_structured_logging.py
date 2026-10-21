"""
Exercise cw_5 — Structured (JSON) logging with correlation ids
==============================================================
Book: chapter 20, "Logging strategy" (book/src/ch20-monitoring-logging.md)
Exam: Domain 4 · Task 4.2 (structured logging, implementing an effective logging strategy)

`print("payment failed for", order)` is hard to query. One JSON object per
line is easy: Logs Insights discovers the fields automatically
(`filter level = "ERROR" and service = "checkout"`), and metric filters
can match JSON fields.

A CORRELATION ID that travels with the request (HTTP header, message
attribute...) lets you follow one transaction across services. Reuse the
caller's id when there is one, otherwise create one (the Lambda request
id is a good default).
(Powertools for AWS Lambda "Logger" does all this. Lambda also supports
JSON log format and log-level filtering natively.)

Your task
---------
Implement JsonLogger (info, error) and `handler(event, context, logger)`.
"""

# I AM NOT DONE

import json
import sys
from datetime import datetime, timezone


class JsonLogger:
    def __init__(self, service: str, stream=sys.stdout, clock=lambda: datetime.now(timezone.utc)):
        self.service, self.stream, self.clock = service, stream, clock
        self.correlation_id = None

    def _log(self, level: str, message: str, **fields) -> None:
        self.stream.write(f"{level} {message} {fields}\n")  # TODO: one JSON object per line

    def info(self, message: str, **fields) -> None:
        self._log("INFO", message, **fields)

    def error(self, message: str, exc: Exception | None = None, **fields) -> None:
        # TODO: describe the exception
        self._log("ERROR", message, **fields)


def handler(event, context, logger: JsonLogger):
    # TODO: set logger.correlation_id
    logger.info("order received", order_id=event.get("order_id"))
    try:
        if event.get("amount", 0) <= 0:
            raise ValueError("amount must be positive")
    except ValueError as exc:
        logger.error("order rejected", exc=exc, order_id=event.get("order_id"))
        return {"statusCode": 400}
    return {"statusCode": 200}


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run cw_5
# =============================================================================
import io  # noqa: E402

from awslings.testing import FakeContext  # noqa: E402

FIXED = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)


def _run(event):
    stream = io.StringIO()
    logger = JsonLogger("checkout", stream=stream, clock=lambda: FIXED)
    result = handler(event, FakeContext(request_id="req-1"), logger)
    return result, [json.loads(line) for line in stream.getvalue().splitlines()]


def test_info_line_is_json():
    _, lines = _run({"order_id": "o-1", "amount": 10})
    assert lines == [
        {"timestamp": "2026-10-21T12:00:00+00:00", "level": "INFO", "service": "checkout", "message": "order received", "correlation_id": "req-1", "order_id": "o-1"}
    ]


def test_correlation_id_is_propagated():
    _, lines = _run({"order_id": "o-1", "amount": 10, "headers": {"x-correlation-id": "corr-42"}})
    assert lines[0]["correlation_id"] == "corr-42"


def test_error_details():
    result, lines = _run({"order_id": "o-2", "amount": 0})
    assert result == {"statusCode": 400}
    error = lines[-1]
    assert error["level"] == "ERROR" and error["order_id"] == "o-2"
    assert error["error"] == {"type": "ValueError", "message": "amount must be positive"}
