# Lab 02 — Cognito-protected API

> **Goal**: create a Cognito user pool, sign up and sign in from the CLI, read the tokens' claims,
> and call a REST API protected by a **Cognito user pool authorizer**. Then use a **group** for
> authorization and see why a token must be refreshed to pick up a change.
>
> **Book**: ch12 (Cognito), ch06 (API Gateway authorizers) · **Exercises**: `cognito_1`, `cognito_2`,
> `apigw_3` · **Time**: 1 h · **Cost**: < $0.10 if deleted the same day

```text
CLI ──sign-up / initiate-auth──► Cognito user pool ──► ID, access and refresh tokens (JWT)
CLI ──GET /me  Authorization: <ID token>──► API Gateway (Cognito authorizer: signature, expiry, issuer)
                                                  └──► Lambda reads requestContext.authorizer.claims
```

Files: `template.yaml`, `src/app.py` (routes `/health`, `/me`, `/admin`), `scripts/decode_jwt.py`,
`tests/`.

## 1. Deploy

```bash
cd labs/lab02-cognito-auth
sam build && sam deploy --guided      # stack dva-lab02, Region eu-west-3, save to samconfig.toml
```

Answer `y` when SAM warns that a function "may not have authorization defined": that is the public
`/health` route (`Authorizer: NONE`).

```bash
out() { aws cloudformation describe-stacks --stack-name dva-lab02 \
        --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }
API=$(out ApiUrl); POOL=$(out UserPoolId); CLIENT=$(out ClientId); FN=$(out FunctionName)

curl -s "$API/health"          # {"status": "ok"}
curl -s -i "$API/me"           # 401 {"message":"Unauthorized"}: no token
```

## 2. Sign up, and see an unconfirmed user fail

```bash
EMAIL=you@example.com            # use an address you can read
PASSWORD='Exam-Ready-2026'       # 12+ characters, upper, lower, digit (no commas: shorthand syntax below)

aws cognito-idp sign-up --client-id "$CLIENT" --username "$EMAIL" --password "$PASSWORD" \
    --user-attributes Name=email,Value="$EMAIL"
# "UserConfirmed": false, and a code is emailed to you

aws cognito-idp initiate-auth --client-id "$CLIENT" --auth-flow USER_PASSWORD_AUTH \
    --auth-parameters USERNAME="$EMAIL",PASSWORD="$PASSWORD"
# An error occurred (UserNotConfirmedException) ... User is not confirmed.
```

Confirm the account with the emailed code, or as an administrator:

```bash
aws cognito-idp confirm-sign-up --client-id "$CLIENT" --username "$EMAIL" --confirmation-code 123456
# or, without the email:
aws cognito-idp admin-confirm-sign-up --user-pool-id "$POOL" --username "$EMAIL"
```

## 3. Sign in and inspect the tokens

```bash
aws cognito-idp initiate-auth --client-id "$CLIENT" --auth-flow USER_PASSWORD_AUTH \
    --auth-parameters USERNAME="$EMAIL",PASSWORD="$PASSWORD" > /tmp/lab02-auth.json
token() { python3 -c "import json; print(json.load(open('/tmp/lab02-auth.json'))['AuthenticationResult']['$1'])"; }
ID_TOKEN=$(token IdToken); ACCESS_TOKEN=$(token AccessToken); REFRESH_TOKEN=$(token RefreshToken)

python3 scripts/decode_jwt.py "$ID_TOKEN"
python3 scripts/decode_jwt.py "$ACCESS_TOKEN"
```

Compare the two:

| Claim | ID token | Access token |
|---|---|---|
| `token_use` | `id` | `access` |
| Who it is for | `aud` = the app client id | `client_id` = the app client id |
| User attributes | `email`, `email_verified`, `cognito:username`... | none (only `sub`, `username`) |
| `scope` | — | `aws.cognito.signin.user.admin` |
| `iss` | `https://cognito-idp.eu-west-3.amazonaws.com/<pool id>` | same |
| `exp` | 60 minutes after sign-in (set in the template) | same |

The header contains `kid`: the id of the pool's public key (published at
`$iss/.well-known/jwks.json`) that verifies the RS256 signature.

## 4. Call the API with each token

```bash
curl -s -i "$API/me" -H "Authorization: $ID_TOKEN"          # 200, your claims
curl -s -i "$API/me" -H "Authorization: $ACCESS_TOKEN"      # which status?
curl -s -i "$API/me" -H "Authorization: ${ID_TOKEN}x"       # 401: the signature check fails
```

With **no OAuth scopes** configured on a method, the REST API Cognito authorizer expects the **ID
token**, so the access token is refused (401). Access tokens are for methods that require scopes
(an `AuthorizationScopes` list on the method, for example a custom resource-server scope).

## 5. Authorization with a group

```bash
curl -s "$API/admin" -H "Authorization: $ID_TOKEN"          # 403 {"message": "admins only"}: your code says no

aws cognito-idp admin-add-user-to-group --user-pool-id "$POOL" --username "$EMAIL" --group-name admins
curl -s "$API/admin" -H "Authorization: $ID_TOKEN"          # still 403!
```

Claims are written into the token when it is issued. The old token has no `cognito:groups` claim.
Get new tokens with the refresh token (no password needed):

```bash
ID_TOKEN=$(aws cognito-idp initiate-auth --client-id "$CLIENT" --auth-flow REFRESH_TOKEN_AUTH \
    --auth-parameters REFRESH_TOKEN="$REFRESH_TOKEN" --query AuthenticationResult.IdToken --output text)
python3 scripts/decode_jwt.py "$ID_TOKEN" | grep -A2 groups
curl -s "$API/admin" -H "Authorization: $ID_TOKEN"          # 200 {"message": "welcome, admin ..."}
```

## 6. Sign out everywhere

```bash
aws cognito-idp global-sign-out --access-token "$ACCESS_TOKEN"
aws cognito-idp initiate-auth --client-id "$CLIENT" --auth-flow REFRESH_TOKEN_AUTH \
    --auth-parameters REFRESH_TOKEN="$REFRESH_TOKEN"
# NotAuthorizedException: the refresh token was revoked
```

`GlobalSignOut` revokes the user's refresh tokens (and the access tokens for Cognito's own APIs).
JWTs that were already issued keep their signature and expiry. That is one reason to keep
token lifetimes short.

## 7. Explore

- Console → Cognito → your pool: *Users* (status `CONFIRMED`), *Groups*, *App clients* (allowed
  authentication flows, token validity, no client secret).
- Console → API Gateway → `dva-lab02` → *Authorizers*: test the authorizer with a token directly.
- Read the function's logs (`sam logs --stack-name dva-lab02 -n ProfileFunction`): no 401 ever
  reaches Lambda, because API Gateway rejects bad tokens before invoking it (and you do not pay for
  those invocations).

## Teardown

```bash
sam delete --stack-name dva-lab02
aws logs delete-log-group --log-group-name "/aws/lambda/$FN"
```

Deleting the stack deletes the user pool and all its users.

## What to remember for the exam

- **User pool** = authentication and JWTs. **Identity pool** = exchange a token for temporary AWS
  credentials (not used here, see `cognito_3`).
- REST API Cognito authorizer: **ID token** when the method has no scopes, **access token** when it
  requires OAuth scopes. Claims reach Lambda in `requestContext.authorizer.claims`.
- Groups appear in the `cognito:groups` claim. Changes appear only in **newly issued** tokens: refresh
  with `REFRESH_TOKEN_AUTH`.
- `UserNotConfirmedException` = sign-up not confirmed (code, `AdminConfirmSignUp`, or a pre sign-up trigger).
- Public clients (SPA, mobile, CLI) have **no client secret**. `USER_PASSWORD_AUTH` sends the password
  to Cognito. `USER_SRP_AUTH` never sends it (the SDKs and Amplify use SRP).
