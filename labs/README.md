# Optional labs on a real AWS account

The awslings exercises run offline against moto. These labs are the complement: you deploy small
applications to a **real AWS account**, break them on purpose, and watch AWS react. They are
optional. Do them when you have a free afternoon, ideally the weekend of the matching week of
`STUDY_PLAN.md`.

| Lab | What you build and observe | Book | Time | Cost if you tear down the same day |
|---|---|---|---|---|
| [lab00-account-setup](lab00-account-setup/README.md) | Budget alert, admin access with MFA, CLI profiles | ch01–ch03 | 45 min | $0 |
| [lab01-serverless-api](lab01-serverless-api/README.md) | SAM: API Gateway + Lambda + DynamoDB, canary deployment with alarm rollback | ch05, ch06, ch16 | 1.5 h | < $0.10 |
| [lab02-cognito-auth](lab02-cognito-auth/README.md) | User pool, sign-up/sign-in from the CLI, JWT claims, Cognito authorizer, groups | ch06, ch12 | 1 h | < $0.10 |
| [lab03-event-driven](lab03-event-driven/README.md) | S3 → EventBridge → Step Functions → Lambda/DynamoDB/SNS/SQS, Retry/Catch | ch04, ch09, ch10 | 1.5 h | < $0.10 |
| [lab04-cicd-pipeline](lab04-cicd-pipeline/README.md) | CodeCommit → CodeBuild (tests + package) → CloudFormation change sets + manual approval | ch15, ch17 | 2 h | < $0.50 |
| [lab05-observability](lab05-observability/README.md) | X-Ray traces and annotations, EMF metrics, Logs Insights, metric filter alarm, dashboard | ch20, ch21 | 1.5 h | < $0.20 |
| [lab06-beanstalk-deployments](lab06-beanstalk-deployments/README.md) | Elastic Beanstalk: rolling vs immutable deployments, failed deployment, blue/green swap | ch18 | 2–3 h | about $0.15–0.25 per hour while running |

Costs are rough estimates for the eu-west-3 (Paris) Region at the time of writing, assuming you delete
everything at the end of the lab. Most usage fits in the AWS Free Tier. Always check the pricing pages
and your bill. The **teardown** section of each lab is not optional.

## Prerequisites

1. **lab00 first**: an account with a budget alert, an admin identity with MFA, and a CLI profile.
2. Tools on your computer:
   - **AWS CLI v2**: `aws --version` (install guide: <https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html>)
   - **AWS SAM CLI** (labs 01, 02, 03, 05): `sam --version` (<https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html>)
   - **Python 3.13** for `sam build` (or Docker with `sam build --use-container`)
   - **Docker** (optional): only for `sam local invoke` / `sam local start-api`
   - **git** and **git-remote-codecommit** (lab04): `uv tool install git-remote-codecommit`
   - **EB CLI** (lab06): `uv tool install awsebcli`, then `eb --version`
3. Set your profile and Region once per terminal:

   ```bash
   export AWS_PROFILE=dva-lab        # the profile created in lab00
   export AWS_REGION=eu-west-3       # every lab uses Paris by default
   aws sts get-caller-identity       # must print your account, not an error
   ```

Run the commands of a lab from that lab's folder (`cd labs/lab01-serverless-api`) unless the lab
says otherwise.

## Safety rules

- **Tear down** at the end of every lab (each README ends with the exact commands), then check the
  next day in *Billing and Cost Management → Bills* that nothing keeps running.
- **Never commit credentials.** `samconfig.toml` and `.aws-sam/` are ignored by git, because
  `sam deploy --guided` writes your choices there.
- Use the **budget alert** from lab00. If it fires, open Cost Explorer, find the service, and delete
  what you forgot.
- Labs create IAM roles for their own resources. Read the templates: they are part of the lesson
  (least-privilege policies, SAM policy templates, trust policies).

## Unit tests without AWS

The Lambda code of the labs has unit tests that run offline with moto, like the exercises:

```bash
uv run pytest labs            # from the repository root
```

Templates are checked with cfn-lint: `uv run cfn-lint labs/*/template.yaml labs/lab04-cicd-pipeline/pipeline.yaml labs/lab04-cicd-pipeline/app/template.yaml`.

## Find leftovers

```bash
aws cloudformation list-stacks --query "StackSummaries[?StackStatus!='DELETE_COMPLETE' && starts_with(StackName, 'dva-lab')].[StackName,StackStatus]" --output table
aws elasticbeanstalk describe-environments --query "Environments[?Status!='Terminated'].[EnvironmentName,Status]" --output table
```
