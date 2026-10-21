# Elastic Beanstalk and containers

> **In this chapter**
> - Elastic Beanstalk: applications, environments, web vs worker tiers, configuration files, deployment policies, blue/green
> - Containers on AWS: ECR, ECS (EC2 and Fargate), task definitions, task role vs execution role, services
> - EKS and App Runner in one paragraph each
>
> **Exam weight**: Domain 3 Tasks 3.1/3.4 (container images, application resources, deployment strategies)
> · **Exercises**: `cicd_3`, `ecs_1`, `beanstalk_1` · **Quiz**: `uv run awslings quiz containers`

## AWS Elastic Beanstalk

A **PaaS**: you upload code, and Beanstalk provisions and manages the EC2 instances, Auto Scaling group,
load balancer, monitoring and platform updates through CloudFormation. You keep full access to the
underlying resources. You pay only for those resources.

- **Application** → **application versions** (your bundles in S3) → **environments** (a running version).
  Application version **lifecycle policies** clean up old versions (there is a quota on stored versions).
- **Platforms**: Java, .NET, Node.js, Python, PHP, Ruby, Go, Docker (single container, or several via the
  ECS-based Docker platform), Tomcat...
- **Environment tiers**:
  - **Web server**: ALB/NLB + Auto Scaling group (or a single instance for dev),
  - **Worker**: pulls messages from an **SQS queue** through the **sqsd daemon**, which POSTs each message to
    your app (HTTP 200 = delete, error = retry/DLQ). Periodic tasks are declared in **`cron.yaml`**.
    Decouple long tasks from the web tier this way.
- **Configuration**:
  - **`.ebextensions/*.config`** (YAML/JSON) at the **root of the source bundle**: `option_settings`
    (namespaces such as `aws:elasticbeanstalk:application:environment` for environment properties,
    `aws:autoscaling:asg`, `aws:elasticbeanstalk:command` for the deployment policy,
    `aws:elasticbeanstalk:xray`), packages, files, commands, extra resources (exercise `beanstalk_1`),
  - **platform hooks** (`.platform/hooks/`) and `Procfile` on Amazon Linux 2/2023 platforms,
  - **saved configurations**, and environment properties (environment variables) in the console/CLI,
  - precedence: settings applied directly to the environment > saved configurations > `.ebextensions` > defaults.
- **Databases**: an RDS instance created **inside** the environment is deleted with it. For production,
  create RDS separately and pass its endpoint through environment properties (or Secrets Manager).
- CLI: `eb init`, `eb create`, `eb deploy`, `eb logs`, `eb ssh`, `eb swap`.
- **Managed platform updates** apply patches in a maintenance window. Enhanced health reporting.
- **X-Ray**: enable the daemon with `XRayEnabled: true` (namespace `aws:elasticbeanstalk:xray`) and instrument the code.

### Deployment policies

| Policy | Downtime | Capacity during deployment | Rollback | Extra cost |
|---|---|---|---|---|
| **All at once** | **Yes** | 0 during the switch | Redeploy the old version | None |
| **Rolling** | No | **Reduced** (one batch out at a time) | Redeploy | None |
| **Rolling with additional batch** | No | **Full** (launch an extra batch first) | Redeploy | One extra batch during the deployment |
| **Immutable** | No | Full, plus a **new temporary ASG** with new instances | **Fast**: terminate the new ASG | Double capacity briefly |
| **Traffic splitting** (canary) | No | Full, plus new instances receiving a **% of traffic** | Fast: shift traffic back | Double capacity briefly |

**Blue/green** with Beanstalk: clone the environment (green), deploy the new version there, test, then
**Swap Environment URLs** (a CNAME swap). Roll back by swapping again. Watch DNS TTLs: the switch is not instantaneous for every client.

> **Exam tip** — "Minimize impact of a failed deployment, fastest rollback, instances never mixed" →
> **Immutable**. "No downtime, keep full capacity, low extra cost" → **Rolling with additional batch**.
> "Test the new version with 10% of real traffic" → **Traffic splitting**. "Fastest, dev environment" → **All at once** (exercise `cicd_3`).

## Containers on AWS

### Amazon ECR

A private (and public) **container registry**:

- `aws ecr get-login-password --region eu-west-3 | docker login --username AWS --password-stdin <account>.dkr.ecr.eu-west-3.amazonaws.com`
- **Image scanning** (basic, or enhanced with Amazon Inspector) for vulnerabilities.
- **Tag immutability** (a tag like `1.4.2` can never be overwritten, so deploy by tag safely, or by **digest**).
- **Lifecycle policies** expire old/untagged images. Cross-Region/cross-account **replication**. Repository policies for cross-account pulls.

### Amazon ECS

| Concept | Meaning |
|---|---|
| **Cluster** | A logical group of capacity |
| **Launch type / capacity provider** | **EC2** (you manage instances running the ECS agent) or **Fargate** (serverless: no instances to manage, pay per vCPU/memory per second) |
| **Task definition** | JSON blueprint: container images, CPU/memory, ports, environment, secrets, log configuration, **IAM roles**, network mode. Versioned (revisions) |
| **Task** | A running instance of a task definition (one or more containers) |
| **Service** | Keeps N tasks running, replaces failed ones, integrates with an **ALB/NLB**, scales with **Service Auto Scaling**, does rolling updates or blue/green deployments (CodeDeploy) |

**The two roles** (exercise `ecs_1`):

| Role | Used by | Needs |
|---|---|---|
| **Task execution role** | The ECS agent / Fargate, **before and around** your containers | Pull images from ECR, write logs to CloudWatch (`awslogs`), read **secrets** to inject (Secrets Manager, Parameter Store, KMS decrypt) |
| **Task role** | **Your application code** inside the container | What the app calls: S3, DynamoDB, SQS... (credentials served through the container credentials endpoint) |

> **Trap** — "The container cannot pull its image / logs never appear / secrets are not injected" → the
> **task execution role**. "The application gets AccessDenied calling DynamoDB" → the **task role**.

**Task definition highlights**:

```json
{
  "family": "web", "requiresCompatibilities": ["FARGATE"], "networkMode": "awsvpc",
  "cpu": "512", "memory": "1024",
  "executionRoleArn": "arn:aws:iam::123456789012:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::123456789012:role/web-app",
  "containerDefinitions": [{
    "name": "web", "image": "123456789012.dkr.ecr.eu-west-3.amazonaws.com/web:1.4.2", "essential": true,
    "portMappings": [{"containerPort": 8080}],
    "environment": [{"name": "STAGE", "value": "prod"}],
    "secrets": [{"name": "DB_PASSWORD", "valueFrom": "arn:aws:ssm:eu-west-3:123456789012:parameter/web/prod/db_password"}],
    "logConfiguration": {"logDriver": "awslogs", "options": {"awslogs-group": "/ecs/web", "awslogs-region": "eu-west-3", "awslogs-stream-prefix": "web"}}
  }]
}
```

- **Fargate** requires `awsvpc` networking (each task gets its own ENI and security groups) and a valid
  **CPU/memory combination** (e.g. 0.25 vCPU with 0.5–2 GB, 0.5 vCPU with 1–4 GB, 1 vCPU with 2–8 GB...).
- **EC2 launch type**: `bridge` networking with **dynamic host port mapping** lets several tasks share an
  instance behind an ALB. **Placement strategies**: `binpack` (pack tightly by CPU/memory, cheapest),
  `spread` (across AZs/instances, highest availability), `random`. **Placement constraints**:
  `distinctInstance`, `memberOf` (cluster query language expressions).
- **Logging**: the `awslogs` driver (CloudWatch Logs), or **FireLens** (Fluent Bit) to route logs anywhere.
- **Secrets** are injected at container start. Restart the tasks to pick up rotated values.
- **Deployments**: rolling update (`minimumHealthyPercent` / `maximumPercent`, deployment circuit breaker
  with automatic rollback), or **blue/green with CodeDeploy** (test listener, canary/linear traffic shifting).
- Service Auto Scaling: target tracking on CPU/memory or ALB requests per target. **Fargate Spot** for interruptible workloads.
- Observability: CloudWatch **Container Insights**, X-Ray/ADOT as a **sidecar** container.

### EKS and App Runner

- **Amazon EKS**: managed Kubernetes control plane. Workers on EC2 node groups or Fargate. Pods get AWS
  permissions through **IAM roles for service accounts (IRSA)** or **EKS Pod Identity**. Choose it when the team
  already uses Kubernetes or needs its ecosystem.
- **AWS App Runner**: deploy a web app or API from source code or a container image. It handles build,
  TLS, load balancing and auto scaling. The simplest container option (less control).

| Need | Choose |
|---|---|
| Upload code, get a managed web stack with full control of resources | **Elastic Beanstalk** |
| Run containers without managing servers, AWS-native | **ECS on Fargate** |
| Kubernetes | **EKS** |
| Simplest container web service from source/image | **App Runner** |
| Event-driven, short tasks | **Lambda** (chapter 5) |

## Hands-on

| Exercise | Skill |
|---|---|
| `cicd_3` | Choosing a Beanstalk deployment policy, serving capacity during deployments |
| `ecs_1` | Fargate task definition: valid sizes, execution role vs task role, secrets, awslogs |
| `beanstalk_1` | `.ebextensions` option settings and worker `cron.yaml` |

Optional lab: `labs/lab06-beanstalk-deployments`.

## Summary

- Beanstalk = managed platform on your resources. Web tier vs worker tier (SQS + sqsd + cron.yaml). `.ebextensions/*.config` at the bundle root.
- Deployment policies: all at once (downtime), rolling (reduced capacity), rolling + batch (full capacity), immutable (fast rollback), traffic splitting (canary). Blue/green = swap URLs.
- ECR: scanning, tag immutability, lifecycle policies. ECS: task definitions, services, EC2 vs Fargate.
- Task **execution** role = pull image, logs, secrets. **Task** role = the app's AWS permissions.

## Check yourself

1. A Beanstalk deployment must never mix old and new versions on the same environment, and rollback must be fast. Which policy?
2. Where do Beanstalk configuration files go, and which extension do they need?
3. An ECS task on Fargate fails with "unable to pull secrets or registry auth". Which role is missing permissions?
4. Long-running jobs slow down a Beanstalk web application. What Beanstalk feature helps?
5. How do you run several copies of the same container port on one EC2 instance behind an ALB?

<details><summary>Answers</summary>

1. **Immutable** (or traffic splitting / blue-green).
2. In the `.ebextensions/` folder at the root of the source bundle, with the `.config` extension.
3. The **task execution role** (ECR pull, Secrets Manager/SSM read, KMS decrypt).
4. A **worker environment**: the web tier enqueues jobs to SQS, and the worker tier processes them (sqsd).
5. `bridge` network mode with **dynamic host port mapping** (host port 0). The ALB target group registers the ephemeral ports.

</details>

## Further reading

- [Elastic Beanstalk developer guide](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/Welcome.html)
- [Deployment policies and settings](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/using-features.rolling-version-deploy.html)
- [Amazon ECS developer guide](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/Welcome.html)
- [ECS task execution IAM role](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_execution_IAM_role.html) and [task IAM role](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-iam-roles.html)
- [Amazon ECR user guide](https://docs.aws.amazon.com/AmazonECR/latest/userguide/what-is-ecr.html)
