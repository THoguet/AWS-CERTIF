# Lab 04 — CI/CD pipeline: CodeCommit → CodeBuild → CloudFormation

> **Goal**: build a release pipeline. Each `git push` runs the unit tests and packages the
> application in CodeBuild, deploys it to a **staging** stack, then prepares a **change set** for
> **production** that waits for your **manual approval** before it is executed.
>
> **Book**: ch15 (CloudFormation, change sets, service roles), ch17 (CodeCommit, CodeBuild,
> CodePipeline) · **Exercises**: `cicd_1`, `cicd_4`, `cfn_1` · **Time**: 2 h · **Cost**: < $0.50 if
> deleted the same day

```text
git push ─► CodeCommit ─(EventBridge rule)─► CodePipeline (V2)
   Source ─► Build: CodeBuild (pytest + JUnit report, aws cloudformation package)
          ─► Staging: CloudFormation CREATE_UPDATE stack dva-lab04-staging
          ─► Production: 1. CHANGE_SET_REPLACE  2. Manual approval (SNS email)  3. CHANGE_SET_EXECUTE  (stack dva-lab04-prod)
artifacts: S3 bucket · CloudFormation acts with its own service role (DeployRole)
```

Files: `pipeline.yaml` (the pipeline stack), and `app/` (what you push to CodeCommit: a SAM
template, `buildspec.yml`, the function and its tests).

## 1. Read before you deploy

- `app/buildspec.yml`: phases `install → pre_build → build → post_build`, a test report, and the
  single output artifact `packaged.yaml`.
- `pipeline.yaml`: four stages. The production stage uses `RunOrder` 1, 2 and 3 to run its actions
  in sequence. Three roles: CodeBuild's, CodePipeline's, and `DeployRole`, which CloudFormation
  assumes to create the application stacks (the pipeline may only *pass* it to CloudFormation).

## 2. Deploy the pipeline

```bash
cd labs/lab04-cicd-pipeline
aws cloudformation deploy --template-file pipeline.yaml --stack-name dva-lab04-pipeline \
    --capabilities CAPABILITY_IAM --parameter-overrides ApprovalEmail=you@example.com
```

Confirm the SNS subscription email. A new pipeline starts once by itself: this first execution
**fails at Source** because the repository is still empty. That is expected.

## 3. Push the application

```bash
uv tool install git-remote-codecommit      # once; lets git use your AWS credentials (AWS_PROFILE)
cp -r app /tmp/dva-lab04-app && cd /tmp/dva-lab04-app
git init -b main
git add . && git commit -m "First release"
git remote add origin "codecommit::eu-west-3://dva-lab04-app"
git push -u origin main
```

The push changes the `main` branch, so the EventBridge rule starts the pipeline.

## 4. Follow the release

```bash
state() { aws codepipeline get-pipeline-state --name dva-lab04-pipeline \
          --query 'stageStates[].[stageName, latestExecution.status]' --output table; }
state
```

- **Build**: open the build in the CodeBuild console. Read the phase durations and the log, then
  the **Reports** tab (4 passed tests).
- **Staging**: once it succeeds, call the staging API:

  ```bash
  URL=$(aws cloudformation describe-stacks --stack-name dva-lab04-staging \
        --query "Stacks[0].Outputs[?OutputKey=='HelloUrl'].OutputValue" --output text)
  curl -s "$URL?name=Ada"        # {"message": "Hello, Ada, from staging!", "release": "1"}
  ```

- **Production**: `CreateChangeSet` creates the change set, then the pipeline waits at `Approve` and
  emails you. In the CloudFormation console, open stack `dva-lab04-prod` (status
  `REVIEW_IN_PROGRESS`) → *Change sets* → `dva-lab04-prod-release` and read the planned changes.

Approve from the console (*Review → Approve*), or from the CLI:

```bash
TOKEN=$(aws codepipeline get-pipeline-state --name dva-lab04-pipeline \
  --query "stageStates[?stageName=='Production'].actionStates[] | [?actionName=='Approve'].latestExecution.token | [0]" \
  --output text)
aws codepipeline put-approval-result --pipeline-name dva-lab04-pipeline --stage-name Production \
  --action-name Approve --token "$TOKEN" --result summary="Staging checked",status=Approved
```

`ExecuteChangeSet` then creates the production stack. Call its `HelloUrl` output the same way.

## 5. Release 2

```bash
cd /tmp/dva-lab04-app
sed -i.bak 's/RELEASE = "1"/RELEASE = "2"/' src/hello.py && rm src/hello.py.bak
git commit -am "Release 2" && git push
```

The **same** `packaged.yaml` goes to staging, then to production after approval: build once, deploy
many. This time the change set shows a **Modify** of the function (new code), not an **Add**.

## 6. A failing test stops the release

```bash
sed -i.bak 's/Hello, {who}/Hi, {who}/' src/hello.py && rm src/hello.py.bak
git commit -am "Change the greeting but not the tests" && git push
```

The `pre_build` phase fails, the build fails, and the pipeline stops at **Build**. Staging and
production keep running release 2. Read the failing test in the **Reports** tab, then undo:

```bash
git revert --no-edit HEAD && git push
```

## 7. Explore

- `aws s3 ls "s3://$(aws cloudformation describe-stacks --stack-name dva-lab04-pipeline --query "Stacks[0].Outputs[?OutputKey=='ArtifactBucketName'].OutputValue" --output text)" --recursive | head -20`:
  the artifacts passed between actions (zipped), and the Lambda packages uploaded by
  `aws cloudformation package`.
- EventBridge console → *Rules*: the rule that starts the pipeline on pushes to `main`.
- Reject an approval and see the execution fail. Or click **Disable transition** between Staging
  and Production to pause releases.
- In IAM, compare `DeployRole` (what CloudFormation may create) with `PipelineRole` (it cannot create
  a Lambda function itself, it can only pass `DeployRole` to CloudFormation).

## Teardown (order matters)

The application stacks were created with `DeployRole`, and CloudFormation needs that role again to
delete them. Delete them **before** the pipeline stack, which owns the role:

```bash
aws cloudformation delete-stack --stack-name dva-lab04-prod
aws cloudformation delete-stack --stack-name dva-lab04-staging
aws cloudformation wait stack-delete-complete --stack-name dva-lab04-prod
aws cloudformation wait stack-delete-complete --stack-name dva-lab04-staging

BUCKET=$(aws cloudformation describe-stacks --stack-name dva-lab04-pipeline \
         --query "Stacks[0].Outputs[?OutputKey=='ArtifactBucketName'].OutputValue" --output text)
aws s3 rm "s3://$BUCKET" --recursive
aws cloudformation delete-stack --stack-name dva-lab04-pipeline
aws cloudformation wait stack-delete-complete --stack-name dva-lab04-pipeline

# log groups created by CodeBuild and Lambda (not owned by any stack)
for g in $(aws logs describe-log-groups --log-group-name-prefix /aws/codebuild/dva-lab04 --query 'logGroups[].logGroupName' --output text) \
         $(aws logs describe-log-groups --log-group-name-prefix /aws/lambda/dva-lab04 --query 'logGroups[].logGroupName' --output text); do
  aws logs delete-log-group --log-group-name "$g"
done
rm -rf /tmp/dva-lab04-app
```

Deleting the pipeline stack also deletes the CodeCommit repository and its history.

## What to remember for the exam

- **buildspec**: `install → pre_build → build → post_build`. A failing command fails the build.
  `reports` for test results, `artifacts` for outputs, environment variables (and `parameter-store` /
  `secrets-manager` for secrets).
- **CodePipeline**: stages contain actions. Artifacts move through the S3 artifact store. Same
  `RunOrder` = parallel, higher `RunOrder` = later. **Manual approval** + SNS, approved with
  `PutApprovalResult` (a token per approval), expires after 7 days.
- **CloudFormation actions**: `CREATE_UPDATE` deploys directly. `CHANGE_SET_REPLACE` then
  `CHANGE_SET_EXECUTE` lets a human review changes. Templates with IAM resources and transforms need
  `CAPABILITY_IAM` and `CAPABILITY_AUTO_EXPAND`.
- A CloudFormation **service role** (`RoleArn`) decides what the stack can create. The caller needs
  only `iam:PassRole` on it. Without the role, the stack cannot be updated or deleted.
- CodeCommit pushes → **EventBridge** → `StartPipelineExecution` (instead of polling).
