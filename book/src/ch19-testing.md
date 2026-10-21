# Testing applications

> **In this chapter**
> - A testing strategy for cloud and serverless applications: unit, integration, end-to-end
> - Mocking AWS in unit tests (moto, botocore Stubber, dependency injection)
> - Local emulation with the SAM CLI and test events
> - Mock integrations and development endpoints (API Gateway stages, Lambda aliases)
> - Automating tests in pipelines: CodeBuild reports, deployment hooks, synthetic canaries
>
> **Exam weight**: Domain 1 Task 1.1 (unit tests), Domain 3 Tasks 3.2/3.3 (testing in development
> environments, automating deployment testing) · **Exercises**: `sam_2` (and every awslings test!)
> · **Quiz**: `uv run awslings quiz testing`

## A testing strategy

| Level | What it checks | How on AWS |
|---|---|---|
| **Unit tests** | Your logic, in isolation, fast (ms) | Plain functions + **mocked AWS calls** (moto, Stubber, fakes injected into handlers) |
| **Integration tests** | Your code with **real** AWS services and permissions | Deploy to a **dev/test stage or account** (`sam deploy`, `sam sync`), call the API/function, check side effects |
| **End-to-end tests** | Whole user journeys | Against a staging environment, API or UI level |
| **Contract tests** | APIs and events keep their agreed shape | OpenAPI/JSON Schema validation, EventBridge schema registry |
| **Load / chaos tests** | Behavior under stress and failure | Load generators, **AWS Fault Injection Service** (FIS) |

AWS's guidance for serverless is "**test in the cloud**" for integration: local emulators approximate
IAM, events and limits imperfectly. Use them for fast feedback, and use real ephemeral stacks for confidence.

## Unit testing with mocked AWS

Three techniques, used throughout awslings:

1. **moto**: an in-memory implementation of AWS APIs. Your boto3 code runs unchanged:

   ```python
   from moto import mock_aws

   @mock_aws
   def test_create_order():
       boto3.client("dynamodb").create_table(...)   # moto table
       assert handler({"id": "o-1"}, None) == {"ok": True}
   ```

2. **botocore Stubber**: queue expected calls and canned responses on a real client (great for errors):

   ```python
   from botocore.stub import Stubber
   stubber = Stubber(sqs)
   stubber.add_client_error("send_message", service_error_code="ThrottlingException")
   ```

3. **Dependency injection / fakes**: pass clients, clocks and sleep functions as parameters (exercises
   `sdk_3`, `cache_1`, `res_1`), so tests control time and failures.

Keep the **handler thin**: parse the event, call pure business functions, format the response. The
business functions are trivial to unit test.

> **Exam tip** — Amazon Q Developer can **generate unit tests** for existing code in the IDE (`/test`), a
> v2.1 exam guide addition.

## Local emulation with the SAM CLI

```bash
sam build
sam local generate-event apigateway aws-proxy --method GET --path orders > events/get.json
sam local invoke OrdersFunction -e events/get.json --env-vars env.json
sam local start-api                      # http://127.0.0.1:3000/orders
sam local start-lambda                   # local Lambda endpoint for SDK-based tests
```

- Functions run in Docker containers that mimic the Lambda runtime. They can call **real** AWS services with
  your local credentials, or local emulators (DynamoDB Local, LocalStack).
- **Test events**: realistic JSON payloads for API Gateway, SQS, SNS, S3, DynamoDB Streams, EventBridge...
  The Lambda console also lets you save **shareable test events** for a function.
- Container-image functions: test locally with the **Runtime Interface Emulator** (included in AWS base images).

### What real events look like

Write test events that match reality, including the surprising parts (exercise `sam_2`):

```json
{"resource": "/orders/{id}", "path": "/orders/o-7", "httpMethod": "GET",
 "headers": {"Content-Type": "application/json"},
 "queryStringParameters": null,
 "pathParameters": {"id": "o-7"},
 "body": null, "isBase64Encoded": false,
 "requestContext": {"stage": "test", "requestId": "c6af9ac6-...", "httpMethod": "GET"}}
```

`queryStringParameters` is `null` without a query string, `body` is a **string** (JSON-encoded) or
`null`, and SQS record bodies are strings too.

## Mock integrations and development endpoints

- **API Gateway mock integration**: API Gateway returns a static response (mapping template) without a backend.
  Front-end teams can start against the agreed contract before the backend exists. Also used to stub a
  dependency during integration tests.
- **Stages as environments**: `dev`, `test`, `prod` stages of the same API, each with stage variables pointing
  to different Lambda aliases or backend URLs. Test on the `test` stage URL without touching production
  (exercise `apigw_1`).
- **Approved versions for integration testing**: integration tests run against a specific **Lambda alias**,
  **container image tag/digest**, or **Amplify branch** environment, which is then promoted.
- **Separate accounts** per environment (with AWS Organizations) are the strongest isolation. Deploy the same
  SAM/CloudFormation template to each with environment parameters (`sam deploy --config-env staging`).

## Automating tests in the pipeline

```text
Commit → CodeBuild: lint + unit tests (JUnit report) → deploy to staging (SAM/CloudFormation)
       → CodeBuild: integration tests against the staging stage → manual approval
       → production deployment with canary + alarms + PreTraffic/PostTraffic hooks
       → CloudWatch Synthetics canaries keep testing production continuously
```

- **CodeBuild test reports** (JUnit, Cucumber, TestNG, coverage) appear in the console. Fail the build on test failures.
- **Deployment validation hooks**: CodeDeploy `ValidateService` (EC2), `AfterAllowTestTraffic` (ECS, against the test
  listener), `BeforeAllowTraffic`/`AfterAllowTraffic` (Lambda, via SAM `PreTraffic`/`PostTraffic`). A failed hook rolls the deployment back.
- **CloudWatch Synthetics canaries**: scheduled scripts (Node.js/Python, Puppeteer/Selenium) that call your APIs or
  load your pages and alarm when they break, even with no real users.
- **Step Functions**: the **TestState** API tests a single state (input/output processing, error handling) without
  deploying a whole workflow.
- **Load tests** before big events. Watch throttling, concurrency and downstream limits.

## Hands-on

| Exercise | Skill |
|---|---|
| `sam_2` | Realistic API Gateway and SQS test events fed to real handlers |
| every exercise | Read the tests: moto fixtures, fakes, injected clocks, spies (`unittest.mock`) |

## Summary

- Unit tests with mocked AWS (moto, Stubber, injected fakes). Integration tests against real deployed stacks.
- SAM CLI: `local invoke`, `local start-api`, `generate-event`, and the same template deployed per environment.
- Mock integrations let teams test API contracts early. Stages, aliases and image tags provide test endpoints and approved versions.
- Pipelines run unit tests (CodeBuild reports), integration tests on staging, deployment hooks, and synthetic canaries.

## Check yourself

1. A front-end team needs the `/orders` API now, but the backend will take two more weeks. What can you give them?
2. Name three ways to fake AWS calls in Python unit tests.
3. How can integration tests target a specific Lambda version while production keeps serving the old one?
4. Which CodeDeploy hook validates a new ECS task set using the test listener before production traffic shifts?
5. What runs continuously against production APIs and alarms when a user journey breaks?

<details><summary>Answers</summary>

1. An API Gateway stage with **mock integrations** returning the agreed responses.
2. **moto**, **botocore Stubber**, and **dependency injection** of fake clients (or `unittest.mock`).
3. Point a test stage / alias (e.g. `test`) at the new version and run the tests through it. `live` still points to the old version.
4. **`AfterAllowTestTraffic`**.
5. **CloudWatch Synthetics canaries**.

</details>

## Further reading

- [Testing serverless applications (AWS guidance)](https://docs.aws.amazon.com/lambda/latest/dg/testing-guide.html)
- [AWS SAM CLI: testing locally](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/using-sam-cli-local.html)
- [API Gateway mock integrations](https://docs.aws.amazon.com/apigateway/latest/developerguide/how-to-mock-integration.html)
- [CodeBuild test reports](https://docs.aws.amazon.com/codebuild/latest/userguide/test-reporting.html)
- [CloudWatch Synthetics](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_Canaries.html)
