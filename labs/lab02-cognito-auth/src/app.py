"""lab02: routes behind an API Gateway Cognito user pool authorizer.

API Gateway has already verified the token (signature, expiry, issuer) before invoking this function.
The verified claims arrive in event["requestContext"]["authorizer"]["claims"].
"""

import json
import re


def response(status: int, body: dict) -> dict:
    return {"statusCode": status, "headers": {"Content-Type": "application/json"}, "body": json.dumps(body)}


def claims_of(event: dict) -> dict:
    return ((event.get("requestContext") or {}).get("authorizer") or {}).get("claims") or {}


def groups_of(claims: dict) -> list[str]:
    """cognito:groups arrives as a string in REST API claims ("admins" or "[admins, readers]")."""
    raw = claims.get("cognito:groups") or ""
    if isinstance(raw, list):
        return [g for g in raw if g]
    return [g for g in re.split(r"[\s,]+", raw.strip("[]")) if g]


def handler(event, context):
    route = event.get("resource")
    if route == "/health":
        return response(200, {"status": "ok"})

    claims = claims_of(event)
    if route == "/me":
        return response(200, {
            "sub": claims.get("sub"),
            "email": claims.get("email"),
            "token_use": claims.get("token_use"),
            "groups": groups_of(claims),
            "issuer": claims.get("iss"),
        })
    if route == "/admin":
        # Authentication was done by API Gateway; authorization is your code's job.
        if "admins" not in groups_of(claims):
            return response(403, {"message": "admins only"})
        return response(200, {"message": f"welcome, admin {claims.get('email')}"})
    return response(404, {"message": f"no route {route}"})
