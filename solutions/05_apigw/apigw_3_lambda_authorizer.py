"""
Exercise apigw_3 — A Lambda (TOKEN) authorizer
==============================================
Book: chapter 6, "Securing APIs" (book/src/ch06-api-gateway-appsync.md)
Exam: Domain 2 · Task 2.1 (securing applications by using bearer tokens)

A Lambda authorizer receives the caller's token and returns an IAM policy
that allows or denies `execute-api:Invoke`:

    {"principalId": "alice",
     "policyDocument": {"Version": "2012-10-17", "Statement": [
         {"Action": "execute-api:Invoke", "Effect": "Allow", "Resource": "<arn>"}]},
     "context": {"tier": "gold"}}         # only strings, numbers and booleans

Behaviours to know:
  * raise Exception("Unauthorized")  → client gets 401,
  * return a Deny policy             → client gets 403,
  * API Gateway CACHES the returned policy per token (default TTL 300 s).
    If you allow only the exact methodArn, the cached policy then DENIES
    the same caller on other methods/paths. Allow the whole stage instead:
    arn:aws:execute-api:<region>:<account>:<api-id>/<stage>/*/*
  * `context` values reach the backend (e.g. $context.authorizer.tier).

Your task
---------
Implement `stage_wildcard(method_arn)`, `policy(...)` and `handler(event, context)`.
"""

TOKENS = {
    "tok-alice": {"user": "alice", "tier": "gold", "revoked": False},
    "tok-bob": {"user": "bob", "tier": "free", "revoked": True},
}


def stage_wildcard(method_arn: str) -> str:
    api_arn, _, path = method_arn.partition("/")  # ".../a1b2c3" and "prod/GET/orders/42"
    stage = path.split("/")[0]
    return f"{api_arn}/{stage}/*/*"


def policy(principal_id: str, effect: str, resource: str, context: dict | None = None) -> dict:
    response = {
        "principalId": principal_id,
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [{"Action": "execute-api:Invoke", "Effect": effect, "Resource": resource}],
        },
    }
    if context:
        response["context"] = context
    return response


def handler(event, context):
    token = event.get("authorizationToken", "").removeprefix("Bearer ").strip()
    info = TOKENS.get(token)
    if info is None:
        raise Exception("Unauthorized")
    resource = stage_wildcard(event["methodArn"])
    if info["revoked"]:
        return policy(info["user"], "Deny", resource)
    return policy(info["user"], "Allow", resource, {"user": info["user"], "tier": info["tier"]})


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run apigw_3
# =============================================================================
import pytest  # noqa: E402

METHOD_ARN = "arn:aws:execute-api:eu-west-3:123456789012:a1b2c3/prod/GET/orders/42"
STAGE_ARN = "arn:aws:execute-api:eu-west-3:123456789012:a1b2c3/prod/*/*"


def _event(token):
    return {"type": "TOKEN", "authorizationToken": token, "methodArn": METHOD_ARN}


def test_stage_wildcard():
    assert stage_wildcard(METHOD_ARN) == STAGE_ARN


def test_valid_token_is_allowed_on_whole_stage():
    result = handler(_event("Bearer tok-alice"), None)
    assert result["principalId"] == "alice"
    statement = result["policyDocument"]["Statement"][0]
    assert result["policyDocument"]["Version"] == "2012-10-17"
    assert statement == {"Action": "execute-api:Invoke", "Effect": "Allow", "Resource": STAGE_ARN}
    assert result["context"] == {"user": "alice", "tier": "gold"}


def test_revoked_token_gets_explicit_deny():
    result = handler(_event("Bearer tok-bob"), None)
    assert result["policyDocument"]["Statement"][0]["Effect"] == "Deny"


def test_unknown_token_is_unauthorized():
    with pytest.raises(Exception, match="^Unauthorized$"):
        handler(_event("Bearer forged"), None)
