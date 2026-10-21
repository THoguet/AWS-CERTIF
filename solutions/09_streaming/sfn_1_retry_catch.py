"""
Exercise sfn_1 — Step Functions: retries, catchers and choices
==============================================================
Book: chapter 10, "AWS Step Functions" (book/src/ch10-streaming-orchestration.md)
Exam: Domain 1 · Task 1.1 (orchestration, fault-tolerant design patterns)

Write the Amazon States Language (ASL) definition of the order workflow:

    ValidateOrder ─► ChargeCard ─► IsBigOrder ─┬─(amount >= 1000)─► ManualReview ─► Ship
                         │                     └─(otherwise)───────────────────────► Ship
                         └─(any error after retries)─► NotifyFailure ─► Failed

  * ValidateOrder, ChargeCard, ManualReview, Ship, NotifyFailure: Task
    states invoking the Lambda ARNs given in FN,
  * ChargeCard retries Lambda.ServiceException, Lambda.TooManyRequestsException
    and States.Timeout: first retry after 2 s, 3 attempts max, backoff rate 2.0,
  * if ChargeCard still fails, catch ANY error (States.ALL), keep the input
    and put the error under "$.error", then go to NotifyFailure,
  * Ship ends the execution successfully. NotifyFailure goes to "Failed",
    a Fail state with Error "PaymentFailed".

Remember: every non-terminal state needs "Next" (or "End": true). Retry
handles transient errors first. Catch takes over when retries are exhausted.
"""

FN = {name: f"arn:aws:lambda:eu-west-3:123456789012:function:{name}" for name in ("validate", "charge", "review", "ship", "notify")}

DEFINITION = {
    "Comment": "Order workflow",
    "StartAt": "ValidateOrder",
    "States": {
        "ValidateOrder": {"Type": "Task", "Resource": FN["validate"], "Next": "ChargeCard"},
        "ChargeCard": {
            "Type": "Task",
            "Resource": FN["charge"],
            "Retry": [
                {
                    "ErrorEquals": ["Lambda.ServiceException", "Lambda.TooManyRequestsException", "States.Timeout"],
                    "IntervalSeconds": 2,
                    "MaxAttempts": 3,
                    "BackoffRate": 2.0,
                }
            ],
            "Catch": [{"ErrorEquals": ["States.ALL"], "ResultPath": "$.error", "Next": "NotifyFailure"}],
            "Next": "IsBigOrder",
        },
        "IsBigOrder": {
            "Type": "Choice",
            "Choices": [{"Variable": "$.amount", "NumericGreaterThanEquals": 1000, "Next": "ManualReview"}],
            "Default": "Ship",
        },
        "ManualReview": {"Type": "Task", "Resource": FN["review"], "Next": "Ship"},
        "Ship": {"Type": "Task", "Resource": FN["ship"], "End": True},
        "NotifyFailure": {"Type": "Task", "Resource": FN["notify"], "Next": "Failed"},
        "Failed": {"Type": "Fail", "Error": "PaymentFailed", "Cause": "Card could not be charged"},
    },
}


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run sfn_1
# =============================================================================
import json  # noqa: E402

import boto3  # noqa: E402

STATES = DEFINITION.get("States", {})


def test_structure_is_valid():
    assert DEFINITION["StartAt"] in STATES
    for name, state in STATES.items():
        targets = [state.get("Next"), state.get("Default")]
        targets += [c.get("Next") for c in state.get("Choices", [])] + [c.get("Next") for c in state.get("Catch", [])]
        for target in filter(None, targets):
            assert target in STATES, f"{name} points to unknown state {target}"
        if state["Type"] not in ("Choice", "Succeed", "Fail"):
            assert "Next" in state or state.get("End") is True, f"{name} needs Next or End"
    assert {"ValidateOrder", "ChargeCard", "IsBigOrder", "ManualReview", "Ship", "NotifyFailure", "Failed"} <= set(STATES)


def test_retry_policy():
    retry = STATES["ChargeCard"]["Retry"][0]
    assert set(retry["ErrorEquals"]) == {"Lambda.ServiceException", "Lambda.TooManyRequestsException", "States.Timeout"}
    assert (retry["IntervalSeconds"], retry["MaxAttempts"], retry["BackoffRate"]) == (2, 3, 2.0)


def test_catch_keeps_input():
    catch = STATES["ChargeCard"]["Catch"][0]
    assert catch == {"ErrorEquals": ["States.ALL"], "ResultPath": "$.error", "Next": "NotifyFailure"}


def test_choice_and_terminal_states():
    choice = STATES["IsBigOrder"]
    assert choice["Type"] == "Choice"
    rule = choice["Choices"][0]
    assert rule["Variable"] == "$.amount" and rule["NumericGreaterThanEquals"] == 1000 and rule["Next"] == "ManualReview"
    assert choice["Default"] == "Ship"
    assert STATES["Ship"].get("End") is True
    assert STATES["Failed"]["Type"] == "Fail" and STATES["Failed"]["Error"] == "PaymentFailed"
    assert STATES["NotifyFailure"]["Next"] == "Failed"


def test_state_machine_can_be_created(aws):
    sfn = boto3.client("stepfunctions")
    arn = sfn.create_state_machine(name="orders", definition=json.dumps(DEFINITION), roleArn="arn:aws:iam::123456789012:role/sfn")["stateMachineArn"]
    assert json.loads(sfn.describe_state_machine(stateMachineArn=arn)["definition"]) == DEFINITION
