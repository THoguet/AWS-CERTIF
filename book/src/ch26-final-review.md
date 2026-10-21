# Final week and exam day

> **In this chapter**
> - A readiness checklist
> - The last 7 days, day by day
> - Exam-day logistics and in-exam technique
> - The 30 facts most worth rereading the night before

## Readiness checklist

- [ ] Two consecutive mock exams ≥ **80%** (`uv run awslings mock`)
- [ ] Every domain ≥ **70%** in `uv run awslings stats`
- [ ] All 83 awslings exercises done (`uv run awslings verify`)
- [ ] The weak-spot queue in `PROGRESS.md` is empty or only has items reviewed twice
- [ ] You can explain, without notes: IAM evaluation logic, Lambda invocation models and concurrency,
      DynamoDB capacity math and indexes, SQS visibility timeout/DLQ/FIFO, Cognito user vs identity pools,
      KMS envelope encryption, SAM/CodeDeploy traffic shifting, CodeDeploy hook order, X-Ray annotations vs metadata
- [ ] Exam booked (before **30 Nov 2026**), ESL +30 requested if relevant, ID ready, online system check done

## The last 7 days

| Day | Focus |
|---|---|
| D-7 | Mock exam #1 in one sitting. Debrief with `/mock-exam`: group misses by concept |
| D-6 | Deep dive on the 2–3 weakest concepts: chapter sections, redo their exercises, `/quiz <topic>` |
| D-5 | Mock exam #2. Debrief |
| D-4 | [Which service when?](ch25-service-selection.md) and the "same goal, different answer" pairs. `/drill` |
| D-3 | Mock #3 or domain mini-mocks on weak domains. `awslings quiz --wrong` until clean |
| D-2 | [Numbers and limits](ch24-numbers-limits.md). Reread every "Exam tip" and "Trap" callout |
| D-1 | Light review only (the 30 facts below). Prepare ID and room. **Sleep** |

## Exam day

- **Online**: clean desk, quiet room, webcam, government ID, launch the check-in ~30 minutes early, close
  every application. No phone within reach, and no paper (use the on-screen whiteboard).
- **Test center**: arrive ~30 minutes early with ID.
- Eat, hydrate, plan a break-free 130 (or 160) minutes.

### In-exam technique

1. **Read the last sentence first** (what is asked, which constraint: least overhead, most cost-effective, most secure).
2. Spot the **deciding keyword** in the scenario (real-time, ordered, temporary credentials, without code changes...).
3. **Eliminate**: impossible options (wrong limits, invented features), then options violating the constraint.
4. Prefer **native, managed, least-custom** solutions.
5. ~2 minutes per question. **Flag** and move on when stuck. Second pass for flagged questions.
6. Multiple response: evaluate each option as true/false, pick exactly the requested number.
7. **Never leave a blank**: there is no penalty for wrong answers.

## 30 facts for the night before

1. Explicit deny > explicit allow > implicit deny. Boundaries and SCPs only restrict.
2. Code on AWS uses **roles**. Stale env vars beat instance profiles in the credential chain.
3. Throttling/5xx → exponential backoff **with jitter**. 4xx → fix the request.
4. Paginate (S3 1,000 keys, DynamoDB 1 MB). Use waiters for async resource creation.
5. Lambda: 15 min, 10 GB memory (CPU follows), 10 GB /tmp, 4 KB env vars, 5 layers, 250 MB unzipped, 10 GB image.
6. Lambda async: 2 retries, up to 6 h, then DLQ or **destinations** (success + failure, with context).
7. Concurrency = rps × duration. 1,000 per Region default. Reserved = guarantee + cap. Provisioned = no cold starts.
8. SQS-triggered Lambda: visibility timeout ≥ 6× function timeout, **ReportBatchItemFailures**, DLQ on the queue.
9. Lambda in VPC → NAT gateway or **VPC endpoints** to reach AWS APIs (gateway endpoints for S3/DynamoDB).
10. API Gateway proxy response = `{statusCode, headers, body: string}`, otherwise **502**. Timeout 29 s → **504**.
11. Stage variables + Lambda aliases = environments. Add a Lambda permission per alias.
12. API keys are **not** auth. Usage plans throttle and meter (429).
13. RCU 4 KB (strong 1, eventual ½, transactional 2). WCU 1 KB (transactional 2). Round up.
14. Query > Scan. Filters do not save RCU. GSI = eventual only, any time. LSI = at creation, strong possible.
15. Optimistic locking = version + condition expression. Idempotency = `attribute_not_exists` conditional put.
16. TTL in epoch **seconds**. Streams 24 h. NEW_AND_OLD_IMAGES to compare. DAX = microseconds, no code change.
17. Lazy loading (stale risk) + write-through (fresh) + TTL. Redis for HA/structures. RDS Proxy for Lambda.
18. SQS: delete after processing, long polling 20 s, retention 4 days (max 14), FIFO = groups + 5-min dedup.
19. Large messages → **S3 + pointer** (claim check), whatever the current size limits.
20. SNS fan-out to SQS. Filter policies. EventBridge: patterns, 5 targets, archive/replay, Scheduler.
21. Kinesis shard: 1 MB/s or 1,000 rec/s in, 2 MB/s out. Partition key → ordering per shard. Firehose = managed delivery, no replay.
22. Step Functions: Standard 1 year exactly-once, Express 5 min. Retry → Catch (ResultPath keeps input). `.waitForTaskToken`.
23. User pool = JWTs. Identity pool = AWS credentials. Pre token generation adds claims. Access token for API scopes.
24. KMS Encrypt ≤ 4 KB → **envelope encryption**. Key policy is mandatory. Cross-account = key policy + IAM policy. Encryption context = AAD.
25. Secrets Manager rotates (AWSPENDING → AWSCURRENT). Parameter Store is free/hierarchical. AppConfig = feature flags with rollback.
26. CloudFormation: `!Ref` queue = URL, `!GetAtt .Arn` = ARN. DeletionPolicy Retain/Snapshot. Change sets. Exports vs nested stacks. `cdk bootstrap`.
27. SAM: `AutoPublishAlias` + `DeploymentPreference` (Canary/Linear) + alarms + Pre/PostTraffic hooks.
28. CodeDeploy EC2 hooks: ApplicationStop → DownloadBundle → BeforeInstall → Install → AfterInstall → ApplicationStart → ValidateService.
29. Beanstalk: all at once (downtime) · rolling (reduced) · rolling + batch (full) · immutable (fast rollback) · traffic splitting (canary) · blue/green = swap URLs.
30. CloudWatch = metrics/logs/alarms (EMF for custom metrics, Logs Insights for queries). X-Ray = traces (annotations are searchable). CloudTrail = who did what.

Good luck! You've got this. 🚀
