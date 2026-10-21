# Lab 06 — Elastic Beanstalk deployments: rolling, immutable, blue/green

> **Goal**: run a web application on Elastic Beanstalk and compare deployment policies with your own
> eyes: a **rolling** deployment (same instances, reduced capacity, mixed versions), an **immutable**
> deployment that **fails without impact** and then succeeds on new instances, and a **blue/green**
> release with **Swap Environment URLs**.
>
> **Book**: ch18 (Elastic Beanstalk), ch17 (deployment strategies) · **Exercises**: `cicd_3`,
> `beanstalk_1` · **Time**: 2–3 h (environments take minutes to create) · **Cost**: about
> $0.15–0.25 per hour while the environments run (load balancers, EC2 instances, public IPv4
> addresses). Terminate them as soon as you finish.

```text
eb deploy ─► application version (S3) ─► environment dva-lab06-blue: ALB + Auto Scaling group (2 × t3.micro)
Rolling:    instance 1 updated, then instance 2 (capacity reduced, versions mixed for a while)
Immutable:  new temporary Auto Scaling group → health checks → swap in, old instances terminated
Blue/green: eb clone → deploy to dva-lab06-green → eb swap (CNAME swap) → rollback = swap again
```

Files: `app/application.py` (a WSGI app with no dependencies), `app/.ebextensions/01-environment.config`,
`ec2-trust.json`, `tests/`.

## 0. One-time setup

1. EB CLI: `uv tool install awsebcli`, then `eb --version`.
2. **Instance profile**. Elastic Beanstalk no longer creates the default EC2 instance profile for
   you. Create it once (run from `labs/lab06-beanstalk-deployments`):

   ```bash
   aws iam get-instance-profile --instance-profile-name aws-elasticbeanstalk-ec2-role >/dev/null 2>&1 || {
     aws iam create-role --role-name aws-elasticbeanstalk-ec2-role --assume-role-policy-document file://ec2-trust.json
     aws iam attach-role-policy --role-name aws-elasticbeanstalk-ec2-role \
         --policy-arn arn:aws:iam::aws:policy/AWSElasticBeanstalkWebTier
     aws iam create-instance-profile --instance-profile-name aws-elasticbeanstalk-ec2-role
     aws iam add-role-to-instance-profile --instance-profile-name aws-elasticbeanstalk-ec2-role \
         --role-name aws-elasticbeanstalk-ec2-role
   }
   ```

   This is the role your application's instances run with: the EC2 equivalent of a Lambda
   execution role.
3. Work on a copy **outside this git repository**. In a git repository, `eb deploy` deploys the last
   commit (not your uncommitted edits):

   ```bash
   cp -r app ~/dva-lab06 && cd ~/dva-lab06
   ```

## 1. Create the application and the environment

```bash
eb init dva-lab06 --platform python-3.13 --region eu-west-3 --profile dva-lab
eb create dva-lab06-blue --elb-type application --instance_type t3.micro \
    --instance_profile aws-elasticbeanstalk-ec2-role
```

If `eb init` rejects the platform name, run `eb platform list` and pick the latest
"Python ... running on 64bit Amazon Linux 2023", or run `eb init` without options and answer the
prompts. If the EB CLI cannot read your SSO profile, export temporary credentials first:
`eval "$(aws configure export-credentials --profile dva-lab --format env)"`.

`eb create` takes 5 to 10 minutes: Beanstalk creates a CloudFormation stack with the load balancer,
the Auto Scaling group (2 instances, from `.ebextensions`), security groups and alarms. Then:

```bash
eb status          # CNAME, health, platform, deployed version
eb health          # enhanced health per instance
URL="http://$(aws elasticbeanstalk describe-environments --environment-names dva-lab06-blue \
      --query 'Environments[0].CNAME' --output text)"
curl -s "$URL"     # {"version": "1", "color": "blue", "instance": "ip-172-31-...", "path": "/"}
```

In a **second terminal**, keep a request loop running for the rest of the lab:

```bash
URL=...   # same value as above
while true; do curl -s -m 2 "$URL" || echo "(no response)"; echo; sleep 1; done
```

Two `instance` values alternate: the load balancer spreads requests over both instances.

## 2. Rolling deployment

Set `VERSION = "2"` in `application.py`, then:

```bash
eb deploy
eb events -f       # in a third terminal: follow the deployment events
```

With `DeploymentPolicy: Rolling` and `BatchSize: 1`, Beanstalk takes one instance out of the load
balancer, deploys, puts it back, then does the next one. In the loop: for a while **only one
instance answers** (reduced capacity), and **versions 1 and 2 are mixed**. The instance names do not
change: the same instances were updated in place.

## 3. Immutable deployment, first broken, then fixed

Switch the policy with a setting applied **directly to the environment**:

```bash
aws elasticbeanstalk update-environment --environment-name dva-lab06-blue \
    --option-settings Namespace=aws:elasticbeanstalk:command,OptionName=DeploymentPolicy,Value=Immutable
aws elasticbeanstalk wait environment-updated --environment-names dva-lab06-blue
```

Settings applied directly (console, CLI, API) **take precedence** over `.ebextensions`, so later
deployments stay immutable even though the file still says `Rolling`. `eb config` shows the result.

Now ship a broken release: set `VERSION = "3"` and `BROKEN = True`, then `eb deploy`.

- Beanstalk launches **new instances in a temporary Auto Scaling group**, behind the same load balancer.
- They answer HTTP 500, fail their health checks, and the deployment **fails** (this can take 10 to
  15 minutes). Beanstalk terminates the temporary instances.
- In the loop, nothing changed: version 2 kept answering from the original instances. A failed
  immutable deployment is cheap to roll back, because nothing was modified.

Fix it: set `BROKEN = False` (keep `VERSION = "3"`), then `eb deploy`. When it completes, the loop
shows version 3 from **new instance names**: immutable deployments replace instances instead of
updating them.

## 4. Blue/green with a CNAME swap

```bash
eb clone dva-lab06-blue --clone_name dva-lab06-green     # 5-10 minutes: same version and settings
eb setenv COLOR=green -e dva-lab06-green
```

Set `VERSION = "4"`, deploy **only to green**, and test it on its own URL:

```bash
eb deploy dva-lab06-green
GREEN="http://$(aws elasticbeanstalk describe-environments --environment-names dva-lab06-green \
        --query 'Environments[0].CNAME' --output text)"
curl -s "$GREEN"     # version 4, color green
```

Production users still see blue (version 3). Release by swapping the CNAMEs:

```bash
eb swap dva-lab06-blue --destination_name dva-lab06-green
```

After a minute or so (DNS caching), the loop on the original URL shows **version 4, color green**.
Rolling back would be the same command again. Both environments keep running until you terminate
one: you pay for both during the transition.

## 5. Explore

- `eb logs` (recent logs of every instance), `eb health --refresh`, `eb config` (every setting).
- EC2 console: the instances, the Auto Scaling groups and the load balancer belong to the
  environments. CloudFormation console: one `awseb-...` stack per environment.
- Optional: try `DeploymentPolicy=TrafficSplitting` (a canary inside one environment): set it the
  same way as Immutable, add the options `NewVersionPercent` and `EvaluationTime` in the
  `aws:elasticbeanstalk:trafficsplitting` namespace, and deploy a new version.

## Teardown

```bash
eb terminate dva-lab06-green --force
eb terminate dva-lab06-blue --force
cd ~ && rm -rf ~/dva-lab06
```

Check in the Beanstalk console that both environments show **Terminated** (it takes a few minutes).
The application versions stay in an `elasticbeanstalk-eu-west-3-<account id>` S3 bucket (a few
KB). You can delete the application in the console (*Actions → Delete application*). The
`aws-elasticbeanstalk-ec2-role` instance profile costs nothing; keep it or delete it.

## What to remember for the exam

| Policy | Downtime | Capacity during the deployment | Rollback | Extra cost |
|---|---|---|---|---|
| All at once | yes | none during the switch | redeploy | none |
| Rolling | no | reduced (one batch out) | redeploy | none |
| Rolling with additional batch | no | full | redeploy | one extra batch |
| Immutable | no | full + temporary new instances | fast: terminate the new instances | double, briefly |
| Traffic splitting | no | full + new instances getting a % of traffic | fast: shift traffic back | double, briefly |
| Blue/green (swap URLs) | no | two full environments | swap again | two environments |

- `.ebextensions/*.config` sit at the **root of the source bundle**. Settings applied directly to the
  environment override them.
- Each environment = a CloudFormation stack (ALB, Auto Scaling group, instances). The instances need
  an **instance profile**.
- Blue/green on Beanstalk = **clone + Swap Environment URLs**. DNS caching delays the switch.
