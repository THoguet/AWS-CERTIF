# Lab 00 — Account setup: budget, admin access with MFA, CLI profiles

> **Goal**: prepare a safe AWS account for the other labs: a protected root user, a cost alert, an
> admin identity with MFA that you use every day, and a CLI profile.
>
> **Book**: ch01 (accounts, Regions, shared responsibility), ch02 (root user, MFA, roles), ch03 (CLI
> profiles, credential chain, STS) · **Time**: 45 min · **Cost**: $0

If you already have an account with these in place, skip to [Verify](#5-verify).

## 1. Protect the root user

The root user (the email address used to create the account) can do everything, including closing
the account. Use it only for the few tasks that need it.

1. Sign in as root at <https://console.aws.amazon.com/>.
2. Top right menu → **Security credentials** → **Assign MFA device** (authenticator app, passkey or
   security key).
3. On the same page, make sure the root user has **no access keys**. Delete any that exist.
4. *Account* page → **IAM user and role access to Billing information** → **Activate**, so your admin
   identity can see costs without signing in as root.

> **Account plans** — Accounts created since July 2025 start with Free Tier credits and a choice
> between a free plan and a paid plan. On the free plan some services or features may be
> restricted until you upgrade. Check the AWS Free Tier page for the current rules before lab04 and
> lab06.

## 2. Create a cost alert

Still as root (or later as admin), open **Billing and Cost Management → Budgets → Create budget**:

- The **Zero spend budget** template emails you as soon as anything costs more than $0.01. This is
  the right choice while you live on Free Tier credits.
- Or a **Monthly cost budget** (e.g. $10) with alerts at 50% and 100% of actual spend and 100% of
  forecasted spend.

The same budget from the CLI, once your profile works (step 4):

```bash
# use your own email address, without modifying the file in the repository
sed 's/you@example.com/YOUR_EMAIL/g' notifications.json > /tmp/dva-notifications.json
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws budgets create-budget --account-id "$ACCOUNT_ID" \
    --budget file://budget.json \
    --notifications-with-subscribers file:///tmp/dva-notifications.json
aws budgets describe-budgets --account-id "$ACCOUNT_ID" \
    --query 'Budgets[].[BudgetName,BudgetLimit.Amount,BudgetLimit.Unit]' --output table
```

In *Billing preferences*, also turn on **Free Tier usage alerts**.

> **Exam link** — Budgets alert on actual **and forecasted** cost. CloudWatch **billing alarms** use
> the `EstimatedCharges` metric, which exists only in **us-east-1** (ch20).

## 3. Create your admin identity

Pick **one** option.

### Option A (recommended): IAM Identity Center, temporary credentials only

1. Console → **IAM Identity Center** → **Enable**. Choose the **organization instance**: it turns on
   AWS Organizations (free), which Identity Center needs to give access to AWS accounts. Create it in
   **eu-west-3**.
2. **Settings → Authentication → Multi-factor authentication**: require MFA at every sign-in.
3. **Users → Add user**: your name and email. Accept the invitation email and set a password and MFA.
4. **Permission sets → Create permission set → Predefined → AdministratorAccess**. Raise the session
   duration to 8 hours if you like.
5. **AWS accounts** → select your account → **Assign users or groups** → your user → the
   AdministratorAccess permission set.
6. Copy the **AWS access portal URL** from the Settings page (`https://d-xxxxxxxxxx.awsapps.com/start`).
7. Configure the CLI:

   ```text
   $ aws configure sso
   SSO session name (Recommended): dva
   SSO start URL [None]: https://d-xxxxxxxxxx.awsapps.com/start
   SSO region [None]: eu-west-3
   SSO registration scopes [sso:account:access]:
   (a browser window opens: sign in, approve)
   (pick your account and the AdministratorAccess role)
   Default client Region [None]: eu-west-3
   CLI default output format [None]: json
   Profile name [...]: dva-lab
   ```

   Each day, refresh the session with `aws sso login --profile dva-lab`.

### Option B (simpler): an IAM user with MFA and access keys

1. Signed in as root: **IAM → Users → Create user** `dva-admin`, with console access, in a group
   `admins` that has the **AdministratorAccess** policy.
2. Sign in as `dva-admin` → **Security credentials** → **Assign MFA device**.
3. **Create access key** → use case *Command Line Interface*, then:

   ```bash
   aws configure --profile dva-lab     # paste the key id and secret, Region eu-west-3, output json
   ```

4. These are **long-term credentials** stored in `~/.aws/credentials`. Never commit them, and delete
   the key when you are done with the labs.

## 4. Use the profile

```bash
export AWS_PROFILE=dva-lab
export AWS_REGION=eu-west-3
```

Add these lines to your shell profile if you like. Every lab assumes them.

## 5. Verify

```bash
aws sts get-caller-identity
aws configure list
```

Expected output of the first command (option A):

```json
{
    "UserId": "AROAEXAMPLEID:you@example.com",
    "Account": "123456789012",
    "Arn": "arn:aws:sts::123456789012:assumed-role/AWSReservedSSO_AdministratorAccess_0123456789abcdef/you@example.com"
}
```

With option B, the Arn is `arn:aws:iam::123456789012:user/dva-admin`. `aws configure list` shows
where each value comes from (`env`, `config-file`, `shared-credentials-file`, `sso`...).

Now see the precedence rules for yourself:

```bash
aws ec2 describe-availability-zones --query 'AvailabilityZones[].ZoneName'                    # eu-west-3a/b/c
AWS_REGION=us-east-1 aws ec2 describe-availability-zones --query 'AvailabilityZones[].ZoneName' # env var wins over the profile
aws ec2 describe-availability-zones --region eu-west-1 --query 'AvailabilityZones[].ZoneName'  # --region wins over everything
```

## 6. Install the lab tools

```bash
aws --version          # aws-cli/2.x
sam --version          # SAM CLI, labs 01, 02, 03, 05
python3 --version      # 3.13 for sam build (or use Docker: sam build --use-container)
docker --version       # optional: sam local
```

## What to remember for the exam

- The **root user** is for account-level tasks only: MFA, no access keys.
- **Identity Center** users get **temporary credentials** of a role (`AWSReservedSSO_*`). Your CLI
  calls then come from an `assumed-role` session, like an EC2 instance profile or a Lambda function.
- `aws sts get-caller-identity` answers "who am I calling AWS as?". It is the first thing to run when
  you get `AccessDenied`.
- `~/.aws/config` holds profiles (Region, output, SSO settings, role_arn), and `~/.aws/credentials`
  holds access keys. Precedence for the Region: `--region` > `AWS_REGION` / `AWS_DEFAULT_REGION` >
  the profile's `region`. Explicit credentials in environment variables override profiles.

## Teardown

Nothing to delete. Keep the budget and the admin identity for the other labs. After the exam,
delete the IAM user's access keys (option B), or close the account if you created it only for this.
