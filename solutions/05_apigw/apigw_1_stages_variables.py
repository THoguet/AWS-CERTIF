"""
Exercise apigw_1 — Stages, stage variables and Lambda aliases
=============================================================
Book: chapter 6, "Stages, deployments and stage variables" (book/src/ch06-api-gateway-appsync.md)
Exam: Domain 3 · Tasks 3.2 / 3.3 / 3.4 (API Gateway stages, using stage variables in Lambda functions)

One REST API, two stages:
  * the `dev` stage must invoke the `orders` function's alias `dev`,
  * the `prod` stage must invoke the alias `prod`.

Instead of two integrations, use ONE integration whose URI contains the
stage variable `${stageVariables.lambdaAlias}`. Each stage defines the
variable's value.

Exam trap: API Gateway needs permission to invoke EACH alias. That is a
resource-based policy on the function (lambda add-permission with
--qualifier). A missing permission gives a 500 "Invalid permissions on
Lambda function" at runtime.

Your task
---------
  * `build_api(apigw)`: REST API "orders-api" (REGIONAL), resource /orders,
    GET method (no auth), AWS_PROXY integration using LAMBDA_URI_TEMPLATE,
    stages dev and prod with lambdaAlias=dev / prod. Return the API id,
  * `grant_invoke(lambda_client, api_id, alias)`: allow API Gateway to
    call `orders:<alias>` for any stage, method GET, path /orders.
"""

REGION = "eu-west-3"
ACCOUNT = "123456789012"
FUNCTION_ARN = f"arn:aws:lambda:{REGION}:{ACCOUNT}:function:orders"
# The ${stageVariables.lambdaAlias} part must reach API Gateway literally.
LAMBDA_URI_TEMPLATE = (
    "arn:aws:apigateway:" + REGION + ":lambda:path/2015-03-31/functions/"
    "{function}:${{stageVariables.lambdaAlias}}/invocations"
)


def build_api(apigw) -> str:
    api_id = apigw.create_rest_api(name="orders-api", endpointConfiguration={"types": ["REGIONAL"]})["id"]
    root_id = next(r["id"] for r in apigw.get_resources(restApiId=api_id)["items"] if r["path"] == "/")
    resource_id = apigw.create_resource(restApiId=api_id, parentId=root_id, pathPart="orders")["id"]
    apigw.put_method(restApiId=api_id, resourceId=resource_id, httpMethod="GET", authorizationType="NONE")
    apigw.put_integration(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod="GET",
        type="AWS_PROXY",
        integrationHttpMethod="POST",
        uri=LAMBDA_URI_TEMPLATE.format(function=FUNCTION_ARN),
    )
    apigw.create_deployment(restApiId=api_id, stageName="dev", variables={"lambdaAlias": "dev"})
    apigw.create_deployment(restApiId=api_id, stageName="prod", variables={"lambdaAlias": "prod"})
    return api_id


def grant_invoke(lambda_client, api_id: str, alias: str) -> None:
    lambda_client.add_permission(
        FunctionName="orders",
        Qualifier=alias,
        StatementId=f"apigw-{alias}",
        Action="lambda:InvokeFunction",
        Principal="apigateway.amazonaws.com",
        SourceArn=f"arn:aws:execute-api:{REGION}:{ACCOUNT}:{api_id}/*/GET/orders",
    )


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run apigw_1
# =============================================================================
import json  # noqa: E402

import boto3  # noqa: E402
import pytest  # noqa: E402

from awslings.testing import lambda_zip  # noqa: E402


@pytest.fixture
def apigw(aws):
    return boto3.client("apigateway")


def test_integration_uses_stage_variable(apigw):
    api_id = build_api(apigw)
    resource = next(r for r in apigw.get_resources(restApiId=api_id)["items"] if r["path"] == "/orders")
    integration = apigw.get_integration(restApiId=api_id, resourceId=resource["id"], httpMethod="GET")
    assert integration["type"] == "AWS_PROXY"
    assert integration["httpMethod"] == "POST"
    assert integration["uri"].endswith("function:orders:${stageVariables.lambdaAlias}/invocations")


def test_two_stages_with_their_alias(apigw):
    api_id = build_api(apigw)
    assert apigw.get_stage(restApiId=api_id, stageName="dev")["variables"] == {"lambdaAlias": "dev"}
    assert apigw.get_stage(restApiId=api_id, stageName="prod")["variables"] == {"lambdaAlias": "prod"}


def test_permission_per_alias(apigw):
    api_id = build_api(apigw)
    iam = boto3.client("iam")
    role = iam.create_role(RoleName="r", AssumeRolePolicyDocument=json.dumps({"Version": "2012-10-17", "Statement": []}))["Role"]["Arn"]
    lam = boto3.client("lambda")
    lam.create_function(FunctionName="orders", Runtime="python3.12", Role=role, Handler="app.handler", Code={"ZipFile": lambda_zip()})
    version = lam.publish_version(FunctionName="orders")["Version"]
    lam.create_alias(FunctionName="orders", Name="prod", FunctionVersion=version)
    grant_invoke(lam, api_id, "prod")
    statement = json.loads(lam.get_policy(FunctionName="orders", Qualifier="prod")["Policy"])["Statement"][0]
    assert statement["Principal"] in ({"Service": "apigateway.amazonaws.com"}, "apigateway.amazonaws.com")
    assert statement["Action"] == "lambda:InvokeFunction"
    source = statement["Condition"]["ArnLike"]["AWS:SourceArn"]
    assert source == f"arn:aws:execute-api:eu-west-3:123456789012:{api_id}/*/GET/orders"
