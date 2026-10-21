# CI/CD with AWS developer tools

> **In this chapter**
> - CI/CD concepts, Git branches/tags and release management
> - CodeCommit (and Git providers through CodeConnections)
> - CodeBuild: buildspec, environment, secrets, artifacts, caching, test reports
> - CodeDeploy: EC2/on-premises, Lambda and ECS deployments, AppSpec files, lifecycle hooks, rollbacks
> - CodePipeline: stages, actions, artifacts, triggers, manual approvals, cross-account
> - CodeArtifact, and a map of deployment strategies
>
> **Exam weight**: Domain 3 Task 3.4 (deploy code by using AWS CI/CD services), Task 3.3, Domain 4 Task 4.1
> (troubleshooting deployment failures) · **Exercises**: `cicd_1`, `cicd_2`, `cicd_4` · **Quiz**: `uv run awslings quiz cicd`

## Concepts

- **Continuous integration (CI)**: every commit is built and tested automatically.
- **Continuous delivery**: every change produces a deployable, tested artifact. Production deployment may
  wait for a **manual approval**. **Continuous deployment**: it goes to production automatically.
- **Build once, deploy many**: the same artifact (zip, container image digest, packaged template) is promoted
  from dev to test to prod. Only configuration changes per environment.
- **Release management with Git**: feature branches merged through pull requests, `main` always releasable,
  **tags** (`v1.4.2`) marking releases. Pipelines can trigger on branches or tags. Image tags, Lambda
  aliases and Amplify branches play the same role for runtime versions.

```text
CodeCommit / GitHub ──► CodePipeline ──► CodeBuild (build + unit tests, artifact to S3/ECR)
                                    ├──► Deploy to staging (CloudFormation/SAM, CodeDeploy, ECS, Beanstalk)
                                    ├──► CodeBuild (integration tests against staging)
                                    ├──► Manual approval (SNS notification)
                                    └──► Deploy to production (canary/blue-green, alarms → rollback)
```

## CodeCommit and other Git sources

- **CodeCommit**: managed private Git repositories, encrypted at rest (KMS), access controlled by **IAM**.
  It was closed to new customers in July 2024 and returned to **general availability in November 2025**.
  It remains in exam scope.
  - Access over HTTPS with **Git credentials** (IAM users) or **`git-remote-codecommit`** (roles, SSO,
    temporary credentials), or over SSH with keys uploaded to an IAM user.
  - Restrict actions per branch with IAM conditions (e.g. deny `codecommit:GitPush` on
    `refs/heads/main` for developers). **Approval rule templates** for pull requests.
  - **Triggers** (SNS, Lambda) on push events, **notifications** to SNS or chat (Amazon Q Developer in chat
    applications), events in **EventBridge** (used by CodePipeline to start).
  - Cross-account access: a role in the repository account that the other account's users assume.
- **GitHub, GitLab, Bitbucket**: connect through **AWS CodeConnections** (formerly CodeStar
  Connections) as a pipeline source, or use webhooks for CodeBuild.

## CodeBuild

A fully managed build service: each build runs in a fresh container, and you pay per build minute.

```yaml
version: 0.2
env:
  variables:
    ARTIFACT_BUCKET: my-artifacts-bucket
  parameter-store:
    SONAR_TOKEN: /ci/sonar/token                  # fetched and decrypted at build time
  secrets-manager:
    DOCKERHUB_PASS: prod/dockerhub:password       # secret-id:json-key
phases:
  install:
    runtime-versions:
      python: 3.12
    commands:
      - pip install -r requirements.txt
  pre_build:
    commands:
      - pytest --junitxml=reports/junit.xml
      - aws ecr get-login-password | docker login --username AWS --password-stdin $REPO_URI
  build:
    commands:
      - sam build
      - sam package --s3-bucket $ARTIFACT_BUCKET --output-template-file packaged.yaml
  post_build:
    commands:
      - echo "Build completed on $(date)"
reports:
  unit-tests:
    files: [junit.xml]
    base-directory: reports
    file-format: JUNITXML
artifacts:
  files: [packaged.yaml]
cache:
  paths: ["/root/.cache/pip/**/*"]
```

- `buildspec.yml` at the source root (or another path, or inline in the project). Phases run in order:
  **install → pre_build → build → post_build** (`finally` blocks and `on-failure` behaviors are available).
- **Environment**: managed images (Amazon Linux, Ubuntu, Windows) or a custom image from ECR/Docker Hub,
  compute size, **privileged mode for building Docker images**, and a **VPC configuration** to reach private
  resources (RDS, internal endpoints).
- **Secrets**: never in plaintext `variables`. Use `parameter-store` / `secrets-manager` mappings (exercise `cicd_1`).
- **Service role**: CodeBuild's IAM role must allow what the build does (write to S3/ECR, read parameters,
  write CloudWatch logs).
- **Artifacts** (to S3, or picked up by CodePipeline), **cache** (S3 or local: source, Docker layers, custom
  paths) for faster builds, **test reports** (JUnit, Cucumber, TestNG, NUnit, code coverage) shown in the console.
- Logs in **CloudWatch Logs** and/or S3. Build timeouts are configurable. Run the same build locally with the CodeBuild agent.
- Triggers: CodePipeline, webhooks (GitHub/GitLab/Bitbucket PRs and pushes), EventBridge schedules, the API.

> **Exam tip** — "The build needs a database password" → `env.secrets-manager` or `env.parameter-store`
> in the buildspec, plus permission in the CodeBuild service role. "Docker build fails with 'Cannot connect
> to the Docker daemon'" → enable **privileged mode**.

## CodeDeploy

Automates deployments to **EC2/on-premises**, **Lambda** and **ECS**.

| Concept | Meaning |
|---|---|
| **Application** | A name + compute platform |
| **Deployment group** | The targets (EC2 tags, Auto Scaling groups, a Lambda function, an ECS service), deployment config, load balancer, **alarms**, **rollback settings**, triggers |
| **Revision** | What to deploy: app bundle + `appspec.yml` (S3 or GitHub), or the AppSpec content for Lambda/ECS |
| **Deployment configuration** | How fast: EC2 `AllAtOnce`, `HalfAtATime`, `OneAtATime`, or a custom minimum healthy hosts. Lambda/ECS: `Canary10Percent5Minutes`, `Linear10PercentEvery1Minute`, `AllAtOnce`... |

### EC2/on-premises

- Requires the **CodeDeploy agent** on instances, and an **instance profile** allowing the agent to read the
  revision from S3.
- **In-place**: stop the app on each instance, install the new version, restart (by batches per the config).
  **Blue/green** (EC2 with Auto Scaling + load balancer): provision new instances, deploy, reroute traffic,
  then terminate the old ones.
- **AppSpec (YAML)**:

```yaml
version: 0.0
os: linux
files:
  - source: /
    destination: /var/www/app
hooks:
  BeforeInstall:
    - location: scripts/install_dependencies.sh
      timeout: 300
      runas: root
  ApplicationStart:
    - location: scripts/start_server.sh
  ValidateService:
    - location: scripts/health_check.sh
```

- **Lifecycle event order, in-place** (exercise `cicd_2`):
  `ApplicationStop → DownloadBundle → BeforeInstall → Install → AfterInstall → ApplicationStart → ValidateService`.
  With a load balancer: `BeforeBlockTraffic → BlockTraffic → AfterBlockTraffic` first, and
  `BeforeAllowTraffic → AllowTraffic → AfterAllowTraffic` last. `DownloadBundle`, `Install`, `BlockTraffic`
  and `AllowTraffic` are reserved for the agent (no scripts).

### Lambda and ECS

- **Lambda**: shifts an **alias** between two versions (canary/linear/all-at-once). AppSpec lists the function,
  alias, current and target versions, and hooks **`BeforeAllowTraffic`** / **`AfterAllowTraffic`** (Lambda
  functions that run validations). SAM generates all of this (chapter 16).
- **ECS blue/green**: a new task set (green) is created behind the load balancer's **test listener**, then
  production traffic shifts (canary/linear/all-at-once). Hooks: `BeforeInstall`, `AfterInstall`,
  `AfterAllowTestTraffic`, `BeforeAllowTraffic`, `AfterAllowTraffic`.

### Rollbacks and troubleshooting

- **Automatic rollback** when a deployment fails or a **CloudWatch alarm** fires. A rollback is a **new
  deployment** of the last known good revision.
- Common failures:
  - agent not installed/running, or the instance profile cannot read the S3 revision,
  - a hook script fails or **times out** (check `/var/log/aws/codedeploy-agent/` and the deployment logs),
  - **`ApplicationStop` runs the script from the *previously deployed* revision**: a broken old script makes
    every new deployment fail. Fix it, or ignore ApplicationStop failures for that deployment,
  - files already exist at the destination (choose the file-exists behavior: fail/overwrite/retain).

## CodePipeline

Orchestrates the release process as **stages** (at least 2) made of **actions**:

| Action category | Providers (examples) |
|---|---|
| **Source** | CodeCommit, S3, ECR, GitHub/GitLab/Bitbucket (CodeConnections) |
| **Build / Test** | CodeBuild, Jenkins, third parties |
| **Deploy** | **CloudFormation** (`CREATE_UPDATE`, `CHANGE_SET_REPLACE` + `CHANGE_SET_EXECUTE`, `DELETE_ONLY`), CodeDeploy, ECS (rolling) and ECS blue/green, Elastic Beanstalk, S3, AppConfig, Service Catalog |
| **Approval** | **Manual approval**: optional SNS notification, review URL, comments. Approvers need `codepipeline:PutApprovalResult`. Pending approvals expire after **7 days** |
| **Invoke** | Lambda, Step Functions |

- **Artifacts** flow between actions through the **S3 artifact store** (encrypted with KMS). Name each output
  artifact and use it as input downstream (`BuildOutput::packaged.yaml`).
- Actions with the same `runOrder` run **in parallel**. Increasing `runOrder` runs them **sequentially** (exercise `cicd_4`).
- **Triggers**: source change events (EventBridge for CodeCommit/S3/ECR, webhooks/CodeConnections for Git hosts).
  **V2 pipelines** add trigger **filters** (branches, tags, file paths, pull request events), pipeline-level
  **variables**, and execution modes (queued, superseded, parallel).
- **Cross-Region** actions need an artifact bucket per Region. **Cross-account** deployments need a
  **customer managed KMS key** (shared with the target account) for artifacts, plus a role in the target
  account that the pipeline assumes.
- Monitoring: pipeline/stage/action **state change events in EventBridge** (→ SNS, chat notifications),
  disable transitions between stages to pause releases.

> **Exam tip** — "A human must approve before production" → a **manual approval action** (with SNS).
> "Notify the team when a pipeline fails" → **EventBridge rule** on pipeline execution state changes → SNS
> (or a notification rule).

## CodeArtifact

A managed **artifact repository** for npm, PyPI, Maven/Gradle, NuGet, Swift and generic packages:

- **Domains** (shared storage, KMS-encrypted) contain **repositories**. **Upstream repositories** and
  **external connections** proxy and cache public registries (npmjs, PyPI, Maven Central).
- Authentication: `aws codeartifact login --tool pip|npm|twine --domain my-domain --repository my-repo`
  (a token valid up to 12 hours). Works in CodeBuild with the service role.
- Use cases: private libraries shared between teams, controlled/approved open-source dependencies,
  builds that keep working when a public registry is down.

## Deployment strategies (map)

| Strategy | Idea | Where on AWS |
|---|---|---|
| **All at once** | Replace everything simultaneously. Downtime, fastest | Beanstalk AllAtOnce, CodeDeploy AllAtOnce, Lambda alias switch |
| **Rolling** | Update in batches, reduced capacity | Beanstalk Rolling, CodeDeploy OneAtATime/HalfAtATime, ECS rolling update |
| **Rolling with additional batch** | Add a batch first, full capacity | Beanstalk |
| **Immutable** | New instances in a new ASG, swap, then terminate the old ones | Beanstalk Immutable |
| **Blue/green** | Two environments, switch traffic at once, keep blue for rollback | CodeDeploy EC2/ECS blue/green, Beanstalk swap URLs, Route 53 weighted records |
| **Canary** | A small percentage first, then everything | Lambda aliases (CodeDeploy/SAM), ECS blue/green, API Gateway canary, Beanstalk traffic splitting, AppConfig |
| **Linear** | Equal increments at fixed intervals | Lambda/ECS via CodeDeploy, AppConfig |
| **Feature flags** | Deploy dark, enable at runtime | AppConfig |

## Hands-on

| Exercise | Skill |
|---|---|
| `cicd_1` | A buildspec: phases, secrets from Parameter Store, reports, artifacts, cache |
| `cicd_2` | AppSpec files and lifecycle hook order (EC2, ECS, Lambda) |
| `cicd_4` | A pipeline with manual approval and CloudFormation change sets |
| `cicd_3` | Elastic Beanstalk deployment policies (chapter 18) |

Optional lab: `labs/lab04-cicd-pipeline`.

## Summary

- CodeBuild: buildspec phases install → pre_build → build → post_build, secrets via parameter-store/secrets-manager, artifacts, cache, reports, privileged mode for Docker.
- CodeDeploy: EC2/on-prem (agent + instance profile, in-place or blue/green), Lambda and ECS (traffic shifting). AppSpec hooks in a fixed order. Rollback on failure/alarms.
- CodePipeline: stages and actions, S3 artifacts, runOrder, manual approval (SNS, 7 days), EventBridge events, cross-account requires a CMK.
- CodeArtifact: private package repositories with upstream proxies. CodeCommit: IAM-controlled Git, back to GA.

## Check yourself

1. In which order do these EC2 in-place hooks run: AfterInstall, ApplicationStart, BeforeInstall, ValidateService, ApplicationStop?
2. Every deployment fails at `ApplicationStop` since a bad release. Why does fixing the new revision not help?
3. A pipeline must deploy to another AWS account. What is required for the artifacts?
4. How do two test actions run in parallel within a stage?
5. Developers must install private Python packages in CodeBuild without exposing them publicly. Which service?

<details><summary>Answers</summary>

1. ApplicationStop → BeforeInstall → AfterInstall → ApplicationStart → ValidateService.
2. `ApplicationStop` runs the script of the **previously deployed** (broken) revision. Fix or remove that
   script on the instances, or ignore ApplicationStop failures for the next deployment.
3. A **customer managed KMS key** for the artifact bucket, shared with the target account, plus a cross-account
   role that the pipeline assumes (and bucket permissions).
4. Give both actions the **same `runOrder`**.
5. **CodeArtifact** (`aws codeartifact login --tool pip` in the build).

</details>

## Further reading

- [CodeBuild buildspec reference](https://docs.aws.amazon.com/codebuild/latest/userguide/build-spec-ref.html)
- [CodeDeploy AppSpec hooks](https://docs.aws.amazon.com/codedeploy/latest/userguide/reference-appspec-file-structure-hooks.html)
- [CodePipeline concepts](https://docs.aws.amazon.com/codepipeline/latest/userguide/concepts.html)
- [Manual approvals in CodePipeline](https://docs.aws.amazon.com/codepipeline/latest/userguide/approvals.html)
- [CodeArtifact user guide](https://docs.aws.amazon.com/codeartifact/latest/ug/welcome.html)
