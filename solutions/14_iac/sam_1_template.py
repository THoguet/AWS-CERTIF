"""
Exercise sam_1 — A SAM template with a canary deployment
========================================================
Book: chapter 16, "AWS SAM" (book/src/ch16-sam-serverless-deploy.md)
Exam: Domain 3 · Tasks 3.1 / 3.3 / 3.4 (SAM templates, deployment strategies)

AWS SAM is a CloudFormation TRANSFORM: short serverless resource types
(AWS::Serverless::Function, ::Api, ::SimpleTable...) expand into full
CloudFormation at deploy time. `sam build`, `sam local invoke`,
`sam deploy --guided`, `sam sync` are the CLI side.

Complete TEMPLATE:
  * the SAM transform,
  * Globals for all functions: python3.12, Timeout 10, X-Ray Tracing
    Active, Architectures [arm64],
  * `OrdersFunction` (Handler app.handler, CodeUri src/):
      - Policies: the SAM policy template DynamoDBCrudPolicy on OrdersTable,
      - Environment variable TABLE_NAME = !Ref OrdersTable,
      - Events: Api GET /orders, and SQS from OrdersQueue (batch 10,
        partial batch responses),
      - AutoPublishAlias "live" + DeploymentPreference
        Canary10Percent5Minutes rolled back by ErrorsAlarm,
  * `OrdersTable`: AWS::Serverless::SimpleTable, `OrdersQueue`: AWS::SQS::Queue,
  * `ErrorsAlarm` is given.
"""

TEMPLATE = """
AWSTemplateFormatVersion: "2010-09-09"
Transform: AWS::Serverless-2016-10-31
Description: Orders service

Globals:
  Function:
    Runtime: python3.12
    Timeout: 10
    Tracing: Active
    Architectures: [arm64]

Resources:
  OrdersFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: app.handler
      CodeUri: src/
      AutoPublishAlias: live
      DeploymentPreference:
        Type: Canary10Percent5Minutes
        Alarms:
          - !Ref ErrorsAlarm
      Policies:
        - DynamoDBCrudPolicy:
            TableName: !Ref OrdersTable
      Environment:
        Variables:
          TABLE_NAME: !Ref OrdersTable
      Events:
        Api:
          Type: Api
          Properties:
            Path: /orders
            Method: get
        Queue:
          Type: SQS
          Properties:
            Queue: !GetAtt OrdersQueue.Arn
            BatchSize: 10
            FunctionResponseTypes:
              - ReportBatchItemFailures

  OrdersTable:
    Type: AWS::Serverless::SimpleTable

  OrdersQueue:
    Type: AWS::SQS::Queue
    Properties:
      VisibilityTimeout: 60

  ErrorsAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      Namespace: AWS/Lambda
      MetricName: Errors
      Dimensions:
        - Name: FunctionName
          Value: !Ref OrdersFunction
      Statistic: Sum
      Period: 60
      EvaluationPeriods: 1
      Threshold: 1
      ComparisonOperator: GreaterThanOrEqualToThreshold
"""


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run sam_1
# =============================================================================
import pytest  # noqa: E402

from awslings.testing import load_cfn  # noqa: E402

T = load_cfn(TEMPLATE)
FN = T["Resources"]["OrdersFunction"]["Properties"]


def test_transform_and_globals():
    assert T.get("Transform") == "AWS::Serverless-2016-10-31"
    globals_ = T["Globals"]["Function"]
    assert globals_["Runtime"] == "python3.12"
    assert globals_["Timeout"] == 10
    assert globals_["Tracing"] == "Active"
    assert globals_["Architectures"] == ["arm64"]


def test_permissions_and_environment():
    assert FN["Policies"] == [{"DynamoDBCrudPolicy": {"TableName": {"Ref": "OrdersTable"}}}]
    assert FN["Environment"]["Variables"]["TABLE_NAME"] == {"Ref": "OrdersTable"}


def test_events():
    events = FN["Events"]
    assert events["Api"]["Type"] == "Api" and events["Api"]["Properties"] == {"Path": "/orders", "Method": "get"}
    queue = events["Queue"]
    assert queue["Type"] == "SQS"
    assert queue["Properties"]["Queue"] == {"Fn::GetAtt": ["OrdersQueue", "Arn"]}
    assert queue["Properties"]["BatchSize"] == 10
    assert queue["Properties"]["FunctionResponseTypes"] == ["ReportBatchItemFailures"]


def test_canary_deployment():
    assert FN["AutoPublishAlias"] == "live"
    assert FN["DeploymentPreference"]["Type"] == "Canary10Percent5Minutes"
    assert FN["DeploymentPreference"]["Alarms"] == [{"Ref": "ErrorsAlarm"}]


def test_cfn_lint_has_no_errors():
    api = pytest.importorskip("cfnlint.api")
    errors = [m for m in api.lint(TEMPLATE, regions=["eu-west-3"]) if str(m.rule.id).startswith("E")]
    assert errors == [], "\n".join(str(e) for e in errors)
