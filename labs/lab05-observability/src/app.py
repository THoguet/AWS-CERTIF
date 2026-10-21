"""lab05: a checkout endpoint instrumented for the three pillars of observability.

Traces   Lambda active tracing records the function. The X-Ray SDK adds subsegments for DynamoDB
         (patched boto3) and for the simulated payment provider, with annotations and metadata.
Logs     One JSON object per line, with a correlation id and the X-Ray trace id.
Metrics  CloudWatch Embedded Metric Format (EMF): log lines that CloudWatch turns into metrics.

Query string: tier=gold|silver|free, amount=42.5, delay=0.3 (payment latency, seconds), fail=true
"""

import json
import os
import time
import uuid
from decimal import Decimal

import boto3
from aws_xray_sdk.core import patch_all, xray_recorder

patch_all()  # record boto3 calls (DynamoDB here) as X-Ray subsegments

TABLE = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
SERVICE = os.environ.get("SERVICE_NAME", "checkout")
NAMESPACE = os.environ.get("METRICS_NAMESPACE", "DvaLab05")
TIERS = ("gold", "silver", "free")


def log(level: str, message: str, **fields) -> None:
    """Structured log line: filterable by metric filters and Logs Insights."""
    print(json.dumps({"level": level, "service": SERVICE, "message": message, **fields}))


def emit_metrics(tier: str, order_value: float, payment_ms: float) -> None:
    """One EMF log line = two metrics (OrderValue, PaymentLatency) with dimensions Service and Tier."""
    print(json.dumps({
        "_aws": {
            "Timestamp": int(time.time() * 1000),
            "CloudWatchMetrics": [{
                "Namespace": NAMESPACE,
                "Dimensions": [["Service", "Tier"]],
                "Metrics": [
                    {"Name": "OrderValue", "Unit": "None"},
                    {"Name": "PaymentLatency", "Unit": "Milliseconds"},
                ],
            }],
        },
        "Service": SERVICE,
        "Tier": tier,
        "OrderValue": order_value,
        "PaymentLatency": payment_ms,
    }))


def charge(amount: float, delay: float, fail: bool) -> None:
    """Pretend to call a payment provider. It appears as its own subsegment in the trace."""
    with xray_recorder.in_subsegment("payment-provider") as subsegment:
        subsegment.put_metadata("amount", amount, "payment")
        time.sleep(delay)
        if fail:
            raise RuntimeError("payment provider timed out")


def parse(event: dict) -> tuple[str, float, float, bool]:
    params = event.get("queryStringParameters") or {}
    tier = params.get("tier") if params.get("tier") in TIERS else "free"
    try:
        amount = round(float(params.get("amount", "25")), 2)
        delay = min(max(float(params.get("delay", "0.1")), 0.0), 5.0)
    except ValueError:
        amount, delay = 25.0, 0.1
    fail = str(params.get("fail", "false")).lower() == "true"
    return tier, amount, delay, fail


def handler(event, context):
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    correlation_id = headers.get("x-correlation-id") or str(uuid.uuid4())
    trace_id = os.environ.get("_X_AMZN_TRACE_ID", "").split(";")[0].removeprefix("Root=")
    tier, amount, delay, fail = parse(event)
    fields = {"correlation_id": correlation_id, "trace_id": trace_id, "tier": tier}

    # Lambda owns the function segment and the SDK cannot modify it: annotate a subsegment instead.
    with xray_recorder.in_subsegment("checkout") as subsegment:
        subsegment.put_annotation("customer_tier", tier)          # indexed: usable in filter expressions
        subsegment.put_annotation("correlation_id", correlation_id)
        subsegment.put_metadata("request", {"amount": amount, "delay": delay, "fail": fail}, "checkout")

        started = time.monotonic()
        try:
            charge(amount, delay, fail)
        except RuntimeError as exc:
            log("ERROR", "payment failed", error=str(exc), **fields)
            raise                                                  # Lambda error -> 502, X-Ray fault
        payment_ms = round((time.monotonic() - started) * 1000, 1)

        order_id = str(uuid.uuid4())
        TABLE.put_item(Item={"id": order_id, "tier": tier, "amount": Decimal(str(amount))})

    emit_metrics(tier, amount, payment_ms)
    log("INFO", "order placed", order_id=order_id, amount=amount, latency_ms=payment_ms, **fields)
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json", "X-Correlation-Id": correlation_id},
        "body": json.dumps({"order_id": order_id, "tier": tier, "amount": amount}),
    }
