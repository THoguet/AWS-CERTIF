# CloudFormation and CDK

> **In this chapter**
> - Template anatomy: parameters, mappings, conditions, resources, outputs
> - Intrinsic functions and pseudo parameters
> - Stack lifecycle: change sets, rollbacks, deletion/update policies, drift, stack policies
> - Reuse: nested stacks vs cross-stack references, StackSets, custom resources, helper scripts
> - AWS CDK: constructs, bootstrap, synth/diff/deploy, assets, testing
>
> **Exam weight**: Domain 3 Tasks 3.3/3.4 (implementing and updating IaC templates)
> · **Exercises**: `cfn_1`, `cfn_2` · **Quiz**: `uv run awslings quiz cloudformation`

## Why infrastructure as code

Templates are versioned, reviewed and repeatable. The same template creates identical dev, test and prod
environments, and an update shows a diff (change set) before touching anything. CloudFormation is the
engine under SAM, CDK, Amplify and Elastic Beanstalk.

## Template anatomy

```yaml
AWSTemplateFormatVersion: "2010-09-09"
Description: Orders backend
Parameters:                    # inputs at deploy time
  Env:
    Type: String
    AllowedValues: [dev, prod]
    Default: dev
  LatestAmi:
    Type: AWS::SSM::Parameter::Value<AWS::EC2::Image::Id>       # resolved from Parameter Store
    Default: /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64
Mappings:                      # static lookup tables
  EnvSettings:
    dev:  {Retention: 345600}
    prod: {Retention: 1209600}
Conditions:                    # booleans computed from parameters
  IsProd: !Equals [!Ref Env, prod]
Transform: AWS::Serverless-2016-10-31   # macros (SAM, AWS::Include...)
Resources:                     # the ONLY mandatory section
  OrdersQueue:
    Type: AWS::SQS::Queue
    Properties:
      MessageRetentionPeriod: !FindInMap [EnvSettings, !Ref Env, Retention]
      VisibilityTimeout: !If [IsProd, 300, 60]
  AlertsTopic:
    Type: AWS::SNS::Topic
    Condition: IsProd          # created only in prod
Outputs:
  QueueUrl:
    Value: !Ref OrdersQueue
    Export:
      Name: !Sub "${AWS::StackName}-QueueUrl"     # importable by other stacks
```

- **Parameter types**: `String`, `Number`, `CommaDelimitedList`, AWS-specific types (`AWS::EC2::VPC::Id`,
  `AWS::EC2::KeyPair::KeyName`...) validated at deploy time, and **SSM parameter types**. `NoEcho: true` masks values.
- **Outputs** with **Export** feed `!ImportValue` in other stacks (same account and Region).

### Intrinsic functions

| Function | Returns / does |
|---|---|
| `!Ref X` | Parameter value, or the resource's main id (bucket **name**, queue **URL**, table **name**, function **name**...) |
| `!GetAtt X.Attr` | Another attribute: `.Arn`, `QueueName`, `DomainName`, `StreamArn`... |
| `!Sub "arn:aws:s3:::${Bucket}/*"` | String interpolation of parameters, resources, pseudo parameters |
| `!Join [",", [a, b]]`, `!Split`, `!Select [0, list]` | String/list manipulation |
| `!FindInMap [Map, Key, SubKey]` | Lookup in Mappings |
| `!ImportValue Name` | A value exported by another stack |
| `!If [Cond, a, b]`, `!Equals`, `!And`, `!Or`, `!Not` | Conditions. `!Ref AWS::NoValue` removes a property |
| `!GetAZs`, `!Cidr`, `!Base64` | AZ list, CIDR blocks, user data encoding |

**Pseudo parameters**: `AWS::AccountId`, `AWS::Region`, `AWS::StackName`, `AWS::StackId`, `AWS::Partition`,
`AWS::URLSuffix`, `AWS::NoValue`.

> **Trap** — `!Ref` on an SQS queue returns its **URL**, but a redrive policy or IAM policy needs the
> **ARN** → `!GetAtt Queue.Arn` (exercise `cfn_1`).

## Stack lifecycle

- **Create / update / delete**. Prefer **change sets** for updates: they preview what will be added,
  modified or **replaced**, then you execute.
- **Update behaviors** per property: *no interruption*, *some interruption*, or **replacement** (a new
  physical resource is created and the old one deleted). Changing a DynamoDB `TableName`, an S3
  `BucketName` or an RDS `DBInstanceIdentifier` means replacement. With custom names, replacement can fail
  because the name is taken. Let CloudFormation generate names when possible.
- **Automatic rollback** on failure (create or update). **Rollback triggers** roll back an update when a
  CloudWatch alarm fires during the monitoring period. For debugging, you can disable rollback /
  preserve successful resources. `UPDATE_ROLLBACK_FAILED` → fix the cause, then *continue update rollback*.
- Resource attributes:
  - `DependsOn`: explicit ordering (implicit dependencies come from `!Ref`/`!GetAtt`),
  - **`DeletionPolicy`**: `Delete` (default for most resources), **`Retain`** (keep the resource when the stack
    is deleted), **`Snapshot`** (RDS, EBS volumes, ElastiCache, Redshift...), `RetainExceptOnCreate`,
  - `UpdateReplacePolicy`: same options when a resource is replaced during an update,
  - `UpdatePolicy` (Auto Scaling rolling/replacing updates), `CreationPolicy` + `cfn-signal` (wait for
    instances to report success).
- **Stack policies** protect critical resources from updates. **Termination protection** prevents stack deletion.
- **Drift detection** finds resources changed outside CloudFormation. **Resource import** / **IaC generator**
  bring existing resources under management.
- **Capabilities**: you must acknowledge `CAPABILITY_IAM` / `CAPABILITY_NAMED_IAM` (templates creating IAM
  resources, named ones for the latter) and `CAPABILITY_AUTO_EXPAND` (macros/transforms such as SAM).
- A **service role** lets CloudFormation act with that role's permissions instead of the caller's (the caller needs `iam:PassRole`).

> **Exam tip** — "Keep the S3 bucket / DynamoDB table when the stack is deleted" → **`DeletionPolicy: Retain`**.
> "Take a final snapshot of the RDS database on deletion" → **`DeletionPolicy: Snapshot`**.

## Reuse and scale

| Mechanism | What | When |
|---|---|---|
| **Nested stacks** (`AWS::CloudFormation::Stack`) | A parent stack includes child templates, deployed and updated **together** | Reusable components (a standard ALB, a VPC module) |
| **Cross-stack references** (Export / `!ImportValue`) | Independent stacks share outputs | Separate lifecycles (a network stack used by many app stacks). An exported value cannot be changed or deleted while imported |
| **StackSets** | Deploy one template to **many accounts and Regions** | Org-wide baselines (roles, Config rules, guardrails) |
| **Modules / Registry** | Reusable resource types and modules | Standardization at scale |

### Custom resources

When CloudFormation cannot do something natively (seed a table, empty a bucket before deletion, call
a third-party API), a **custom resource** invokes a Lambda function (`ServiceToken`) with
`RequestType` = `Create`, `Update` or `Delete`. The function **must send a response** (SUCCESS/FAILED +
data) to the presigned S3 URL in the event (`cfnresponse` helper). Otherwise the stack waits until
the custom resource times out (1 hour by default, configurable with `ServiceTimeout`).

### EC2 helper scripts

`cfn-init` (applies `AWS::CloudFormation::Init` metadata: packages, files, services), `cfn-signal`
(signals success to a CreationPolicy/WaitCondition), `cfn-hup` (re-applies metadata on updates),
`cfn-get-metadata`.

### Packaging and deploying from the CLI

```bash
aws cloudformation package --template-file template.yaml --s3-bucket my-artifacts \
    --output-template-file packaged.yaml          # uploads local code (Lambda zips...) to S3, rewrites paths
aws cloudformation deploy --template-file packaged.yaml --stack-name orders-prod \
    --parameter-overrides Env=prod --capabilities CAPABILITY_IAM   # creates + executes a change set
```

Quality tools: **cfn-lint** (template linter), **CloudFormation Guard** (policy-as-code rules),
**CloudFormation Hooks** (pre-provisioning checks).

## AWS CDK

The **Cloud Development Kit** defines infrastructure in TypeScript, Python, Java, C#, Go. Your code
**synthesizes** CloudFormation templates.

- **Constructs**: **L1** (`Cfn*`, a 1:1 mapping to CloudFormation resources), **L2** (curated, sensible defaults
  and helper methods, e.g. `s3.Bucket`), **L3** patterns (several resources, e.g.
  `ApplicationLoadBalancedFargateService`). App → Stacks → Constructs.
- **Grants** generate least-privilege IAM policies: `table.grantReadWriteData(fn)`, `bucket.grantRead(role)`.

```python
from aws_cdk import App, Stack, aws_dynamodb as ddb, aws_lambda as lambda_

class OrdersStack(Stack):
    def __init__(self, scope, id, **kw):
        super().__init__(scope, id, **kw)
        table = ddb.Table(self, "Orders", partition_key=ddb.Attribute(name="pk", type=ddb.AttributeType.STRING),
                          billing_mode=ddb.BillingMode.PAY_PER_REQUEST)
        fn = lambda_.Function(self, "Api", runtime=lambda_.Runtime.PYTHON_3_12, handler="app.handler",
                              code=lambda_.Code.from_asset("src"), environment={"TABLE": table.table_name})
        table.grant_read_write_data(fn)

app = App(); OrdersStack(app, "orders-dev"); app.synth()
```

| Command | Does |
|---|---|
| `cdk init app --language python` | New project |
| **`cdk bootstrap`** | Once per account/Region: creates the **CDKToolkit** stack (S3 bucket, ECR repository, IAM roles) used to stage **assets** |
| `cdk synth` | Generates the CloudFormation template (`cdk.out/`) |
| `cdk diff` | Compares with the deployed stack |
| `cdk deploy` | Uploads assets (Lambda code, Docker images), deploys through CloudFormation |
| `cdk destroy` | Deletes the stack |
| `cdk watch` / `--hotswap` | Fast dev-loop updates (development only) |

- Testing: the **assertions** module (`Template.from_stack(stack).has_resource_properties(...)`) and snapshot tests in your normal unit test framework.
- **CDK Pipelines**: a self-mutating CodePipeline that deploys your CDK app to several stages/accounts.

> **Exam tip** — "Error: the environment is not bootstrapped / SSM parameter /cdk-bootstrap/... not found"
> → run **`cdk bootstrap`** for that account and Region.

## Hands-on

| Exercise | Skill |
|---|---|
| `cfn_1` | Parameters, `!Sub`, `!GetAtt ... Arn` for a redrive policy, exported outputs (deployed into moto) |
| `cfn_2` | Mappings, conditions, `!If`, `!Join` with pseudo parameters, conditional resources and outputs |

Optional lab: `labs/lab04-cicd-pipeline` deploys a stack through CodePipeline.

## Summary

- Resources is the only mandatory section. Parameters, Mappings, Conditions, Outputs/Exports.
- `!Ref` = main id (queue URL, bucket name). `!GetAtt` = attributes (Arn). `!Sub` for strings with pseudo parameters.
- Change sets preview replacements. Rollback on failure. DeletionPolicy Retain/Snapshot. Stack policies, termination protection, drift.
- Nested stacks = deployed together. Exports = shared between independent stacks. StackSets = multi-account/Region.
- Custom resources must respond to the presigned URL. CDK: constructs → synth → CloudFormation. Bootstrap once per account/Region.

## Check yourself

1. Which function returns the ARN of an SQS queue declared in the same template?
2. How do you make sure a DynamoDB table survives the deletion of its stack?
3. Several application stacks must use the VPC id created by a network stack. Which mechanism?
4. A stack update renames a DynamoDB table. What happens to the data?
5. `cdk deploy` fails in a new account with an error about a missing bootstrap stack. Fix?

<details><summary>Answers</summary>

1. `!GetAtt MyQueue.Arn` (`!Ref` returns the URL).
2. `DeletionPolicy: Retain` on the table (and optionally `UpdateReplacePolicy: Retain`).
3. **Exports** in the network stack + `!ImportValue` in the application stacks (cross-stack references).
4. Renaming requires **replacement**: a new empty table is created and the old one deleted (unless a Retain policy keeps it). The data is not migrated.
5. Run `cdk bootstrap aws://<account>/<region>`.

</details>

## Further reading

- [CloudFormation user guide](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/Welcome.html)
- [Intrinsic function reference](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/intrinsic-function-reference.html)
- [DeletionPolicy attribute](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-attribute-deletionpolicy.html)
- [Custom resources](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-custom-resources.html)
- [AWS CDK developer guide](https://docs.aws.amazon.com/cdk/v2/guide/home.html)
