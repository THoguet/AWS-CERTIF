"""
Exercise s3_7 — Handling S3 events in Lambda
============================================
Book: chapter 4, "Event notifications" and chapter 5, "Event sources"
Exam: Domain 1 · Task 1.2 (event-driven architecture, handling the event lifecycle)

A thumbnail function is triggered by S3 ObjectCreated events. Two bugs
show up again and again in production (and in exam questions):

  1. Object keys in the event are URL-encoded: "my photo (1).jpg" arrives
     as "my+photo+%281%29.jpg". Calling GetObject with the raw key gives
     NoSuchKey.
  2. If the function writes its output to the SAME bucket that triggers
     it, every output triggers a new invocation: an infinite loop and a
     huge bill. Use another bucket, or a prefix filter on the trigger plus
     a guard in code. Lambda can also detect and stop some recursive loops.

Your task
---------
  * `objects_from_event(event)`: list of (bucket, decoded_key, size),
  * `handler(event, context)`: return {"to_process": [decoded keys]},
    ignoring objects under OUTPUT_PREFIX.
"""

# I AM NOT DONE

from urllib.parse import unquote_plus

OUTPUT_PREFIX = "thumbnails/"


def objects_from_event(event: dict) -> list[tuple[str, str, int]]:
    # TODO: decode the keys!
    return [(r["s3"]["bucket"]["name"], r["s3"]["object"]["key"], r["s3"]["object"]["size"]) for r in event["Records"]]


def handler(event, context):
    # TODO: ignore our own output to avoid recursive invocations
    return {"to_process": [key for _, key, _ in objects_from_event(event)]}


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run s3_7
# =============================================================================


def _event(*keys):
    return {
        "Records": [
            {
                "eventSource": "aws:s3",
                "eventName": "ObjectCreated:Put",
                "awsRegion": "eu-west-3",
                "s3": {"bucket": {"name": "media"}, "object": {"key": key, "size": 1024}},
            }
            for key in keys
        ]
    }


def test_keys_are_decoded():
    objects = objects_from_event(_event("uploads/my+photo+%281%29.jpg", "uploads/caf%C3%A9.png"))
    assert objects == [("media", "uploads/my photo (1).jpg", 1024), ("media", "uploads/café.png", 1024)]


def test_ignores_own_output():
    result = handler(_event("uploads/a.jpg", "thumbnails/a.jpg", "uploads/b+c.jpg"), None)
    assert result == {"to_process": ["uploads/a.jpg", "uploads/b c.jpg"]}


def test_empty_event():
    assert handler({"Records": []}, None) == {"to_process": []}
