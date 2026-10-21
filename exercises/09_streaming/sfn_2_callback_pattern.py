"""
Exercise sfn_2 — Wait for a human: the callback (task token) pattern
====================================================================
Book: chapter 10, "Service integration patterns" (book/src/ch10-streaming-orchestration.md)
Exam: Domain 1 · Task 1.1 (orchestration, synchronous vs asynchronous patterns)

Step Functions can call services in three ways:
  * Request/Response (default) — call the service and move on,
  * Run a Job (.sync)          — wait until the job (Batch, ECS, Glue...) finishes,
  * Wait for Callback (.waitForTaskToken) — pause until someone calls
    SendTaskSuccess / SendTaskFailure with the task token (or the
    TimeoutSeconds / HeartbeatSeconds expire).
(Standard workflows can run up to 1 year, so waiting days for an approval is fine.)

Your task
---------
  * APPROVAL_STATE: a Task state that sends {"order_id": <from input>,
    "task_token": <the task token>} to the approvals queue APPROVAL_QUEUE_URL
    and waits for the callback, with a 1-day timeout (TimeoutSeconds) and
    "Next": "Ship",
  * `handle_decision(sfn, message_body, approved, reviewer)`: called by
    the approval UI. On approval, resume the execution with output
    {"approved": true, "reviewer": reviewer}. On rejection, fail the task
    with error "Rejected".
"""

# I AM NOT DONE

import json

APPROVAL_QUEUE_URL = "https://sqs.eu-west-3.amazonaws.com/123456789012/approvals"

APPROVAL_STATE = {
    "Type": "Task",
    "Resource": "arn:aws:states:::sqs:sendMessage",  # TODO: this does not wait for anything
    "Parameters": {
        "QueueUrl": APPROVAL_QUEUE_URL,
        "MessageBody": {"order_id.$": "$.order_id"},  # TODO: the approver needs the task token
    },
    "Next": "Ship",
}


def handle_decision(sfn, message_body: str, approved: bool, reviewer: str) -> None:
    message = json.loads(message_body)
    # TODO: resume or fail the waiting task
    raise NotImplementedError


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run sfn_2
# =============================================================================


class FakeStepFunctions:
    def __init__(self):
        self.calls = []

    def send_task_success(self, taskToken, output):
        self.calls.append(("success", taskToken, json.loads(output)))

    def send_task_failure(self, taskToken, error, cause=""):
        self.calls.append(("failure", taskToken, error))


def test_state_waits_for_token():
    assert APPROVAL_STATE["Type"] == "Task"
    assert APPROVAL_STATE["Resource"] == "arn:aws:states:::sqs:sendMessage.waitForTaskToken"
    body = APPROVAL_STATE["Parameters"]["MessageBody"]
    assert body.get("task_token.$") == "$$.Task.Token"
    assert body.get("order_id.$") == "$.order_id"
    assert APPROVAL_STATE["Parameters"]["QueueUrl"] == APPROVAL_QUEUE_URL
    assert APPROVAL_STATE.get("TimeoutSeconds") == 86400
    assert APPROVAL_STATE["Next"] == "Ship"


def test_approval_resumes_execution():
    sfn = FakeStepFunctions()
    handle_decision(sfn, json.dumps({"order_id": "o-1", "task_token": "TOKEN123"}), True, "ada")
    assert sfn.calls == [("success", "TOKEN123", {"approved": True, "reviewer": "ada"})]


def test_rejection_fails_task():
    sfn = FakeStepFunctions()
    handle_decision(sfn, json.dumps({"order_id": "o-1", "task_token": "TOKEN123"}), False, "ada")
    assert sfn.calls == [("failure", "TOKEN123", "Rejected")]
