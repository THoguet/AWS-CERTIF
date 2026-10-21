"""
Exercise xray_1 — Annotations, metadata and subsegments
=======================================================
Book: chapter 21, "AWS X-Ray and OpenTelemetry" (book/src/ch21-tracing.md)
Exam: Domain 4 · Task 4.2 (adding annotations for tracing services), Task 4.1 (service maps)

A trace is made of SEGMENTS (one per service) and SUBSEGMENTS (a
downstream call, an SQL query, a block of your code).
  * ANNOTATIONS: key/value pairs (string, number, boolean) that are
    INDEXED. Use them in filter expressions and to group traces.
    Max 50 per trace.
  * METADATA: any JSON value, NOT indexed. Use it for debugging details
    such as full payloads.
Filter expressions look like:
    annotation.customer_tier = "gold" AND fault
    service("checkout") { responsetime > 2 }

(The X-Ray SDKs entered maintenance mode in February 2026. AWS now
recommends OpenTelemetry/ADOT. The concepts and the exam vocabulary are
the same: OpenTelemetry span attributes are converted into X-Ray
annotations or metadata.)

In AWS Lambda, the function segment belongs to Lambda and the SDK cannot
modify it: put annotations on a subsegment you create (see
labs/lab05-observability).

Your task
---------
  * `record_checkout(recorder, order, pay)`: annotate customer_tier
    and order_total, attach the whole order as metadata (namespace
    "shop"), and call pay(order) inside a subsegment "payment-provider".
    If pay raises, record the exception on the subsegment and re-raise,
  * GOLD_FAULTS: filter expression for traces of gold customers that faulted.
"""


def record_checkout(recorder, order: dict, pay):
    recorder.put_annotation("customer_tier", order["tier"])
    recorder.put_annotation("order_total", order["total"])
    recorder.put_metadata("order", order, "shop")
    subsegment = recorder.begin_subsegment("payment-provider")
    try:
        return pay(order)
    except Exception as exc:
        subsegment.add_exception(exc)
        raise
    finally:
        recorder.end_subsegment()


GOLD_FAULTS = 'annotation.customer_tier = "gold" AND fault'


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run xray_1
# =============================================================================
import re  # noqa: E402

import pytest  # noqa: E402


class FakeSubsegment:
    def __init__(self, name):
        self.name, self.exceptions = name, []

    def add_exception(self, exc, stack=None):
        self.exceptions.append(exc)


class FakeRecorder:
    def __init__(self):
        self.annotations, self.metadata, self.events = {}, {}, []

    def put_annotation(self, key, value):
        self.annotations[key] = value

    def put_metadata(self, key, value, namespace="default"):
        self.metadata[(namespace, key)] = value

    def begin_subsegment(self, name):
        self.events.append(("begin", name))
        self.current = FakeSubsegment(name)
        return self.current

    def end_subsegment(self):
        self.events.append(("end", self.current.name))


ORDER = {"id": "o-1", "tier": "gold", "total": 129.9, "items": [{"sku": "MUG", "qty": 2}]}


def test_annotations_and_metadata():
    recorder = FakeRecorder()
    record_checkout(recorder, ORDER, lambda order: "paid")
    assert recorder.annotations == {"customer_tier": "gold", "order_total": 129.9}
    assert recorder.metadata == {("shop", "order"): ORDER}


def test_payment_in_subsegment():
    recorder, calls = FakeRecorder(), []

    def pay(order):
        calls.append(recorder.events[-1])
        return "paid"

    assert record_checkout(recorder, ORDER, pay) == "paid"
    assert calls == [("begin", "payment-provider")], "pay() must run inside the subsegment"
    assert recorder.events == [("begin", "payment-provider"), ("end", "payment-provider")]


def test_exception_is_recorded_and_subsegment_closed():
    recorder = FakeRecorder()

    def pay(order):
        raise TimeoutError("provider timeout")

    with pytest.raises(TimeoutError):
        record_checkout(recorder, ORDER, pay)
    assert [type(e) for e in recorder.current.exceptions] == [TimeoutError]
    assert recorder.events[-1] == ("end", "payment-provider")


def test_filter_expression():
    assert re.fullmatch(r'annotation\.customer_tier\s*=\s*"gold"\s+AND\s+(fault|fault\s*=\s*true)', GOLD_FAULTS.strip())
