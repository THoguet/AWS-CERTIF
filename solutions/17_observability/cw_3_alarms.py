"""
Exercise cw_3 — CloudWatch alarms
=================================
Book: chapter 20, "Alarms" (book/src/ch20-monitoring-logging.md)
Exam: Domain 4 · Task 4.2 (implementing notification alerts for specific actions)

An alarm watches ONE metric (or a metric math expression) and changes
state: OK, ALARM, INSUFFICIENT_DATA.
  * Period             — length of each evaluation window (60 s...),
  * EvaluationPeriods  — how many recent periods are considered,
  * DatapointsToAlarm  — how many of them must breach ("M out of N", here 2 out of 3,
                         which avoids paging on a single blip),
  * TreatMissingData   — missing / notBreaching / breaching / ignore,
  * actions            — SNS topics (email, chat, Lambda...), Auto Scaling,
                         EC2 actions, Systems Manager...

Your task
---------
  * `lambda_errors_alarm(cw, function_name, topic_arn)`: alarm
    "<function>-errors": Errors sum >= 1 in 2 of the last 3 one-minute
    periods, missing data = not breaching, notify the topic on ALARM and on OK,
  * `dlq_alarm(cw, queue_name, topic_arn)`: alarm "<queue>-not-empty":
    the maximum ApproximateNumberOfMessagesVisible of the queue > 0 over
    one 5-minute period, notify on ALARM.
"""


def lambda_errors_alarm(cw, function_name: str, topic_arn: str) -> None:
    cw.put_metric_alarm(
        AlarmName=f"{function_name}-errors",
        Namespace="AWS/Lambda",
        MetricName="Errors",
        Dimensions=[{"Name": "FunctionName", "Value": function_name}],
        Statistic="Sum",
        Period=60,
        EvaluationPeriods=3,
        DatapointsToAlarm=2,
        Threshold=1,
        ComparisonOperator="GreaterThanOrEqualToThreshold",
        TreatMissingData="notBreaching",
        AlarmActions=[topic_arn],
        OKActions=[topic_arn],
    )


def dlq_alarm(cw, queue_name: str, topic_arn: str) -> None:
    cw.put_metric_alarm(
        AlarmName=f"{queue_name}-not-empty",
        Namespace="AWS/SQS",
        MetricName="ApproximateNumberOfMessagesVisible",
        Dimensions=[{"Name": "QueueName", "Value": queue_name}],
        Statistic="Maximum",
        Period=300,
        EvaluationPeriods=1,
        Threshold=0,
        ComparisonOperator="GreaterThanThreshold",
        AlarmActions=[topic_arn],
    )


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run cw_3
# =============================================================================
import boto3  # noqa: E402

TOPIC = "arn:aws:sns:eu-west-3:123456789012:oncall"


def _alarm(cw, name):
    alarms = cw.describe_alarms(AlarmNames=[name])["MetricAlarms"]
    assert alarms, f"alarm {name} not found"
    return alarms[0]


def test_lambda_errors_alarm(aws):
    cw = boto3.client("cloudwatch")
    lambda_errors_alarm(cw, "checkout", TOPIC)
    alarm = _alarm(cw, "checkout-errors")
    assert (alarm["Namespace"], alarm["MetricName"], alarm["Statistic"]) == ("AWS/Lambda", "Errors", "Sum")
    assert alarm["Dimensions"] == [{"Name": "FunctionName", "Value": "checkout"}]
    assert (alarm["Period"], alarm["EvaluationPeriods"], alarm["DatapointsToAlarm"]) == (60, 3, 2)
    assert alarm["Threshold"] == 1 and alarm["ComparisonOperator"] == "GreaterThanOrEqualToThreshold"
    assert alarm["TreatMissingData"] == "notBreaching"
    assert alarm["AlarmActions"] == [TOPIC] and alarm["OKActions"] == [TOPIC]


def test_dlq_alarm(aws):
    cw = boto3.client("cloudwatch")
    dlq_alarm(cw, "payments-dlq", TOPIC)
    alarm = _alarm(cw, "payments-dlq-not-empty")
    assert (alarm["Namespace"], alarm["MetricName"]) == ("AWS/SQS", "ApproximateNumberOfMessagesVisible")
    assert alarm["Dimensions"] == [{"Name": "QueueName", "Value": "payments-dlq"}]
    assert alarm["Statistic"] == "Maximum" and alarm["Period"] == 300
    assert alarm["Threshold"] == 0 and alarm["ComparisonOperator"] == "GreaterThanThreshold"
    assert alarm["AlarmActions"] == [TOPIC]
