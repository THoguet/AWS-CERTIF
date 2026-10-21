"""
Exercise cfn_2 — Mappings, conditions and intrinsic functions
=============================================================
Book: chapter 15, "Intrinsic functions, mappings and conditions"
Exam: Domain 3 · Tasks 3.3 / 3.4 (deploying the same template to several environments)

ONE template, two environments:
  * Mappings EnvSettings: dev → Retention 345600 (4 days),
                          prod → Retention 1209600 (14 days),
  * Condition IsProd (Env == prod),
  * `JobsQueue`: QueueName "jobs-<Env>-<region>" (use !Join and the
    AWS::Region pseudo parameter), MessageRetentionPeriod from the
    mapping, VisibilityTimeout 300 in prod and 60 in dev (!If),
  * `AlertsTopic`: an SNS topic created ONLY in prod,
  * Outputs: `JobsQueueName` (!GetAtt JobsQueue.QueueName) and
    `AlertsTopicArn` (only in prod).
"""

# I AM NOT DONE

TEMPLATE = """
AWSTemplateFormatVersion: "2010-09-09"
Parameters:
  Env:
    Type: String
    AllowedValues: [dev, prod]
# TODO: Mappings (EnvSettings) and Conditions (IsProd)
Resources:
  JobsQueue:
    Type: AWS::SQS::Queue
    Properties:
      QueueName: jobs                # TODO: jobs-<Env>-<region>
      MessageRetentionPeriod: 345600 # TODO: from the mapping
      VisibilityTimeout: 60          # TODO: 300 in prod
  AlertsTopic:
    Type: AWS::SNS::Topic            # TODO: prod only
Outputs:
  JobsQueueName:
    Value: !GetAtt JobsQueue.QueueName
  AlertsTopicArn:
    Value: !Ref AlertsTopic          # TODO: prod only
"""


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run cfn_2
# =============================================================================
import boto3  # noqa: E402
import pytest  # noqa: E402

from awslings.testing import load_cfn  # noqa: E402


def _deploy(env):
    cfn = boto3.client("cloudformation")
    cfn.create_stack(StackName=f"jobs-{env}", TemplateBody=TEMPLATE, Parameters=[{"ParameterKey": "Env", "ParameterValue": env}])
    stack = cfn.describe_stacks(StackName=f"jobs-{env}")["Stacks"][0]
    outputs = {o["OutputKey"]: o["OutputValue"] for o in stack.get("Outputs", [])}
    resources = {r["LogicalResourceId"] for r in cfn.list_stack_resources(StackName=f"jobs-{env}")["StackResourceSummaries"]}
    return outputs, resources


def _queue_attrs(name):
    sqs = boto3.client("sqs")
    url = sqs.get_queue_url(QueueName=name)["QueueUrl"]
    return sqs.get_queue_attributes(QueueUrl=url, AttributeNames=["All"])["Attributes"]


def test_template_structure():
    template = load_cfn(TEMPLATE)
    assert template["Conditions"]["IsProd"] == {"Fn::Equals": [{"Ref": "Env"}, "prod"]}
    assert template["Resources"]["AlertsTopic"].get("Condition") == "IsProd"


@pytest.mark.parametrize(
    "env, retention, visibility",
    [("dev", "345600", "60"), ("prod", "1209600", "300")],
)
def test_queue_per_environment(aws, env, retention, visibility):
    outputs, _ = _deploy(env)
    assert outputs["JobsQueueName"] == f"jobs-{env}-eu-west-3"
    attrs = _queue_attrs(f"jobs-{env}-eu-west-3")
    assert attrs["MessageRetentionPeriod"] == retention
    assert attrs["VisibilityTimeout"] == visibility


def test_topic_only_in_prod(aws):
    dev_outputs, dev_resources = _deploy("dev")
    prod_outputs, prod_resources = _deploy("prod")
    assert "AlertsTopic" not in dev_resources and "AlertsTopicArn" not in dev_outputs
    assert "AlertsTopic" in prod_resources and prod_outputs["AlertsTopicArn"].startswith("arn:aws:sns:")
