"""lab04: the application that the pipeline tests, packages and deploys."""

import json
import os

RELEASE = "1"


def greeting(stage: str, name: str | None) -> str:
    who = name.strip() if name and name.strip() else "world"
    return f"Hello, {who}, from {stage}!"


def handler(event, context):
    params = event.get("queryStringParameters") or {}   # absent when there is no query string
    body = {"message": greeting(os.environ.get("STAGE", "dev"), params.get("name")), "release": RELEASE}
    return {"statusCode": 200, "headers": {"Content-Type": "application/json"}, "body": json.dumps(body)}
