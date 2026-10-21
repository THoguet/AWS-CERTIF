# Exam strategy

> **In this chapter**
> - What the exam looks like and how it is scored
> - How questions are built, and how to decode them
> - Time management, elimination, and the keywords that decide answers
> - Booking, accommodations, and exam-day logistics
>
> **Quiz**: there is no quiz for this chapter, but run `uv run awslings quiz -n 20` as a diagnostic today.

## The exam in one table

| | |
|---|---|
| Code | DVA-C02 (guide v2.1). **Last day: 30 Nov 2026** |
| Questions | 65: 50 scored + 15 unscored "pretest" questions you cannot distinguish |
| Time | 130 minutes → **2 minutes per question** |
| Formats | *Multiple choice*: 4 options, 1 correct. *Multiple response*: 5+ options, 2+ correct, and the question says how many ("Choose TWO.") |
| Score | 100–1000, pass at **720**. Scaled and **compensatory**: you can be weak in one domain if strong elsewhere |
| Guessing | No penalty, so **never leave a question blank** |
| Domains | Development 32% · Security 26% · Deployment 24% · Troubleshooting & Optimization 18% |

Because the score is scaled, there is no exact "number of correct answers" to pass. A good
rule of thumb is to aim for **80%+ on practice exams** before sitting the real one.

## Anatomy of a question

Almost every question has the same three parts:

```text
[SCENARIO]     A company runs an order-processing application on AWS Lambda. Orders arrive in
               bursts of several thousand per minute from an API...
[REQUIREMENT]  The developer must ensure that no order is lost if the downstream payment
               service is unavailable for up to 2 hours.
[CONSTRAINT]   Which solution meets these requirements with the LEAST operational overhead?
```

**Read the last sentence first.** It tells you what to optimize for. Then read the scenario
looking for facts that eliminate options: limits ("payload up to 2 MB"), durations ("up to
2 hours"), ordering, existing services, the team's skills...

### Types of wrong answers

The distractors fall into four families. Name the family when you eliminate an option:

1. **Works, but violates the constraint**: a custom solution on EC2 when the question says
   "least operational overhead", or provisioned capacity when it says "most cost-effective".
2. **Wrong service for the job**: Kinesis for simple decoupling, SNS when you need durable
   buffering, CloudTrail to measure latency.
3. **Partially correct**: right service, wrong setting (e.g. SQS with a visibility timeout shorter
   than the processing time; a GSI queried with strong consistency).
4. **Invented or impossible**: a feature that does not exist, or a limit that is exceeded
   (a 20-minute Lambda function, a 6 KB KMS Encrypt call).

## Keyword decoder

These phrases almost always point toward a family of answers:

| The question says… | Think… |
|---|---|
| "LEAST operational overhead", "fully managed" | Serverless and managed features over custom code: Lambda, DynamoDB, SQS, Step Functions, managed rotation, built-in integrations |
| "MOST cost-effective" | On-demand vs provisioned, S3 lifecycle and storage classes, right-sized Lambda memory, caching, batching |
| "without changing the application code" | Configuration: environment variables, stage variables, aliases, bucket policies, CloudFront behaviors, Lambda layers / extensions |
| "decouple", "absorb spikes", "buffer" | **SQS** between producer and consumer |
| "fan out to multiple consumers" | **SNS → several SQS queues**, or EventBridge rules |
| "strict order", "exactly once", "deduplicate" | **SQS FIFO** (message group ID, deduplication ID) |
| "real-time stream", "replay", "multiple consumers reading the same data" | **Kinesis Data Streams** |
| "load streaming data into S3/OpenSearch/Redshift", "near real-time" | **Amazon Data Firehose** |
| "react to events from AWS services / SaaS", "event bus", "schedule" | **EventBridge** |
| "coordinate steps, retries, human approval, long-running workflow" | **Step Functions** |
| "temporary credentials", "cross-account access" | **IAM roles + STS AssumeRole** |
| "users sign up / sign in" | **Cognito user pool** |
| "give app users AWS credentials" | **Cognito identity pool** |
| "who made this API call?" | **CloudTrail** |
| "trace latency across services", "service map" | **X-Ray** (OpenTelemetry) |
| "custom metric", "metric from logs" | `PutMetricData`, **Embedded Metric Format**, metric filters |
| "store DB credentials and rotate them" | **Secrets Manager** |
| "configuration values / hierarchy, cheap" | **SSM Parameter Store** |
| "feature flags", "gradual config rollout" | **AWS AppConfig** |
| "encrypt data larger than 4 KB" | **Envelope encryption** (`GenerateDataKey`) |
| "share a file temporarily without AWS credentials" | **S3 presigned URL** |
| "zero downtime", "fast rollback" | Blue/green, immutable, canary/linear traffic shifting with aliases |

> **Exam tip** — When two answers both work, the exam wants the one that uses a **native
> feature** instead of code you would have to write and maintain.

## Time management

- First pass: answer everything in ~90 minutes. If a question takes more than ~2.5 minutes,
  pick your best guess, **flag it**, move on.
- Second pass: revisit flagged questions with the remaining time. Later questions sometimes
  remind you of a detail.
- Last 2 minutes: make sure every question has an answer.

For multiple response questions, evaluate each option **independently** (true/false), then pick
the required number. They are scored all or nothing, with no partial credit.

## Elimination technique

1. Read the requirement and constraint (last sentence).
2. Eliminate **impossible** options first: wrong limits, non-existent features.
3. Eliminate options that **violate the constraint**: too much ops work, too expensive, not secure.
4. Between the last two, pick the one that is the **most AWS-native** and **least custom**.
5. Don't overthink. Questions describe "typical" AWS setups, not edge cases.

## Booking and logistics

- Book through your AWS Certification account (Pearson VUE delivery): in a **test center** or
  **online proctored** from home.
- **Non-native English speaker?** Request the **ESL +30 minutes** accommodation in your
  certification account **before** scheduling. Then you get 160 minutes.
- **Online proctoring**: quiet room, clean desk, webcam, government ID, system check beforehand.
  No paper: use the on-screen whiteboard. Check in early.
- **Test center**: arrive about 30 minutes early with a valid government-issued photo ID.
- You may reschedule or cancel up to 24 hours before the appointment. Read the current policy when booking.
- Results usually arrive by email within a few days, with a breakdown by domain.
- After a fail, you must wait **14 days** before retaking (and pay again).
- Passing grants a 50% discount voucher for your next AWS exam. It shows up in your certification account.

## A study method that works

- **Active recall beats rereading.** Answer the "Check yourself" questions before revealing them,
  and explain concepts to your tutor in your own words.
- **Spaced repetition.** Revisit weak topics after 1, 3 and 7 days. The tutor keeps that queue in `PROGRESS.md`.
- **Practice questions early.** They show you how concepts are tested. Read every explanation, not
  only the ones you got wrong.
- **Hands-on.** Even mocked exercises build intuition for API shapes and error codes, and the
  optional labs make services concrete.
- **Official free resources**: AWS Skill Builder offers a free official practice question set and
  an exam prep course for DVA-C02. Use them in week 5 as an extra calibration point.

## Check yourself

1. How many questions are scored, and what is the passing score?
2. A multiple response question asks you to choose THREE. You are sure of two. What do you do?
3. Which part of the question should you read first, and why?
4. Two options both solve the problem. One uses a native feature, the other a small custom
   Lambda function. The constraint is "least operational overhead". Which one wins?

<details><summary>Answers</summary>

1. 50 of the 65 questions are scored. The pass mark is 720 on a 100–1000 scaled score.
2. Pick the third most plausible option anyway: no penalty for wrong answers, and an empty
   answer is always wrong.
3. The last sentence (the requirement and constraint), because it tells you what the "best"
   answer optimizes for.
4. The native feature: less code to write, deploy, secure and maintain.

</details>

## Further reading

- [AWS Certified Developer – Associate exam page](https://aws.amazon.com/certification/certified-developer-associate/)
- [DVA-C02 exam guide](https://docs.aws.amazon.com/aws-certification/latest/developer-associate-02/developer-associate-02.html)
- [AWS Certification policies (retakes, accommodations)](https://aws.amazon.com/certification/policies/)
