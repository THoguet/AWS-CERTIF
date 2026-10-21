"""
Exercise cicd_4 — A CodePipeline with an approval gate
======================================================
Book: chapter 17, "CodePipeline" (book/src/ch17-cicd.md)
Exam: Domain 3 · Task 3.4 (manual and automated approvals in CodePipeline, orchestrated workflows)

Build the pipeline definition (the structure you would put in
CloudFormation or pass to CreatePipeline):

  Source   — CodeCommit repository "shop-app", branch "main" → artifact SourceOutput
  Build    — CodeBuild project "shop-build", SourceOutput → BuildOutput
  Approve  — Manual approval, notification to APPROVAL_TOPIC_ARN,
             CustomData "Review the change set before production"
  Deploy   — CloudFormation, stack "shop-prod", change set "shop-prod-changes":
             1) CHANGE_SET_REPLACE with TemplatePath "BuildOutput::packaged.yaml",
                Capabilities "CAPABILITY_IAM,CAPABILITY_AUTO_EXPAND", RoleArn CFN_ROLE_ARN
             2) CHANGE_SET_EXECUTE (runOrder 2)

Artifacts flow between stages through the S3 artifact store.
"""

PIPELINE_ROLE_ARN = "arn:aws:iam::123456789012:role/shop-pipeline"
CFN_ROLE_ARN = "arn:aws:iam::123456789012:role/shop-cloudformation"
APPROVAL_TOPIC_ARN = "arn:aws:sns:eu-west-3:123456789012:prod-approvals"


def _action(name, category, provider, configuration, inputs=(), outputs=(), run_order=1):
    return {
        "name": name,
        "actionTypeId": {"category": category, "owner": "AWS", "provider": provider, "version": "1"},
        "configuration": configuration,
        "inputArtifacts": [{"name": i} for i in inputs],
        "outputArtifacts": [{"name": o} for o in outputs],
        "runOrder": run_order,
    }


def pipeline_definition() -> dict:
    stages = [
        {"name": "Source", "actions": [_action("Source", "Source", "CodeCommit", {"RepositoryName": "shop-app", "BranchName": "main"}, outputs=["SourceOutput"])]},
        {"name": "Build", "actions": [_action("Build", "Build", "CodeBuild", {"ProjectName": "shop-build"}, inputs=["SourceOutput"], outputs=["BuildOutput"])]},
        {
            "name": "Approve",
            "actions": [
                _action("ProductionApproval", "Approval", "Manual", {"NotificationArn": APPROVAL_TOPIC_ARN, "CustomData": "Review the change set before production"})
            ],
        },
        {
            "name": "Deploy",
            "actions": [
                _action(
                    "CreateChangeSet",
                    "Deploy",
                    "CloudFormation",
                    {
                        "ActionMode": "CHANGE_SET_REPLACE",
                        "StackName": "shop-prod",
                        "ChangeSetName": "shop-prod-changes",
                        "TemplatePath": "BuildOutput::packaged.yaml",
                        "Capabilities": "CAPABILITY_IAM,CAPABILITY_AUTO_EXPAND",
                        "RoleArn": CFN_ROLE_ARN,
                    },
                    inputs=["BuildOutput"],
                    run_order=1,
                ),
                _action(
                    "ExecuteChangeSet",
                    "Deploy",
                    "CloudFormation",
                    {"ActionMode": "CHANGE_SET_EXECUTE", "StackName": "shop-prod", "ChangeSetName": "shop-prod-changes"},
                    run_order=2,
                ),
            ],
        },
    ]
    return {
        "name": "shop-pipeline",
        "roleArn": PIPELINE_ROLE_ARN,
        "artifactStore": {"type": "S3", "location": "shop-pipeline-artifacts"},
        "stages": stages,
    }


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run cicd_4
# =============================================================================
import json  # noqa: E402

import boto3  # noqa: E402


def _stage(definition, name):
    return next(s for s in definition["stages"] if s["name"] == name)


def test_stage_order():
    assert [s["name"] for s in pipeline_definition()["stages"]] == ["Source", "Build", "Approve", "Deploy"]


def test_manual_approval():
    action = _stage(pipeline_definition(), "Approve")["actions"][0]
    assert action["actionTypeId"]["category"] == "Approval" and action["actionTypeId"]["provider"] == "Manual"
    assert action["configuration"]["NotificationArn"] == APPROVAL_TOPIC_ARN
    assert action["configuration"]["CustomData"]


def test_change_set_deploy():
    create, execute = sorted(_stage(pipeline_definition(), "Deploy")["actions"], key=lambda a: a["runOrder"])
    assert (create["runOrder"], execute["runOrder"]) == (1, 2)
    assert create["configuration"]["ActionMode"] == "CHANGE_SET_REPLACE"
    assert create["configuration"]["TemplatePath"] == "BuildOutput::packaged.yaml"
    assert create["configuration"]["Capabilities"] == "CAPABILITY_IAM,CAPABILITY_AUTO_EXPAND"
    assert create["configuration"]["RoleArn"] == CFN_ROLE_ARN
    assert create["inputArtifacts"] == [{"name": "BuildOutput"}]
    assert execute["configuration"]["ActionMode"] == "CHANGE_SET_EXECUTE"
    assert execute["configuration"]["ChangeSetName"] == create["configuration"]["ChangeSetName"]
    assert execute["configuration"]["StackName"] == create["configuration"]["StackName"] == "shop-prod"


def test_pipeline_can_be_created(aws):
    trust = {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Principal": {"Service": "codepipeline.amazonaws.com"}, "Action": "sts:AssumeRole"}]}
    boto3.client("iam").create_role(RoleName="shop-pipeline", AssumeRolePolicyDocument=json.dumps(trust))
    client = boto3.client("codepipeline")
    client.create_pipeline(pipeline=pipeline_definition())
    assert [s["name"] for s in client.get_pipeline(name="shop-pipeline")["pipeline"]["stages"]] == ["Source", "Build", "Approve", "Deploy"]
