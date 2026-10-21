# Lab 03 — Event-driven pipeline: S3 → EventBridge → Step Functions

> **Goal**: build an event-driven workflow. Uploading a CSV file to S3 emits an event, an
> EventBridge rule starts a Step Functions workflow, and the workflow validates the file with Lambda,
> alerts through SNS when the total is large, stores a summary in DynamoDB, and sends bad files to an
> SQS queue. You will follow executions step by step and see Retry, Catch, Choice and ResultPath at
> work.
>
> **Book**: ch04 (S3 events), ch09 (SNS, SQS, EventBridge), ch10 (Step Functions) · **Exercises**:
> `events_1`, `sfn_1`, `sqs_1`, `sns_1` · **Time**: 1.5 h · **Cost**: < $0.10 if deleted the same day

```text
aws s3 cp file.csv s3://bucket/incoming/ ─► S3 "Object Created" event ─► EventBridge rule (prefix incoming/)
   ─► Step Functions (Standard)
        ValidateFile (Lambda, Retry on Lambda errors, Catch InvalidFile) ──► RejectFile (SQS) ─► Rejected (Fail)
          └─► IsLargeTotal (Choice: total > 1,000.00) ──► AlertLargeTotal (SNS) ─┐
                                └──────────────────────────────────────────────┴─► SaveSummary (DynamoDB)
```

Files: `template.yaml`, `statemachine/process_upload.asl.json` (the workflow, in Amazon States
Language), `src/validate.py`, `sample/*.csv`, `tests/`.

## 1. Read before you deploy

- `template.yaml`: the bucket sends its events to EventBridge (`EventBridgeEnabled: true`). The state
  machine's `Events` section creates the rule. `Policies` give the workflow's role only what its
  states call.
- `process_upload.asl.json`: find the `Retry` (transient Lambda errors, exponential backoff with
  jitter), the `Catch` on the business error `InvalidFile` with `"ResultPath": "$.error"`, and the
  direct service integrations (`sns:publish`, `dynamodb:putItem`, `sqs:sendMessage`): no Lambda code
  is needed for those steps.

## 2. Deploy

```bash
cd labs/lab03-event-driven
sam build && sam deploy --guided     # stack dva-lab03, Region eu-west-3, AlertEmail = your email
```

Confirm the SNS subscription from the email "AWS Notification - Subscription Confirmation".
Until then, SNS does not deliver anything to you.

```bash
out() { aws cloudformation describe-stacks --stack-name dva-lab03 \
        --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }
BUCKET=$(out BucketName); SM=$(out StateMachineArn); TABLE=$(out SummaryTableName)
QUEUE=$(out RejectedQueueUrl); FN=$(out ValidateFunctionName)
latest() { aws stepfunctions list-executions --state-machine-arn "$SM" --max-items 1 \
           --query 'executions[0].executionArn' --output text; }
```

## 3. A valid, small file

```bash
aws s3 cp sample/orders-small.csv "s3://$BUCKET/incoming/orders-small.csv"
sleep 10
aws stepfunctions list-executions --state-machine-arn "$SM" --query 'executions[].[name,status]' --output table
aws stepfunctions describe-execution --execution-arn "$(latest)" --query '{status: status, output: output}'
aws dynamodb get-item --table-name "$TABLE" --key '{"file": {"S": "incoming/orders-small.csv"}}'
```

Open the execution in the Step Functions console (*Graph view*). Click each state and compare its
**input** and **output**: the EventBridge event enters the workflow, `ResultSelector` keeps three
fields of the Lambda response, and `ResultPath` adds them under `$.summary` without losing
`$.detail`.

## 4. A large file: the Choice branch

```bash
aws s3 cp sample/orders-large.csv "s3://$BUCKET/incoming/orders-large.csv"
```

The total is 1,188.89, so the execution goes through `AlertLargeTotal` and you receive an email.
`AlertLargeTotal` has `"ResultPath": null`: the SNS response is thrown away and the state's input
moves on unchanged to `SaveSummary`.

## 5. A broken file: Catch and the rejected queue

```bash
aws s3 cp sample/broken.csv "s3://$BUCKET/incoming/broken.csv"
sleep 10
aws stepfunctions describe-execution --execution-arn "$(latest)" --query '{status: status, error: error}'
aws sqs receive-message --queue-url "$QUEUE" --wait-time-seconds 10      # long polling
```

The function raised `InvalidFile`. The error is not retried (it is not in `Retry`), the `Catch`
routes it to `RejectFile`, and the execution ends in the `Rejected` Fail state (`FAILED`). The message
body contains the file name and the error. Delete it once read:

```bash
aws sqs delete-message --queue-url "$QUEUE" --receipt-handle "<ReceiptHandle from the output above>"
```

## 6. Filtering at the source

```bash
aws s3 cp sample/orders-small.csv "s3://$BUCKET/archive/orders-small.csv"
```

No new execution starts: the rule's pattern only matches keys with the prefix `incoming/`.
EventBridge filtered the event before anything ran, so it cost no compute.

## 7. Explore (and break things on purpose)

- EventBridge console → *Rules* (default event bus): read the rule's event pattern, its target (the
  state machine) and the IAM role that lets EventBridge start executions.
- In the execution's *Events* tab, find `TaskScheduled`, `TaskSucceeded` / `TaskFailed`, and the
  catch transition.
- **Why ResultPath matters**: in the ASL file, delete `"ResultPath": null,` from `AlertLargeTotal`,
  then `sam build && sam deploy` and upload the large file under a new name. `SaveSummary` fails
  because the SNS response replaced the state input and `$.detail` no longer exists. Put the line
  back and redeploy.
- What happens if the function fails with another error (for example, upload a file, then delete it
  before the workflow reads it)? Which errors would you add to `Catch`, and which to `Retry`?

## Teardown

```bash
aws s3 rm "s3://$BUCKET" --recursive      # CloudFormation cannot delete a bucket that still has objects
sam delete --stack-name dva-lab03
aws logs delete-log-group --log-group-name "/aws/lambda/$FN"
```

If you skip the first command, `sam delete` ends in `DELETE_FAILED` on the bucket. Empty it, then
run `sam delete` again.

## What to remember for the exam

- S3 can send events to **EventBridge** (content filtering on key, size, metadata, several targets,
  archive and replay) or directly to Lambda, SQS and SNS (S3 event notifications).
- Step Functions **Standard** workflows: exactly-once, up to 1 year, full history (good for
  business processes). **Express**: high volume, up to 5 minutes, at-least-once.
- **Retry** for transient errors (backoff + jitter), **Catch** for errors that need another path.
  `ResultPath` decides where a state's result goes: `"$.error"` keeps the input and adds the error,
  `null` discards the result.
- Service integrations (DynamoDB, SNS, SQS, ECS, Glue...) remove "glue" Lambda functions.
- SQS **long polling** (`WaitTimeSeconds` up to 20) reduces empty receives. SNS email subscriptions
  must be confirmed.
- A non-empty S3 bucket blocks stack deletion.
