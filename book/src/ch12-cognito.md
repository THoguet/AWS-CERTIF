# Amazon Cognito

> **In this chapter**
> - User pools: sign-up/sign-in, MFA, federation, app clients and auth flows, groups, Lambda triggers
> - Tokens: ID vs access vs refresh tokens, JWT validation
> - Identity pools: temporary AWS credentials for app users, authenticated/guest roles, policy variables
> - Integrations with API Gateway, ALB and AppSync, and the classic architectures
>
> **Exam weight**: Domain 2 Task 2.1 (identity federation, bearer tokens, user pools vs identity pools)
> · **Exercises**: `cognito_1`–`cognito_3` · **Quiz**: `uv run awslings quiz cognito`

## Two different services under one name

| | **User pool** | **Identity pool** (federated identities) |
|---|---|---|
| Question it answers | **Who are you?** (authentication) | **What AWS resources can you access?** (authorization to AWS) |
| Output | **JWTs**: ID, access and refresh tokens | **Temporary AWS credentials** (via STS) for an IAM role |
| Typical consumer | Your API (API Gateway authorizer, ALB, your backend) | The app calling AWS services directly (S3, DynamoDB...) with SigV4 |
| Identity sources | Its own user directory + social (Google, Apple, Facebook, Amazon) and enterprise (SAML, OIDC) federation | User pools, social IdPs, SAML, OIDC, developer-authenticated identities, **guests (unauthenticated)** |

> **Exam tip** — "Users must sign up and sign in to the app" → **user pool**. "Mobile users must upload
> directly to S3 / write to DynamoDB with temporary credentials" → **identity pool** (usually fed by a
> user pool). The two are often used together.

## User pools

- **Sign-up and sign-in** with username, email or phone. Password policy, email/phone verification,
  account recovery, **MFA** (TOTP authenticator apps, SMS, email), and passwordless options (passkeys, one-time codes).
- **Managed login / hosted UI**: an AWS-hosted sign-in page implementing **OAuth 2.0 / OIDC**:
  authorization code grant (+ **PKCE** for public clients), client credentials grant for machine-to-machine
  (with resource servers and custom **scopes**).
- **Federation**: users sign in with Google, Apple, Facebook, Amazon, or a corporate SAML/OIDC IdP, and the user
  pool still issues its own tokens, so your app integrates only with Cognito.
- **App clients**: one per application. A **public** client (SPA, mobile) has **no client secret**. A
  confidential (server-side) client may have a secret (then requests need a `SECRET_HASH`).
  **Auth flows** allowed per client: `ALLOW_USER_SRP_AUTH` (Secure Remote Password, the password never leaves
  the device; the SDK default), `ALLOW_USER_PASSWORD_AUTH` (password sent over TLS, needed for user migration),
  `ALLOW_ADMIN_USER_PASSWORD_AUTH` (server side with IAM credentials), `ALLOW_CUSTOM_AUTH`, `ALLOW_REFRESH_TOKEN_AUTH`.
- **Groups**: role-based access. They appear in the **`cognito:groups`** claim of the tokens, and can map to IAM roles (with precedence).
- **Custom attributes** (`custom:tenant_id`) and standard OIDC attributes.
- **Threat protection** (advanced security): compromised-credential detection, adaptive authentication (risk-based MFA).

### Lambda triggers

| Trigger | Typical use |
|---|---|
| **Pre sign-up** | Validate or block sign-ups (domain allow list), auto-confirm or auto-verify users |
| **Post confirmation** | Create the user's profile in DynamoDB, send a welcome email |
| **Pre authentication** / **Post authentication** | Extra checks, block users, auditing |
| **Pre token generation** | **Add, change or remove claims** in tokens (e.g. tenant id, roles), customize scopes |
| **Custom message** | Customize verification/invitation emails and SMS |
| **Define / Create / Verify auth challenge** | Custom authentication flows (CAPTCHA, magic links, OTP) |
| **User migration** | Migrate users from a legacy directory transparently at their first sign-in |

> **Exam tip** — "Add a custom claim (tenant, permissions) to the JWT" → **pre token generation** trigger.
> "Migrate existing users without forcing a password reset" → **user migration** trigger.

## Tokens

After authentication a user pool returns three tokens:

| Token | Contents | Use | Default lifetime |
|---|---|---|---|
| **ID token** (JWT) | Identity claims: `sub`, `email`, `cognito:username`, `cognito:groups`, `aud` (= app client id), `token_use: "id"` | Tell the app who the user is (profile). Also accepted by Cognito user pool authorizers | 60 min (5 min – 24 h) |
| **Access token** (JWT) | `scope`, `client_id`, `cognito:groups`, `token_use: "access"` | **Authorize API calls** (scopes, groups), call user pool APIs for the user | 60 min (5 min – 24 h) |
| **Refresh token** (opaque) | — | Get new ID/access tokens (`REFRESH_TOKEN_AUTH`) without signing in again | **30 days** (60 min – 10 years) |

```python
tokens = idp.initiate_auth(ClientId=client_id, AuthFlow="USER_PASSWORD_AUTH",
                           AuthParameters={"USERNAME": "ada", "PASSWORD": "..."})["AuthenticationResult"]
renewed = idp.initiate_auth(ClientId=client_id, AuthFlow="REFRESH_TOKEN_AUTH",
                            AuthParameters={"REFRESH_TOKEN": tokens["RefreshToken"]})["AuthenticationResult"]
```

### Validating a JWT (what an authorizer does)

1. Decode the header, find the key `kid` in the pool's **JWKS**:
   `https://cognito-idp.<region>.amazonaws.com/<user-pool-id>/.well-known/jwks.json`.
2. Verify the **RS256 signature**.
3. Check `exp` (not expired), `iss` (`https://cognito-idp.<region>.amazonaws.com/<pool-id>`), and
   `token_use` + `aud` (ID token) or `client_id` (access token).
4. Authorize with claims: `cognito:groups`, `scope`, custom claims (exercise `cognito_2`).

You rarely do this by hand. API Gateway (Cognito/JWT authorizers), ALB authentication and the
`aws-jwt-verify` library do it for you.

> **Trap** — Sending the **ID token** where an **access token** is expected (or the reverse). For
> OAuth scopes on API Gateway methods, send the **access token**.

## Identity pools

```text
1. App signs in with the user pool          → ID token
2. App calls GetId(IdentityPoolId, Logins={"cognito-idp.<region>.amazonaws.com/<pool>": idToken})
                                             → IdentityId ("eu-west-3:1b2c...")
3. App calls GetCredentialsForIdentity(...)  → temporary AWS credentials of the AUTHENTICATED role
4. App calls S3/DynamoDB directly with SigV4 (scoped by the role's policy)
```

- **Authenticated role** for signed-in users, **unauthenticated (guest) role** for anonymous users
  (if guest access is enabled). Keep guest permissions minimal.
- **Role mapping**: choose the role from token claims (rules on `cognito:groups` or other claims, or
  "choose role from token" with `cognito:preferred_role`).
- **Per-user isolation with policy variables**: `${cognito-identity.amazonaws.com:sub}` is the
  **identity id** (not the user pool `sub`):

```json
{"Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject"],
 "Resource": "arn:aws:s3:::photo-app/private/${cognito-identity.amazonaws.com:sub}/*"}
```

  The same works for DynamoDB with `dynamodb:LeadingKeys` (rows keyed by identity id).
- **Attributes for access control**: map token claims to principal tags (ABAC).

## Integrations

| Integration | How |
|---|---|
| **API Gateway REST** | Cognito user pool authorizer (validates the token from the `Authorization` header, scopes per method) |
| **API Gateway HTTP** | JWT authorizer with the user pool as issuer |
| **ALB** | `authenticate-cognito` listener rule action. The ALB handles the login redirect and passes the user claims to targets in `x-amzn-oidc-*` headers |
| **AppSync** | Cognito user pools auth mode (with group-based access in resolvers) |
| **Amplify** | Client libraries and UI components for sign-in, tokens, identity pools |

### Classic architectures

- **Web/mobile app + backend API**: user pool → access token → API Gateway Cognito/JWT authorizer → Lambda.
  The backend reads claims from the request context.
- **Mobile app uploading media**: user pool + identity pool → temporary credentials → S3 presigned or
  direct upload to `private/${identity-id}/`.
- **B2B SaaS with enterprise SSO**: user pool federated with each customer's SAML/OIDC IdP, plus a pre token
  generation trigger to add the tenant id.

## Hands-on

| Exercise | Skill |
|---|---|
| `cognito_1` | Create a pool and a public client, sign up, sign in, refresh |
| `cognito_2` | Decode and check JWT claims (exp, iss, token_use, client, groups) |
| `cognito_3` | Identity pool with a user pool provider, per-user S3 policy variable |

Optional lab: `labs/lab02-cognito-auth`.

## Summary

- User pool = authentication + JWTs. Identity pool = temporary AWS credentials. They are often combined.
- Public clients have no secret. SRP is the default secure flow. Groups appear in `cognito:groups`.
- Pre token generation adds claims. User migration moves users lazily. Post confirmation creates profiles.
- ID token = identity. Access token = API authorization (scopes). Refresh token = 30 days by default.
- `${cognito-identity.amazonaws.com:sub}` (the identity id) isolates each user's S3 prefix or DynamoDB rows.

## Check yourself

1. A mobile app must let users upload photos directly to S3, each user only into their own folder. Which Cognito components and policy?
2. Which token should a SPA send to an API Gateway method protected by OAuth scopes?
3. How do you add a `tenant_id` claim to every token?
4. Users of a legacy system must move to Cognito without resetting their passwords. How?
5. What is the difference between `sub` in an ID token and `${cognito-identity.amazonaws.com:sub}`?

<details><summary>Answers</summary>

1. A user pool for sign-in, an identity pool for temporary credentials, and an authenticated role
   allowing `s3:PutObject` on `arn:aws:s3:::bucket/private/${cognito-identity.amazonaws.com:sub}/*`.
2. The **access token** (it carries the scopes).
3. A **pre token generation** Lambda trigger (or a custom attribute mapped into the token).
4. A **user migration** Lambda trigger: it validates the credentials against the old system at first sign-in and creates the user.
5. The ID token `sub` is the user's id in the **user pool**. The policy variable is the **identity id** assigned by the **identity pool**.

</details>

## Further reading

- [Cognito developer guide](https://docs.aws.amazon.com/cognito/latest/developerguide/what-is-amazon-cognito.html)
- [Understanding user pool JSON web tokens](https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-tokens-with-identity-providers.html)
- [User pool Lambda triggers](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-identity-pools-working-with-aws-lambda-triggers.html)
- [Identity pools](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-identity.html)
- [aws-jwt-verify](https://github.com/awslabs/aws-jwt-verify)
