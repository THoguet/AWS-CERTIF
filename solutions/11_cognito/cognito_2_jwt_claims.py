"""
Exercise cognito_2 — Reading and checking JWT claims
====================================================
Book: chapter 12, "Tokens and JWT validation" (book/src/ch12-cognito.md)
Exam: Domain 2 · Task 2.1 (bearer tokens: JWT, OAuth; role-based access control)

Your backend receives Cognito ACCESS tokens in the Authorization header.
Validating a JWT means:
  1. verify the SIGNATURE with the pool's public keys
     (https://cognito-idp.<region>.amazonaws.com/<pool-id>/.well-known/jwks.json).
     Libraries such as aws-jwt-verify or python-jose do this, and so do
     API Gateway's Cognito authorizer and JWT authorizer, for free,
  2. check `exp` (not expired), `iss` (your pool), and `token_use`
     ("access" or "id") / `client_id` or `aud` (your app client),
  3. authorize with claims, for example the `cognito:groups` claim (RBAC).

This exercise covers steps 2 and 3. The signature check is assumed done
upstream (by API Gateway).

Your task
---------
  * `claims(token)`: decode the payload (no signature check),
  * `authorize(token, required_group, issuer, client_id, now)`: True only
    if the token is an unexpired ACCESS token for this issuer and client,
    and the user is in `required_group`.
"""

import base64
import json
import time


def claims(token: str) -> dict:
    payload = token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(payload))


def authorize(token: str, required_group: str, issuer: str, client_id: str, now=time.time) -> bool:
    c = claims(token)
    return (
        c.get("exp", 0) > now()
        and c.get("iss") == issuer
        and c.get("token_use") == "access"
        and c.get("client_id") == client_id
        and required_group in c.get("cognito:groups", [])
    )


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run cognito_2
# =============================================================================
import boto3  # noqa: E402

ISSUER = "https://cognito-idp.eu-west-3.amazonaws.com/eu-west-3_Example"
CLIENT = "app-client-123"
NOW = 1_800_000_000


def _token(**overrides):
    payload = {"iss": ISSUER, "token_use": "access", "client_id": CLIENT, "exp": NOW + 600, "cognito:groups": ["admins"], "sub": "u-1"}
    payload.update(overrides)
    payload = {k: v for k, v in payload.items() if v is not None}

    def b64(data):
        return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()

    return f"{b64({'alg': 'RS256', 'kid': 'k1'})}.{b64(payload)}.signature"


def test_claims_decoding_handles_missing_padding():
    assert claims(_token(sub="abc"))["sub"] == "abc"
    assert claims(_token(sub="abcd"))["sub"] == "abcd"


def test_valid_admin_token():
    assert authorize(_token(), "admins", ISSUER, CLIENT, now=lambda: NOW) is True


def test_rejections():
    clock = lambda: NOW  # noqa: E731
    assert not authorize(_token(exp=NOW - 1), "admins", ISSUER, CLIENT, now=clock), "expired"
    assert not authorize(_token(iss="https://evil.example.com"), "admins", ISSUER, CLIENT, now=clock), "wrong issuer"
    assert not authorize(_token(token_use="id"), "admins", ISSUER, CLIENT, now=clock), "ID token used as access token"
    assert not authorize(_token(client_id="other-app"), "admins", ISSUER, CLIENT, now=clock), "wrong client"
    assert not authorize(_token(**{"cognito:groups": None}), "admins", ISSUER, CLIENT, now=clock), "no groups"
    assert not authorize(_token(**{"cognito:groups": ["readers"]}), "admins", ISSUER, CLIENT, now=clock), "wrong group"


def test_real_cognito_token(aws, region):
    idp = boto3.client("cognito-idp")
    pool = idp.create_user_pool(PoolName="p")["UserPool"]["Id"]
    client = idp.create_user_pool_client(UserPoolId=pool, ClientName="web", ExplicitAuthFlows=["ALLOW_USER_PASSWORD_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"])["UserPoolClient"]["ClientId"]
    idp.sign_up(ClientId=client, Username="ada", Password="Analytical-Engine-1843")
    idp.admin_confirm_sign_up(UserPoolId=pool, Username="ada")
    idp.create_group(UserPoolId=pool, GroupName="admins")
    idp.admin_add_user_to_group(UserPoolId=pool, Username="ada", GroupName="admins")
    tokens = idp.initiate_auth(ClientId=client, AuthFlow="USER_PASSWORD_AUTH", AuthParameters={"USERNAME": "ada", "PASSWORD": "Analytical-Engine-1843"})["AuthenticationResult"]
    issuer = f"https://cognito-idp.{region}.amazonaws.com/{pool}"
    assert authorize(tokens["AccessToken"], "admins", issuer, client) is True
    assert authorize(tokens["IdToken"], "admins", issuer, client) is False
