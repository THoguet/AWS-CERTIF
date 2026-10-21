"""
Exercise cicd_2 — CodeDeploy AppSpec files and lifecycle hooks
==============================================================
Book: chapter 17, "CodeDeploy" (book/src/ch17-cicd.md)
Exam: Domain 3 · Task 3.4 (deployment strategies), Domain 4 · Task 4.1 (troubleshooting deployment failures)

The order of lifecycle events is a favourite exam topic, and so is
knowing which events you can hook scripts/functions into.

Your task
---------
  1. EC2_IN_PLACE: the lifecycle events of an in-place EC2/on-premises
     deployment WITHOUT a load balancer, in order,
  2. EC2_IN_PLACE_WITH_LB: the same WITH a load balancer (13 events in total),
  3. ECS_BLUE_GREEN and LAMBDA: the events for ECS and Lambda deployments,
  4. EC2_SCRIPTABLE: the EC2 events in which YOU can run scripts (the
     others are reserved for the CodeDeploy agent),
  5. `lambda_appspec(...)`: the AppSpec (as a dict) for a Lambda
     deployment shifting alias `alias` from `current` to `target`, with
     validation functions for BeforeAllowTraffic and AfterAllowTraffic.
"""

# I AM NOT DONE

EC2_IN_PLACE = ["DownloadBundle", "Install", "ApplicationStart"]  # TODO: complete and order
EC2_IN_PLACE_WITH_LB = []  # TODO
ECS_BLUE_GREEN = []  # TODO
LAMBDA = []  # TODO
EC2_SCRIPTABLE = set()  # TODO


def lambda_appspec(function_name: str, alias: str, current: str, target: str, before_hook: str, after_hook: str) -> dict:
    raise NotImplementedError  # TODO


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run cicd_2
# =============================================================================


def test_ec2_in_place():
    assert EC2_IN_PLACE == ["ApplicationStop", "DownloadBundle", "BeforeInstall", "Install", "AfterInstall", "ApplicationStart", "ValidateService"]


def test_ec2_with_load_balancer():
    assert EC2_IN_PLACE_WITH_LB[:3] == ["BeforeBlockTraffic", "BlockTraffic", "AfterBlockTraffic"]
    assert EC2_IN_PLACE_WITH_LB[3:10] == EC2_IN_PLACE
    assert EC2_IN_PLACE_WITH_LB[10:] == ["BeforeAllowTraffic", "AllowTraffic", "AfterAllowTraffic"]


def test_ecs_and_lambda():
    assert ECS_BLUE_GREEN == [
        "BeforeInstall", "Install", "AfterInstall", "AllowTestTraffic", "AfterAllowTestTraffic",
        "BeforeAllowTraffic", "AllowTraffic", "AfterAllowTraffic",
    ]
    assert LAMBDA == ["BeforeAllowTraffic", "AllowTraffic", "AfterAllowTraffic"]


def test_scriptable_hooks():
    reserved = {"DownloadBundle", "Install", "BlockTraffic", "AllowTraffic"}
    assert EC2_SCRIPTABLE == set(EC2_IN_PLACE_WITH_LB) - reserved


def test_lambda_appspec():
    spec = lambda_appspec("checkout", "live", "3", "4", "PreTrafficCheck", "PostTrafficCheck")
    props = spec["Resources"][0]["checkout"]["Properties"]
    assert spec["Resources"][0]["checkout"]["Type"] == "AWS::Lambda::Function"
    assert props == {"Name": "checkout", "Alias": "live", "CurrentVersion": "3", "TargetVersion": "4"}
    assert spec["Hooks"] == [{"BeforeAllowTraffic": "PreTrafficCheck"}, {"AfterAllowTraffic": "PostTrafficCheck"}]
