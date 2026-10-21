# AWS foundations for developers

> **In this chapter**
> - Regions, Availability Zones, edge locations, ARNs and the shared responsibility model
> - The networking a developer must know: VPC, subnets, security groups, NAT, VPC endpoints
> - EC2 essentials: instance metadata (IMDSv2), instance profiles, user data, Auto Scaling
> - Load balancers and Route 53 from an application point of view
>
> **Exam weight**: background for every domain (VPC access from Lambda is explicitly in Task 1.2)
> · **Quiz**: `uv run awslings quiz foundations`

This chapter is a refresher on the platform underneath everything else. The exam rarely
asks pure infrastructure questions, but these concepts are the context of many developer
questions ("the Lambda function in a VPC cannot reach DynamoDB...").

## Global infrastructure

| Concept | What it is | Developer impact |
|---|---|---|
| **Region** | A geographic area (e.g. `eu-west-3` Paris) with several isolated AZs | Choose by latency to users, data residency/compliance, service availability, price. Most resources are regional |
| **Availability Zone (AZ)** | One or more data centers with independent power and networking, connected by low-latency links | Deploy across ≥ 2 AZs for high availability (ALB, ASG, RDS Multi-AZ) |
| **Edge location / PoP** | Hundreds of sites used by CloudFront, Route 53, Global Accelerator | Caching close to users, DNS |
| **Local Zones / Wavelength** | Extensions of a Region closer to specific cities / 5G networks | Rare in the exam |

**Global vs regional services**: IAM, Route 53, CloudFront and WAF for CloudFront are *global*.
S3 bucket **names** are globally unique, but a bucket and its data live in one Region.
Most other services (Lambda, DynamoDB, SQS...) are regional: an SQS queue in `eu-west-1` is
invisible from an SDK client configured for `eu-west-3`.

> **Trap** — "The application cannot find the queue/table/function" is often a **region**
> mismatch in the client configuration, not a permission problem.

### Amazon Resource Names (ARNs)

```text
arn:partition:service:region:account-id:resource
arn:aws:lambda:eu-west-3:123456789012:function:orders:live     ← function alias
arn:aws:dynamodb:eu-west-3:123456789012:table/Orders/index/*    ← all indexes of a table
arn:aws:s3:::my-bucket/reports/*                                ← S3: no region, no account
arn:aws:iam::123456789012:role/app-role                         ← IAM: global, no region
```

Partitions: `aws` (commercial), `aws-cn` (China), `aws-us-gov` (GovCloud).

## Shared responsibility model

AWS is responsible for security **of** the cloud (hardware, facilities, the virtualization layer,
managed service internals). You are responsible for security **in** the cloud: your data, IAM,
encryption choices, network rules, and your code. How much you manage depends on the service:

| | EC2 | Elastic Beanstalk / ECS on EC2 | Lambda, DynamoDB, S3 |
|---|---|---|---|
| OS patching | **You** | You (managed updates available) | AWS |
| Runtime / platform | **You** | Platform updates (managed) | AWS (until a runtime is deprecated) |
| Your code, IAM, data, encryption | You | You | You |

## Accounts and quotas

- **Root user**: the email that created the account. Enable MFA, never use it day to day, and never create access keys for it.
- **AWS Organizations** groups accounts. **Service Control Policies (SCPs)** set the *maximum*
  permissions in member accounts (guardrails). They never grant anything on their own.
- **Service quotas**: most limits are *soft* (raise them through the Service Quotas console or
  support), some are *hard*. Exceeding a request-rate quota gives **throttling** errors
  (`ThrottlingException`, HTTP 429/503), which your code should retry with backoff (chapter 3).

## Networking for developers

### VPC building blocks

```text
                         Internet
                            │
                     Internet Gateway
                            │
   ┌──────────────── VPC 10.0.0.0/16 ─────────────────┐
   │  Public subnet 10.0.1.0/24     Private subnet 10.0.2.0/24
   │  (route 0.0.0.0/0 → IGW)       (route 0.0.0.0/0 → NAT GW)
   │  ┌─────────┐ ┌─────────┐       ┌──────────────┐ ┌────────┐
   │  │  ALB    │ │ NAT GW  │◄──────│ Lambda ENIs, │ │  RDS   │
   │  └─────────┘ └─────────┘       │ EC2, ECS     │ └────────┘
   │                                └──────────────┘
   │  Gateway endpoint (S3, DynamoDB): route table entry, free
   │  Interface endpoint (most other services): ENI with private IP (PrivateLink), paid
   └──────────────────────────────────────────────────┘
```

- **Public subnet**: its route table sends `0.0.0.0/0` to an Internet Gateway.
- **Private subnet**: no direct route from the internet. Outbound internet goes through a
  **NAT gateway** (managed, in a public subnet, billed per hour + per GB).
- **Security groups**: *stateful* (replies are allowed automatically), **allow rules only**,
  attached to ENIs (instances, Lambda ENIs, RDS...). Rules can reference another security group
  ("allow 5432 from the app's SG"), which is the clean way to connect tiers.
- **Network ACLs**: *stateless* (allow return traffic explicitly), allow **and** deny rules,
  evaluated in number order, at the subnet level.
- **VPC endpoints** let resources in private subnets reach AWS services without internet:
  - **Gateway endpoints**: **S3 and DynamoDB only**, free, added to route tables.
  - **Interface endpoints** (AWS PrivateLink): an ENI with a private IP for SQS, SNS, KMS, Secrets
    Manager, STS... Charged per hour and per GB.
- **VPC Flow Logs** capture IP traffic metadata (accepted/rejected) to CloudWatch Logs or S3. Use them for network troubleshooting.

### Lambda and VPCs

By default a Lambda function runs in an AWS-managed VPC **with internet access** but **cannot
reach your private resources** (RDS in a private subnet, ElastiCache...). If you attach it to your
VPC (subnets + security groups):

- it can reach private resources (Lambda creates **Hyperplane ENIs** shared per subnet/SG pair),
- it **loses internet access** unless the subnets route to a **NAT gateway**, so calls to public AWS
  endpoints (DynamoDB, SQS, S3...) time out unless you add a NAT gateway **or VPC endpoints**,
- the execution role needs `ec2:CreateNetworkInterface`, `DescribeNetworkInterfaces`,
  `DeleteNetworkInterface` (the managed policy `AWSLambdaVPCAccessExecutionRole` has them).

> **Exam tip** — "Lambda in a VPC times out when calling DynamoDB/S3" → add a **gateway VPC
> endpoint** (cheapest) or a NAT gateway. Attaching a Lambda function to a **public** subnet
> does NOT give it internet access (its ENIs have no public IP).

## EC2 essentials

- **AMI**: the image an instance boots from. **Instance type**: CPU/memory family (t, m, c, r, g...).
  Graviton (`*g` types, arm64) usually offers better price/performance.
- **User data**: a script that runs **once, as root, at first boot**. Use it for bootstrapping (install packages, pull code).
- **Instance metadata service (IMDS)**: `http://169.254.169.254/latest/...` returns instance id,
  AZ, user data, and the **temporary credentials of the instance profile role**.
  **IMDSv2** requires a session token (`PUT /latest/api/token`, then the `X-aws-ec2-metadata-token`
  header) and protects against SSRF attacks. You can enforce IMDSv2-only.
- **Instance profile**: the container that attaches an IAM role to an instance. The SDK picks up
  the role credentials from IMDS automatically (chapter 3). **Never put access keys on an instance.**
- **Storage**: EBS volumes (network block storage, one AZ, persist independently, snapshots to S3),
  instance store (physically attached, **ephemeral**: lost on stop/terminate), EFS (shared NFS
  across AZs and instances, also mountable by Lambda and ECS).

### Auto Scaling groups

An **ASG** keeps a fleet between *min* and *max*, replaces unhealthy instances, and spreads them
across AZs. It launches instances from a **launch template**.
Scaling policies: **target tracking** (e.g. keep average CPU at 50%, the simplest),
**step/simple** scaling (CloudWatch alarm thresholds), **scheduled** scaling, **predictive** scaling.
Health checks: EC2 status checks by default, or **ELB health checks** (recommended behind a load balancer).

## Elastic Load Balancing

| | Application Load Balancer (ALB) | Network Load Balancer (NLB) |
|---|---|---|
| Layer | 7 (HTTP/HTTPS, gRPC, WebSocket) | 4 (TCP/UDP/TLS) |
| Routing | Path, host, header, query string, method rules | Port based |
| Targets | Instances, IPs, **Lambda functions**, ECS tasks | Instances, IPs, ALB |
| Extras | Authentication (Cognito/OIDC), redirects, fixed responses, sticky sessions (cookies) | Static IP / Elastic IP per AZ, millions of req/s, preserves client IP |
| Client IP seen by the app | In the **`X-Forwarded-For`** header (plus `X-Forwarded-Proto`, `X-Forwarded-Port`) | Source IP preserved |

- **Target groups** with **health checks** (path, interval, thresholds). Unhealthy targets get no traffic.
- **Deregistration delay** (connection draining, default 300 s) lets in-flight requests finish.
- **Sticky sessions** bind a client to a target. Better: keep apps stateless and store sessions in ElastiCache/DynamoDB.
- TLS certificates come from **ACM** and terminate on the load balancer (chapter 13).

> **Trap** — "The application logs show the load balancer's IP instead of the client IP" → read
> the **X-Forwarded-For** header (ALB). With an NLB the client IP is preserved.

## Route 53 in five minutes

- **Records**: `A` (IPv4), `AAAA` (IPv6), `CNAME` (alias to another name, **not allowed at the zone
  apex** `example.com`), `MX`, `TXT`, `NS`...
- **Alias records** (Route 53 extension): point to AWS resources (ALB, CloudFront, S3 website, API
  Gateway...), **work at the zone apex**, and queries to AWS resources are free.
- **Routing policies**: simple, **weighted** (e.g. 90/10 between two stacks), **latency-based**,
  **failover** (active-passive with health checks), geolocation, geoproximity, multivalue answer.
- **TTL** controls how long resolvers cache answers, so lower it before a migration.

## Pricing basics a developer should know

- Data transfer **in** is free. Transfer **out** to the internet and **between AZs** is charged.
  Same-AZ private traffic is generally free.
- Serverless pricing is per request + duration (Lambda), per request or capacity (DynamoDB),
  per GB stored + requests (S3).
- Use **AWS Budgets** alarms and **Cost Explorer**. The labs in this repo all include a teardown section.

## Hands-on

- Optional lab: `labs/lab00-account-setup` creates a budget alarm, an admin user with MFA, and CLI profiles.
- Quiz: `uv run awslings quiz foundations`

## Summary

- Most resources are regional, and clients must target the right Region. ARNs identify resources (S3 and IAM ARNs omit parts).
- Security groups are stateful allow-lists on ENIs. NACLs are stateless subnet filters.
- A Lambda function in a VPC needs a NAT gateway or VPC endpoints to reach public AWS endpoints. Gateway endpoints exist only for S3 and DynamoDB.
- EC2 apps get credentials from the instance profile through IMDS (prefer IMDSv2).
- An ALB passes the client IP in `X-Forwarded-For`. Use Route 53 alias records at the zone apex.

## Check yourself

1. A Lambda function attached to private subnets must read from S3 and write to DynamoDB, without internet access. What is the cheapest way?
2. Security group vs network ACL: which one is stateful? Which one supports deny rules?
3. An application on EC2 must call SQS. Where should its credentials come from?
4. Why can't you create a CNAME for `example.com`, and what do you use instead?
5. A web app behind an ALB logs `10.0.1.25` as the client address. How do you get the real client IP?

<details><summary>Answers</summary>

1. Two **gateway VPC endpoints** (S3 and DynamoDB): free, no NAT gateway needed.
2. Security groups are stateful (allow rules only). NACLs are stateless and support deny rules.
3. From an **IAM role attached through an instance profile**. The SDK fetches temporary credentials from IMDS.
4. CNAMEs are not allowed at the zone apex. Use a Route 53 **alias** record (e.g. to the ALB or CloudFront distribution).
5. Read the `X-Forwarded-For` request header added by the ALB.

</details>

## Further reading

- [AWS global infrastructure](https://aws.amazon.com/about-aws/global-infrastructure/)
- [Shared responsibility model](https://aws.amazon.com/compliance/shared-responsibility-model/)
- [Giving Lambda functions access to resources in a VPC](https://docs.aws.amazon.com/lambda/latest/dg/configuration-vpc.html)
- [Use IMDSv2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-service.html)
- [Elastic Load Balancing user guide](https://docs.aws.amazon.com/elasticloadbalancing/)
