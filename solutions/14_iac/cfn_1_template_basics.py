"""
Exercise cfn_1 — A first CloudFormation template
================================================
Book: chapter 15, "CloudFormation" (book/src/ch15-cloudformation-cdk.md)
Exam: Domain 3 · Tasks 3.3 / 3.4 (implementing and updating IaC templates)

Complete TEMPLATE so that a stack creates:
  * Parameter `Env` (String, AllowedValues dev/prod, Default dev),
  * `OrdersTable`: DynamoDB table named "orders-<Env>", on-demand,
    partition key `pk` (String),
  * `OrdersDLQ`: SQS queue keeping messages 14 days (1209600 s),
  * `OrdersQueue`: SQS queue with a 180 s visibility timeout and a redrive
    policy sending messages to OrdersDLQ after 5 receives,
  * Outputs: `OrdersQueueUrl` (exported as "<stack name>-OrdersQueueUrl")
    and `OrdersTableName`.

Reminders: !Ref returns a resource's "main" identifier (table name, queue
URL, bucket name...), !GetAtt returns other attributes (Arn...), and
!Sub interpolates ${Param}, ${Resource} and pseudo parameters such as
${AWS::StackName} / ${AWS::Region} / ${AWS::AccountId}.
"""

TEMPLATE = """
AWSTemplateFormatVersion: "2010-09-09"
Description: Orders backend
Parameters:
  Env:
    Type: String
    AllowedValues: [dev, prod]
    Default: dev
Resources:
  OrdersTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: !Sub "orders-${Env}"
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: pk
          AttributeType: S
      KeySchema:
        - AttributeName: pk
          KeyType: HASH
  OrdersDLQ:
    Type: AWS::SQS::Queue
    Properties:
      MessageRetentionPeriod: 1209600
  OrdersQueue:
    Type: AWS::SQS::Queue
    Properties:
      VisibilityTimeout: 180
      RedrivePolicy:
        deadLetterTargetArn: !GetAtt OrdersDLQ.Arn
        maxReceiveCount: 5
Outputs:
  OrdersQueueUrl:
    Value: !Ref OrdersQueue
    Export:
      Name: !Sub "${AWS::StackName}-OrdersQueueUrl"
  OrdersTableName:
    Value: !Ref OrdersTable
"""


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run cfn_1
# =============================================================================
import json  # noqa: E402

import boto3  # noqa: E402
import pytest  # noqa: E402

from awslings.testing import load_cfn  # noqa: E402


def test_template_parses():
    template = load_cfn(TEMPLATE)
    assert set(template["Resources"]) == {"OrdersTable", "OrdersDLQ", "OrdersQueue"}
    assert template["Parameters"]["Env"]["AllowedValues"] == ["dev", "prod"]


@pytest.fixture
def stack(aws):
    cfn = boto3.client("cloudformation")
    cfn.create_stack(StackName="orders-dev", TemplateBody=TEMPLATE, Parameters=[{"ParameterKey": "Env", "ParameterValue": "dev"}])
    return cfn, cfn.describe_stacks(StackName="orders-dev")["Stacks"][0]


def test_stack_outputs_and_export(stack):
    cfn, description = stack
    assert description["StackStatus"] == "CREATE_COMPLETE"
    outputs = {o["OutputKey"]: o["OutputValue"] for o in description["Outputs"]}
    assert outputs["OrdersTableName"] == "orders-dev"
    assert "orders-dev-OrdersQueueUrl" in [e["Name"] for e in cfn.list_exports()["Exports"]]


def test_table_is_on_demand(stack):
    table = boto3.client("dynamodb").describe_table(TableName="orders-dev")["Table"]
    assert table["BillingModeSummary"]["BillingMode"] == "PAY_PER_REQUEST"


def test_queue_redrive(stack):
    _, description = stack
    sqs = boto3.client("sqs")
    url = {o["OutputKey"]: o["OutputValue"] for o in description["Outputs"]}["OrdersQueueUrl"]
    attrs = sqs.get_queue_attributes(QueueUrl=url, AttributeNames=["All"])["Attributes"]
    policy = json.loads(attrs["RedrivePolicy"])
    assert int(policy["maxReceiveCount"]) == 5
    dlq_url = sqs.get_queue_url(QueueName=policy["deadLetterTargetArn"].split(":")[-1])["QueueUrl"]
    dlq = sqs.get_queue_attributes(QueueUrl=dlq_url, AttributeNames=["MessageRetentionPeriod"])["Attributes"]
    assert dlq["MessageRetentionPeriod"] == "1209600"
