# Lab 01 — Serverless API with a canary deployment

> **Goal**: deploy a REST API (API Gateway → Lambda → DynamoDB) with AWS SAM, then ship a new
> version with a **canary deployment** and watch CodeDeploy **roll back automatically** when an alarm
> fires.
>
> **Book**: ch05 (Lambda), ch06 (API Gateway), ch16 (SAM, versions, aliases, traffic shifting) ·
> **Exercises**: `lambda_8`, `sam_1`, `sam_2` · **Time**: 1.5 h · **Cost**: < $0.10 if deleted the same day

```text
client ──HTTPS──► API Gateway (REST, stage Prod) ──► Lambda alias "live" ──► version N ──► DynamoDB table
                                                         │   (90%)
                                                         └──► version N+1 (10% during a canary)
CodeDeploy shifts the alias weights · CloudWatch alarm on errors → rollback
```

Files: `template.yaml` (SAM), `src/app.py` (the function), `events/*.json` (test events),
`tests/` (offline unit tests).

## 0. Before you start

- Lab 00 done, `AWS_PROFILE` and `AWS_REGION` exported, `sam --version` works.
- Run the unit tests offline first (from the repository root): `uv run pytest labs/lab01-serverless-api`.
- Read `template.yaml`. Find `AutoPublishAlias`, `DeploymentPreference`, the alarm, and the
  `DynamoDBCrudPolicy` policy template. Predict what SAM will generate.

## 1. Build and deploy

```bash
cd labs/lab01-serverless-api
sam validate --lint
sam build
sam deploy --guided
```

Answers for the guided deployment:

| Prompt | Answer |
|---|---|
| Stack Name | `dva-lab01` |
| AWS Region | `eu-west-3` |
| Parameter FailureRate | `0` |
| Confirm changes before deploy | `y` (you will see the change set) |
| Allow SAM CLI IAM role creation | `Y` |
| Disable rollback | `N` |
| *ItemsFunction has no authentication. Is this okay?* | `y` (this lab has no auth, lab02 adds it) |
| Save arguments to configuration file | `Y` (writes `samconfig.toml`, ignored by git) |

The first deployment creates version 1 and points the `live` alias at it directly: there is no
previous version to shift traffic from.

## 2. Use the API

```bash
API=$(aws cloudformation describe-stacks --stack-name dva-lab01 \
      --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" --output text)
FN=$(aws cloudformation describe-stacks --stack-name dva-lab01 \
      --query "Stacks[0].Outputs[?OutputKey=='FunctionName'].OutputValue" --output text)

curl -s -X POST "$API/items" -H "Content-Type: application/json" -d '{"name": "exam voucher"}'
ID=$(curl -s -X POST "$API/items" -H "Content-Type: application/json" -d '{"name": "practice test"}' \
     | python3 -c 'import json, sys; print(json.load(sys.stdin)["id"])')

curl -s -i "$API/items/$ID"        # 200 + X-Function-Version: 1
curl -s -i "$API/items/unknown"    # 404 from your code
curl -s -i -X POST "$API/items" -d 'oops'   # 400 from your code
curl -s -i "$API/item"             # 403 {"message":"Missing Authentication Token"}: the route does not exist
```

Follow the logs in another terminal: `sam logs --stack-name dva-lab01 -n ItemsFunction --tail`.
Each invocation ends with a `REPORT` line (duration, billed duration, memory used, init duration on
cold starts).

**Optional, needs Docker**: run the same code locally against the real table.

```bash
TABLE=$(aws cloudformation describe-stacks --stack-name dva-lab01 \
        --query "Stacks[0].Outputs[?OutputKey=='TableName'].OutputValue" --output text)
echo "{\"ItemsFunction\": {\"TABLE_NAME\": \"$TABLE\"}}" > /tmp/lab01-env.json
sam local invoke ItemsFunction -e events/get-item.json --env-vars /tmp/lab01-env.json   # 404 for an unknown id
```

## 3. A successful canary deployment

1. Edit `src/app.py`: in `response()`, add a header such as `"X-Release": "2"`.
2. In a **second terminal**, send one request per second and print the version that answered:

   ```bash
   while true; do
     curl -s -o /dev/null -D /tmp/lab01-headers -w "%{http_code} " "$API/items/$ID"
     grep -i '^x-function-version' /tmp/lab01-headers | tr -d '\r'
     sleep 1
   done
   ```

3. Deploy: `sam build && sam deploy`. The command waits while CodeDeploy shifts traffic.
4. While it runs:
   - about 1 response in 10 comes from the new version,
   - `aws lambda get-alias --function-name "$FN" --name live` shows
     `RoutingConfig.AdditionalVersionWeights` = `{"2": 0.1}`,
   - *CodeDeploy console → Deployments* shows the deployment with 10% of traffic shifted.
5. After 5 minutes the alias points 100% to version 2 and `sam deploy` completes.

## 4. A failed deployment that rolls back by itself

Keep the request loop running and deploy a version where half of the requests crash:

```bash
sam deploy --parameter-overrides FailureRate=0.5
```

The changed environment variable is a configuration change, so SAM publishes a new version and
CodeDeploy starts a canary. Watch for:

1. `502` responses in the loop: an unhandled exception in Lambda becomes a **502 Bad Gateway** behind API Gateway.
2. The alarm going to `ALARM`:
   `aws cloudwatch describe-alarms --alarm-name-prefix dva-lab01 --query 'MetricAlarms[].[AlarmName,StateValue]'`.
3. CodeDeploy **stopping the deployment** and moving all traffic back to the previous version.
4. CloudFormation failing the update and rolling back the stack (`UPDATE_ROLLBACK_COMPLETE`).
   `sam deploy` exits with an error. That is the expected result.

Users saw only a few errors (10% of traffic for about a minute) instead of a full outage.

## 5. Explore

- List what SAM generated:
  `aws cloudformation list-stack-resources --stack-name dva-lab01 --query 'StackResourceSummaries[].[LogicalResourceId,ResourceType]' --output table`.
  Find the alias, the versions, the CodeDeploy application and deployment group, the API stage, and
  the `AWS::Lambda::Permission` that lets API Gateway invoke the alias.
- See the expanded template:
  `aws cloudformation get-template --stack-name dva-lab01 --template-stage Processed --query TemplateBody`.
  Look at the alias's `UpdatePolicy` (`CodeDeployLambdaAliasUpdate`).
- In the IAM console, open the function's role: the policy template became a policy scoped to one table.
- Invoke a specific version directly: `aws lambda invoke --function-name "$FN:1" --payload fileb://events/get-item.json /tmp/out.json && cat /tmp/out.json`.

## Teardown

```bash
sam delete --stack-name dva-lab01          # confirm both prompts (stack + artifacts)
aws logs delete-log-group --log-group-name "/aws/lambda/$FN"   # Lambda created it, so the stack does not delete it
```

The `aws-sam-cli-managed-default` stack holds the S3 bucket that SAM uses for artifacts. Keep it for
the next labs, and delete it after the last one (empty the bucket first in the S3 console).

## What to remember for the exam

- `AutoPublishAlias` + `DeploymentPreference` = new version on each change + CodeDeploy traffic
  shifting (`Canary10Percent5Minutes`, `Linear10PercentEvery1Minute`, `AllAtOnce`). Alarms roll back automatically.
- A failed CodeDeploy step makes the **CloudFormation update fail and roll back**.
- Event sources and integrations should target the **alias**. Releasing or rolling back = moving the alias.
- Proxy integration responses need `statusCode` and a string `body`. Unhandled errors → **502**.
  Unknown routes on a REST API → **403 Missing Authentication Token**.
- Execution role (what the function may call) vs resource-based policy (who may invoke the function).
- Log groups created by Lambda survive stack deletion: set retention or create them in the template.
