# API Gateway and AppSync

> **In this chapter**
> - REST vs HTTP vs WebSocket APIs, endpoint types
> - Integrations (proxy vs non-proxy), mapping templates, request validation, mock integrations
> - Stages, deployments, stage variables, canary releases, custom domains
> - Throttling, usage plans and API keys, caching
> - Securing APIs: IAM, Cognito, Lambda and JWT authorizers, resource policies, CORS
> - Error codes, logging, metrics; AWS AppSync (GraphQL) in a nutshell
>
> **Exam weight**: Domain 1 Task 1.1 (creating and maintaining APIs), Domain 2 Task 2.1, Domain 3
> Tasks 3.2–3.4 (stages, environments), Domain 4 (errors, caching)
> · **Exercises**: `lambda_3`, `apigw_1`–`apigw_3` · **Quiz**: `uv run awslings quiz apigw`

## API types

| | **REST API** (v1) | **HTTP API** (v2) | **WebSocket API** |
|---|---|---|---|
| Use | Full-featured APIs | Simple, cheap, fast proxies to Lambda/HTTP | Two-way, persistent connections (chat, live dashboards) |
| Price / latency | Higher | **Cheaper** and lower latency | Per message + connection minutes |
| Auth | IAM, Cognito user pools, Lambda authorizers, resource policies | IAM, **JWT authorizers** (OIDC/OAuth2, Cognito), Lambda authorizers | IAM, Lambda authorizer on `$connect` |
| API keys + usage plans | ✅ | ❌ | ❌ |
| Request validation, VTL mapping templates | ✅ | ❌ (parameter mapping only) | ✅ (on routes) |
| Caching | ✅ | ❌ | ❌ |
| AWS WAF, private endpoints, canary on stage | ✅ | ❌ | ❌ |

> **Exam tip** — "Cheapest/simplest way to put a Lambda function behind HTTP with JWT auth" →
> **HTTP API**. "Need API keys, usage plans, caching, request validation or WAF" → **REST API**.

**Endpoint types** (REST): **edge-optimized** (requests routed through CloudFront edge locations,
for global clients, ACM certificate in **us-east-1**), **regional** (clients in the same Region, or
your own CloudFront distribution in front), **private** (reachable only from VPCs through an
interface VPC endpoint, with a resource policy).

## Integrations

| Type | What happens |
|---|---|
| **Lambda proxy** (`AWS_PROXY`) | The whole request (headers, path, query, body...) is the event. The function returns `{statusCode, headers, body}`. The most common choice |
| **Lambda custom** (`AWS`, non-proxy) | You map the request and response with **mapping templates** (VTL), and map errors to status codes |
| **HTTP proxy / HTTP custom** | Forward to an HTTP endpoint, raw or with mappings |
| **AWS service** | Call an AWS API directly, without Lambda: SQS `SendMessage`, DynamoDB `PutItem`, Step Functions `StartExecution`... |
| **Mock** | API Gateway returns a response itself. Used for testing, stubbing a backend not built yet, or CORS preflight |
| **VPC link** | Private integration with an NLB (REST) or ALB/NLB/Cloud Map (HTTP API) inside a VPC |

The request flow of a REST API:

```text
Client → Method request (auth, validation, API key) → Integration request (mapping template)
       → Backend → Integration response (status mapping, transformation) → Method response → Client
```

- **Request validation**: a request validator checks required parameters/headers and validates the
  body against a JSON Schema **model**, returning **400** without invoking the backend. That is cheaper and safer.
- **Overriding status codes / transforming responses** (non-proxy): integration responses map backend
  errors (regex on the error message) to HTTP codes, and VTL reshapes payloads.
- **Lambda proxy response contract** (exercise `lambda_3`):

```python
return {"statusCode": 200,                                     # an int
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "https://app.example.com"},
        "body": json.dumps(payload)}                           # a STRING
```

A malformed response (missing `statusCode`, a dict body...) gives **502 Bad Gateway**.
`queryStringParameters` and `pathParameters` are `null` when absent.

## Stages, deployments and stage variables

- A **deployment** is an immutable snapshot of the API configuration. A **stage** (`dev`, `test`,
  `prod`) points to a deployment and has its own URL
  (`https://{api-id}.execute-api.{region}.amazonaws.com/{stage}`), settings (throttling, caching, logs,
  X-Ray) and **stage variables**.
- **Changes are not live until you deploy** to a stage (REST APIs). HTTP APIs can auto-deploy.
- **Stage variables** are name/value pairs per stage, used in integration URIs, mapping templates
  and Lambda authorizers. The classic pattern: one integration pointing to
  `function:orders:${stageVariables.lambdaAlias}`, with `lambdaAlias=dev` on the dev stage and
  `prod` on prod (exercise `apigw_1`). Remember the **Lambda permission for each alias**.
- **Canary release** (REST stage setting): send a percentage of the stage's traffic to a new deployment,
  watch metrics, then promote or roll back.
- **Custom domain names** (`api.example.com`) with ACM certificates and **base path mappings**
  (`/v1` → stage prod of API A, `/v2` → API B).

> **Exam tip** — "Test a new API version without affecting production clients" → deploy it to a
> separate **stage** (or a canary on the prod stage). "Different backends per environment
> without changing the API definition" → **stage variables**.

## Throttling, usage plans and API keys

- Account-level default: **10,000 requests/s** steady with a **5,000-request burst** per Region
  (token bucket, soft limit), shared by all APIs. You can set lower limits per stage and per method.
- **Usage plans** set rate, burst and **quota** (per day/week/month) per client, identified by an
  **API key** (`x-api-key` header) on methods with `apiKeyRequired` (exercise `apigw_2`).
- Over the limit → **429 Too Many Requests**. Clients should retry with backoff.

> **Trap** — **API keys are not an authentication mechanism.** They are for metering and throttling.
> Use IAM, Cognito or Lambda authorizers to authenticate callers.

## Caching (REST APIs)

- Enabled **per stage** (cache size 0.5 GB to 237 GB, billed per hour). TTL default **300 s**, max **3,600 s**,
  0 disables. Per-method overrides are possible.
- The cache key is the method + resource path, plus the parameters/headers/query strings you declare as **cache keys**.
- Clients can bypass the cache with `Cache-Control: max-age=0` if allowed: require authorization
  (`execute-api:InvalidateCache`) to stop anyone from flushing your cache. You can also flush the whole stage cache.
- Metrics: `CacheHitCount`, `CacheMissCount`.

## Securing APIs

| Mechanism | How it works | Typical use |
|---|---|---|
| **IAM (SigV4)** | Callers sign requests with AWS credentials. `execute-api:Invoke` permissions | Internal services, other AWS accounts (with a resource policy), Cognito identity pool users |
| **Cognito user pool authorizer** (REST) / **JWT authorizer** (HTTP) | API Gateway validates the JWT (signature, expiry, audience/scopes). No code | Apps with users in a Cognito user pool or any OIDC provider |
| **Lambda authorizer** | Your function validates a token (TOKEN type: a header) or request data (REQUEST type: headers, query, stage variables, context) and returns an IAM policy + context. Results are **cached** per identity source (default TTL 300 s) | Custom/third-party tokens, API keys in a database, multi-tenant rules (exercise `apigw_3`) |
| **Resource policy** (REST) | Allow/deny by AWS account, IP range, VPC/VPC endpoint | Cross-account access, IP allow lists, private APIs |
| **Mutual TLS** | Clients present certificates on a custom domain | B2B / IoT |
| **AWS WAF** (REST) | Rate-based rules, SQL injection/XSS protection, geo-blocking | Public APIs |

Lambda authorizer rules: raise `Unauthorized` → **401**. Return a Deny policy → **403**. Because the
policy is cached per token, allow the **whole stage** (`.../stage/*/*`) rather than only the
method ARN, or other methods will be denied from cache.

### CORS

Browsers send a **preflight `OPTIONS`** request for cross-origin calls with non-simple methods/headers.
- REST API: "Enable CORS" creates an `OPTIONS` method (mock integration) returning the
  `Access-Control-Allow-*` headers. **With proxy integrations, your Lambda must also return
  `Access-Control-Allow-Origin` in its responses.**
- HTTP API: a built-in CORS configuration.

## Errors you must recognize

| Code | Typical cause in API Gateway |
|---|---|
| **400** | Request validation failed, malformed request |
| **401** | Unauthorized: missing/invalid token for a Cognito/Lambda authorizer |
| **403** | Access denied (resource policy, IAM, authorizer Deny, WAF). **Also "Missing Authentication Token" when calling a path or method that does not exist** |
| **429** | Throttling (account, stage, method, usage plan) or quota exceeded |
| **500** | Integration error, e.g. API Gateway lacks permission to invoke the Lambda function |
| **502** | Bad Gateway: malformed Lambda proxy response, or the Lambda function threw an error |
| **503** | Service unavailable |
| **504** | Integration timeout: the backend took longer than the integration timeout (default max **29 s** for REST, 30 s for HTTP APIs. Regional/private REST APIs can raise it with a quota increase) |

> **Exam tip** — Long-running backend work and 504s → make the API **asynchronous**: accept the
> request, put it in SQS / start a Step Functions execution, return **202**, and let the client poll or get notified.

## Logging and monitoring

- **Execution logs** (CloudWatch, ERROR or INFO level, optionally full request/response data. Beware
  of logging sensitive data) and **access logs** (one line per request, custom format with `$context` variables).
- Metrics: `Count`, `Latency` (full round trip seen by API Gateway), **`IntegrationLatency`** (backend only),
  `4XXError`, `5XXError`, `CacheHitCount`, `CacheMissCount`.
  `Latency − IntegrationLatency` = time spent in API Gateway itself (auth, mapping...).
- **X-Ray tracing** per stage.
- Import/export **OpenAPI** (Swagger) definitions. Generate client SDKs from a REST API.

## AWS AppSync (GraphQL)

AppSync is a managed **GraphQL** service (plus a pub/sub Events API):

- You define a **schema** (types, queries, mutations, subscriptions) and attach **resolvers** that
  read/write **data sources**: DynamoDB, Lambda, Aurora (RDS Data API), OpenSearch, HTTP endpoints, EventBridge.
  Resolvers are written in JavaScript (APPSYNC_JS) or VTL. **Pipeline resolvers** chain functions.
- **Real-time subscriptions** over WebSockets: clients get updates when a mutation runs.
- **Offline and sync** for mobile/web clients with the Amplify libraries (conflict detection and resolution).
- Auth modes (several at once): API key, IAM, Cognito user pools, OIDC, Lambda.
- Server-side caching. Merged APIs combine several source APIs.

> **Exam tip** — "Mobile/web app needs to fetch exactly the fields it needs from several sources,
> with **real-time updates** and **offline** support" → **AppSync**.

## Choosing a front door

| Need | Choose |
|---|---|
| Full-featured public REST API (keys, quotas, caching, validation, WAF) | API Gateway **REST API** |
| Low-cost HTTP proxy to Lambda with JWT auth | API Gateway **HTTP API** |
| Bidirectional real-time messaging | API Gateway **WebSocket API** (or AppSync subscriptions) |
| GraphQL, flexible queries, subscriptions, offline | **AppSync** |
| HTTP to containers/instances with path routing | **ALB** (it can also target Lambda) |
| One function, one HTTPS endpoint, minimal setup | **Lambda function URL** |

## Hands-on

| Exercise | Skill |
|---|---|
| `lambda_3` | The Lambda proxy response contract, null query strings, CORS headers |
| `apigw_1` | One integration + stage variables → Lambda aliases, per-alias permissions |
| `apigw_2` | API keys and usage plans (rate, burst, quota) |
| `apigw_3` | A TOKEN Lambda authorizer: 401 vs 403, stage-wide policy, context |

Optional lab: `labs/lab01-serverless-api` and `labs/lab02-cognito-auth`.

## Summary

- REST API = full features. HTTP API = cheaper/faster with JWT auth. WebSocket = two-way. AppSync = GraphQL with subscriptions and offline.
- Proxy integration: the Lambda function returns `{statusCode, headers, body-string}`. A bad shape gives 502.
- Deploy to stages. Stage variables (+ Lambda aliases) separate environments. Canary releases on REST stages.
- Throttling gives 429. Usage plans + API keys meter clients (not auth). Caching on REST stages (TTL 300 s default, max 3,600 s).
- Auth: IAM, Cognito/JWT authorizers, Lambda authorizers (cached), resource policies, WAF. CORS headers come from the API **and** from proxy Lambdas.

## Check yourself

1. Clients get **502** right after a developer refactored the Lambda function behind a proxy integration. What is the likely cause?
2. How do you route the `dev` stage to a Lambda alias `dev` and the `prod` stage to alias `prod` with a single integration?
3. A partner calls the API with a valid API key but is rejected with 429 after 1,000 calls today. Why?
4. Calls to `GET /orders` work but `GET /order` returns 403 "Missing Authentication Token". Why?
5. Which authorizer validates Cognito user pool tokens without any custom code (REST API)?

<details><summary>Answers</summary>

1. The function no longer returns the proxy response format (e.g. body not a string, missing statusCode), or it throws an error.
2. Use `${stageVariables.lambdaAlias}` in the integration URI, set the variable per stage, and add a
   Lambda permission for API Gateway on each alias.
3. The usage plan's daily quota (1,000 requests/day) is exhausted.
4. The resource `/order` does not exist. REST APIs answer 403 "Missing Authentication Token" for unknown paths/methods.
5. The Cognito user pool authorizer (`COGNITO_USER_POOLS`).

</details>

## Further reading

- [Choosing between REST APIs and HTTP APIs](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-vs-rest.html)
- [API Gateway quotas](https://docs.aws.amazon.com/apigateway/latest/developerguide/limits.html)
- [Set up Lambda proxy integrations](https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html)
- [Use API Gateway Lambda authorizers](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-use-lambda-authorizer.html)
- [AWS AppSync developer guide](https://docs.aws.amazon.com/appsync/latest/devguide/what-is-appsync.html)
