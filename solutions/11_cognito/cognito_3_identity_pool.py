"""
Exercise cognito_3 — Identity pools: AWS credentials for app users
==================================================================
Book: chapter 12, "Identity pools" (book/src/ch12-cognito.md)
Exam: Domain 2 · Task 2.1 (identity federation, user pools vs identity pools)

User pool = AUTHENTICATION (who are you? → JWTs).
Identity pool = AUTHORIZATION to AWS (exchange a token from Cognito user
pools, Google, Apple, SAML, OIDC... or nothing at all for guests for
temporary AWS credentials of an IAM role, through STS).

The mobile app uploads photos straight to S3. Each user may only touch
`private/<their identity id>/`. The policy variable
`${cognito-identity.amazonaws.com:sub}` holds the IDENTITY id (not the
user pool sub!).

Your task
---------
  * PHOTO_POLICY: permissions of the authenticated role: s3:GetObject and
    s3:PutObject on arn:aws:s3:::photo-app/private/${cognito-identity.amazonaws.com:sub}/*,
  * `create_identity_pool(ci, user_pool_id, client_id, region)`: no guest
    access, trusts the user pool's app client. Return the pool id,
  * `credentials_for(ci, identity_pool_id, provider, id_token)`: return
    the temporary AWS credentials.
"""

PHOTO_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": ["s3:GetObject", "s3:PutObject"],
            "Resource": "arn:aws:s3:::photo-app/private/${cognito-identity.amazonaws.com:sub}/*",
        }
    ],
}


def provider_name(region: str, user_pool_id: str) -> str:
    return f"cognito-idp.{region}.amazonaws.com/{user_pool_id}"


def create_identity_pool(ci, user_pool_id: str, client_id: str, region: str) -> str:
    return ci.create_identity_pool(
        IdentityPoolName="photo_app",
        AllowUnauthenticatedIdentities=False,
        CognitoIdentityProviders=[{"ProviderName": provider_name(region, user_pool_id), "ClientId": client_id}],
    )["IdentityPoolId"]


def credentials_for(ci, identity_pool_id: str, provider: str, id_token: str) -> dict:
    logins = {provider: id_token}
    identity_id = ci.get_id(IdentityPoolId=identity_pool_id, Logins=logins)["IdentityId"]
    return ci.get_credentials_for_identity(IdentityId=identity_id, Logins=logins)["Credentials"]


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run cognito_3
# =============================================================================
import boto3  # noqa: E402


def test_policy_isolates_users():
    resource = PHOTO_POLICY["Statement"][0]["Resource"]
    assert resource == "arn:aws:s3:::photo-app/private/${cognito-identity.amazonaws.com:sub}/*"


def test_identity_pool_trusts_user_pool(aws, region):
    ci = boto3.client("cognito-identity")
    pool_id = create_identity_pool(ci, "eu-west-3_Example", "client-123", region)
    pool = ci.describe_identity_pool(IdentityPoolId=pool_id)
    assert pool["AllowUnauthenticatedIdentities"] is False
    assert pool["CognitoIdentityProviders"][0]["ProviderName"] == "cognito-idp.eu-west-3.amazonaws.com/eu-west-3_Example"
    assert pool["CognitoIdentityProviders"][0]["ClientId"] == "client-123"


def test_exchange_token_for_credentials(aws, region):
    idp, ci = boto3.client("cognito-idp"), boto3.client("cognito-identity")
    user_pool = idp.create_user_pool(PoolName="p")["UserPool"]["Id"]
    client = idp.create_user_pool_client(UserPoolId=user_pool, ClientName="app", ExplicitAuthFlows=["ALLOW_USER_PASSWORD_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"])["UserPoolClient"]["ClientId"]
    idp.sign_up(ClientId=client, Username="ada", Password="Analytical-Engine-1843")
    idp.admin_confirm_sign_up(UserPoolId=user_pool, Username="ada")
    id_token = idp.initiate_auth(ClientId=client, AuthFlow="USER_PASSWORD_AUTH", AuthParameters={"USERNAME": "ada", "PASSWORD": "Analytical-Engine-1843"})["AuthenticationResult"]["IdToken"]
    identity_pool = create_identity_pool(ci, user_pool, client, region)
    creds = credentials_for(ci, identity_pool, provider_name(region, user_pool), id_token)
    assert {"AccessKeyId", "SecretKey", "SessionToken", "Expiration"} <= set(creds)
