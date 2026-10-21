"""
Exercise cognito_1 — User pool sign-up and sign-in
==================================================
Book: chapter 12, "Cognito user pools" (book/src/ch12-cognito.md)
Exam: Domain 2 · Task 2.1 (identity providers, bearer tokens, user pools vs identity pools)

A Cognito USER POOL is a user directory and an OpenID Connect identity
provider. After authentication it returns three JWTs:
  * ID token      — who the user is (claims: sub, email, cognito:groups...),
  * access token  — what the user may do (scopes, groups), sent to APIs,
  * refresh token — exchanged for new ID/access tokens (default validity
                    30 days, while ID/access tokens last 1 hour by default).

A public client (SPA, mobile app) must NOT have a client secret. Its
allowed auth flows are set with ExplicitAuthFlows. (USER_SRP_AUTH is the
secure default for apps. USER_PASSWORD_AUTH sends the password over TLS.)

Your task
---------
  * `create_pool(idp)`: pool "shop-users" (passwords >= 12 chars with
    numbers, email auto-verified) + public app client "web" allowing
    USER_PASSWORD_AUTH and refresh. Return (pool_id, client_id),
  * `register(idp, pool_id, client_id, username, password, email)`: self
    sign-up, then confirm as an admin (in real life: the email code),
  * `login(idp, client_id, username, password)` → AuthenticationResult,
  * `refresh(idp, client_id, refresh_token)` → new AuthenticationResult.
"""


def create_pool(idp) -> tuple[str, str]:
    pool_id = idp.create_user_pool(
        PoolName="shop-users",
        Policies={"PasswordPolicy": {"MinimumLength": 12, "RequireNumbers": True}},
        AutoVerifiedAttributes=["email"],
    )["UserPool"]["Id"]
    client_id = idp.create_user_pool_client(
        UserPoolId=pool_id,
        ClientName="web",
        GenerateSecret=False,
        ExplicitAuthFlows=["ALLOW_USER_PASSWORD_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"],
    )["UserPoolClient"]["ClientId"]
    return pool_id, client_id


def register(idp, pool_id: str, client_id: str, username: str, password: str, email: str) -> None:
    idp.sign_up(ClientId=client_id, Username=username, Password=password, UserAttributes=[{"Name": "email", "Value": email}])
    idp.admin_confirm_sign_up(UserPoolId=pool_id, Username=username)


def login(idp, client_id: str, username: str, password: str) -> dict:
    return idp.initiate_auth(
        ClientId=client_id, AuthFlow="USER_PASSWORD_AUTH", AuthParameters={"USERNAME": username, "PASSWORD": password}
    )["AuthenticationResult"]


def refresh(idp, client_id: str, refresh_token: str) -> dict:
    return idp.initiate_auth(ClientId=client_id, AuthFlow="REFRESH_TOKEN_AUTH", AuthParameters={"REFRESH_TOKEN": refresh_token})[
        "AuthenticationResult"
    ]


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run cognito_1
# =============================================================================
import boto3  # noqa: E402
import pytest  # noqa: E402
from botocore.exceptions import ClientError  # noqa: E402


@pytest.fixture
def idp(aws):
    return boto3.client("cognito-idp")


def test_pool_configuration(idp):
    pool_id, client_id = create_pool(idp)
    pool = idp.describe_user_pool(UserPoolId=pool_id)["UserPool"]
    assert pool["Name"] == "shop-users"
    assert pool["Policies"]["PasswordPolicy"]["MinimumLength"] == 12
    client = idp.describe_user_pool_client(UserPoolId=pool_id, ClientId=client_id)["UserPoolClient"]
    assert "ClientSecret" not in client, "public clients must not have a secret"
    assert set(client["ExplicitAuthFlows"]) == {"ALLOW_USER_PASSWORD_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"}


def test_weak_password_is_rejected(idp):
    pool_id, client_id = create_pool(idp)
    with pytest.raises(ClientError) as error:
        register(idp, pool_id, client_id, "eve", "short1", "eve@example.com")
    assert error.value.response["Error"]["Code"] == "InvalidPasswordException"


def test_login_and_refresh(idp):
    pool_id, client_id = create_pool(idp)
    register(idp, pool_id, client_id, "ada", "Analytical-Engine-1843", "ada@example.com")
    tokens = login(idp, client_id, "ada", "Analytical-Engine-1843")
    assert {"IdToken", "AccessToken", "RefreshToken"} <= set(tokens)
    renewed = refresh(idp, client_id, tokens["RefreshToken"])
    assert {"IdToken", "AccessToken"} <= set(renewed)
    assert "RefreshToken" not in renewed, "refreshing does not issue a new refresh token"
