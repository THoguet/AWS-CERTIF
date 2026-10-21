# Study plan — DVA-C02 in 5 weeks

**Start:** Thursday 22 Oct 2026 · **Suggested exam:** Wednesday 25 Nov 2026 ·
**Hard deadline:** Monday 30 Nov 2026 (last day of DVA-C02)
**Rhythm:** about 1–1.5 h per day. Each "review" day absorbs delays.

Each day follows the same loop:

1. **Read** the chapter (`book/src/…`, or `mdbook serve book`), 30–45 min.
2. **Practice** with the awslings exercises of the chapter (`uv run awslings`), 20–30 min.
3. **Check** with an exam-style quiz (`uv run awslings quiz <topic>`), 10–15 min.
4. **Tell your tutor** how it went (`/progress`), so weak spots get scheduled for review.

> Tip: start each session in Claude Code with `/today`. It reads this plan and PROGRESS.md and proposes the session.

## Week 1 — Foundations, IAM, SDKs, S3

| Day | Date | Read | Exercises | Quiz |
|---|---|---|---|---|
| D1 | Thu 22 Oct | Introduction, ch00 exam strategy. **Book the exam** (and request ESL +30 first if English is not your native language) | intro_1–2 | `quiz -n 20` (diagnostic, all topics) |
| D2 | Fri 23 Oct | ch01 AWS foundations for developers | — | foundations |
| D3 | Sat 24 Oct | ch02 IAM | iam_1–5 | iam |
| D4 | Sun 25 Oct | ch03 CLI, SDKs, STS | sdk_1–5 | sdk |
| D5 | Mon 26 Oct | ch04 S3 (buckets → encryption) | s3_1–4 | — |
| D6 | Tue 27 Oct | ch04 S3 (lifecycle → events) | s3_5–7 | s3 |
| D7 | Wed 28 Oct | **Review**: catch up, `/drill` week 1 numbers | — | `quiz --wrong` |

## Week 2 — Lambda, API Gateway, DynamoDB, caching

| Day | Date | Read | Exercises | Quiz |
|---|---|---|---|---|
| D8 | Thu 29 Oct | ch05 Lambda (model, configuration, concurrency) | lambda_1–4 | — |
| D9 | Fri 30 Oct | ch05 Lambda (event sources, async, VPC) | lambda_5–7 | lambda |
| D10 | Sat 31 Oct | ch06 API Gateway & AppSync | apigw_1–3 | apigw |
| D11 | Sun 1 Nov | ch07 DynamoDB (model, capacity, queries, indexes) | ddb_1–4 | — |
| D12 | Mon 2 Nov | ch07 DynamoDB (conditions, transactions, streams, DAX) | ddb_5–9 | dynamodb |
| D13 | Tue 3 Nov | ch08 Caching, relational databases, CloudFront | cache_1–3 | caching |
| D14 | Wed 4 Nov | **Review**: Domain 1 so far | — | `quiz -d 1 -n 30` |

Optional lab this week: **lab01 serverless API** (weekend).

## Week 3 — Integration, patterns, security

| Day | Date | Read | Exercises | Quiz |
|---|---|---|---|---|
| D15 | Thu 5 Nov | ch09 SQS, SNS, EventBridge | sqs_1–4, sns_1, events_1 | messaging |
| D16 | Fri 6 Nov | ch10 Kinesis, Firehose, Step Functions | kinesis_1–3, sfn_1–2 | streaming |
| D17 | Sat 7 Nov | ch11 Application patterns and resilience | res_1–2 | patterns |
| D18 | Sun 8 Nov | ch12 Cognito | cognito_1–3 | cognito |
| D19 | Mon 9 Nov | ch13 KMS and encryption | kms_1–3 | kms |
| D20 | Tue 10 Nov | ch14 Secrets and configuration | secrets_1–4 | secrets |
| D21 | Wed 11 Nov | **Review**: Domain 2 | — | `quiz -d 2 -n 30` then `quiz --wrong` |

Optional labs this week: **lab02 Cognito-protected API**, **lab03 event-driven pipeline**.

## Week 4 — Deployment and observability

| Day | Date | Read | Exercises | Quiz |
|---|---|---|---|---|
| D22 | Thu 12 Nov | ch15 CloudFormation and CDK | cfn_1–2 | cloudformation |
| D23 | Fri 13 Nov | ch16 SAM and serverless deployments | sam_1, lambda_8 | sam |
| D24 | Sat 14 Nov | ch17 CI/CD with CodeCommit/CodeBuild/CodeDeploy/CodePipeline | cicd_1, cicd_2, cicd_4 | cicd |
| D25 | Sun 15 Nov | ch18 Elastic Beanstalk and containers | cicd_3, ecs_1, beanstalk_1 | containers |
| D26 | Mon 16 Nov | ch19 Testing · ch20 Monitoring and logging | sam_2, cw_1–5 | testing, monitoring |
| D27 | Tue 17 Nov | ch21 Tracing · ch22 Troubleshooting | xray_1 | xray, troubleshooting |
| D28 | Wed 18 Nov | ch23 Optimization. Run `awslings verify` | opt_1–2 | optimization |

Optional labs this week: **lab04 CI/CD pipeline**, **lab05 observability**, **lab06 Beanstalk deployments**.

## Week 5 — Exam rehearsal

| Day | Date | Activity |
|---|---|---|
| D29 | Thu 19 Nov | **Mock exam #1** (`awslings mock`, 130 min, no notes, in one sitting), then review every miss with `/mock-exam` |
| D30 | Fri 20 Nov | Deep dive on the 3 weakest topics (tutor-led) · ch24 numbers and limits |
| D31 | Sat 21 Nov | **Mock exam #2** + review |
| D32 | Sun 22 Nov | ch25 service selection · targeted quizzes on weak topics |
| D33 | Mon 23 Nov | **Mock exam #3** (or 3 domain mini-mocks) · ch26 final checklist |
| D34 | Tue 24 Nov | Light day: cheat sheets, `/drill`, sleep early |
| D35 | Wed 25 Nov | 🎯 **Exam day** (buffer until Mon 30 Nov) |

## Am I ready?

Go to the exam when **all** of these are true:

- [ ] ≥ 80% on two consecutive mock exams
- [ ] every domain ≥ 70% in `awslings stats`
- [ ] all 83 awslings exercises done (`awslings verify`)
- [ ] the weak-spot queue in PROGRESS.md is empty or only has "reviewed twice" items

If you are clearly not ready by 23 Nov, it may be better to take **DVA-C03** after 1 December
instead of rushing. Almost all of this material still applies. Ask your tutor to add the C03-specific topics.
