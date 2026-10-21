"""
Exercise apigw_2 — API keys and usage plans
===========================================
Book: chapter 6, "Throttling, usage plans and API keys" (book/src/ch06-api-gateway-appsync.md)
Exam: Domain 1 · Task 1.1, Domain 4 · Task 4.3

You sell API access to partners. The "basic" tier is limited to
10 requests/second (bursts up to 20) and 1,000 requests per day.

  * a USAGE PLAN holds throttling (rate + burst) and quota (per day/week/month)
    limits, and lists the API stages it applies to,
  * an API KEY identifies a client and is attached to a usage plan,
  * methods must require the key (`apiKeyRequired`). Clients send it in
    the `x-api-key` header,
  * API keys are for metering and throttling, NOT for authorization. Use
    IAM, Cognito or a Lambda authorizer to authenticate callers,
  * when limits are exceeded, callers get 429 Too Many Requests.

Your task
---------
Implement `onboard_partner(apigw, api_id, stage, partner)`:
  1. create an enabled API key named `partner`,
  2. create the usage plan "basic-<partner>" for the stage with the limits above,
  3. attach the key to the plan,
  4. return the key id.
"""


def onboard_partner(apigw, api_id: str, stage: str, partner: str) -> str:
    key_id = apigw.create_api_key(name=partner, enabled=True)["id"]
    plan_id = apigw.create_usage_plan(
        name=f"basic-{partner}",
        apiStages=[{"apiId": api_id, "stage": stage}],
        throttle={"rateLimit": 10.0, "burstLimit": 20},
        quota={"limit": 1000, "period": "DAY"},
    )["id"]
    apigw.create_usage_plan_key(usagePlanId=plan_id, keyId=key_id, keyType="API_KEY")
    return key_id


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run apigw_2
# =============================================================================
import boto3  # noqa: E402
import pytest  # noqa: E402


@pytest.fixture
def api(aws):
    apigw = boto3.client("apigateway")
    api_id = apigw.create_rest_api(name="weather")["id"]
    root = apigw.get_resources(restApiId=api_id)["items"][0]["id"]
    apigw.put_method(restApiId=api_id, resourceId=root, httpMethod="GET", authorizationType="NONE", apiKeyRequired=True)
    apigw.put_integration(restApiId=api_id, resourceId=root, httpMethod="GET", type="MOCK")
    apigw.create_deployment(restApiId=api_id, stageName="v1")
    return apigw, api_id


def test_usage_plan_limits(api):
    apigw, api_id = api
    onboard_partner(apigw, api_id, "v1", "acme")
    plans = [p for p in apigw.get_usage_plans()["items"] if p["name"] == "basic-acme"]
    assert len(plans) == 1
    plan = plans[0]
    assert plan["throttle"] == {"rateLimit": 10.0, "burstLimit": 20}
    assert plan["quota"]["limit"] == 1000 and plan["quota"]["period"] == "DAY"
    assert plan["apiStages"] == [{"apiId": api_id, "stage": "v1"}]


def test_key_is_attached(api):
    apigw, api_id = api
    key_id = onboard_partner(apigw, api_id, "v1", "acme")
    key = apigw.get_api_key(apiKey=key_id)
    assert key["name"] == "acme" and key["enabled"] is True
    plan = next(p for p in apigw.get_usage_plans()["items"] if p["name"] == "basic-acme")
    assert [k["id"] for k in apigw.get_usage_plan_keys(usagePlanId=plan["id"])["items"]] == [key_id]
