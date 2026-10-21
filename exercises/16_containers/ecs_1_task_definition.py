"""
Exercise ecs_1 — An ECS task definition for Fargate
===================================================
Book: chapter 18, "Amazon ECS and ECR" (book/src/ch18-beanstalk-containers.md)
Exam: Domain 3 · Task 3.1 (container images, applying application requirements for resources)

Two roles that the exam LOVES to confuse:
  * TASK EXECUTION ROLE — assumed by the ECS agent/Fargate to pull the
    image from ECR, send logs to CloudWatch Logs (awslogs driver) and
    read the secrets injected into the container,
  * TASK ROLE — assumed by your application code. Give it least-privilege
    access to what the app calls (S3, DynamoDB...).

Fargate only accepts specific CPU/memory pairs, for example:
  256 (.25 vCPU) → 512, 1024 or 2048 MiB
  512 (.5 vCPU)  → 1024 to 4096 MiB in 1024 steps
  1024 (1 vCPU)  → 2048 to 8192 MiB in 1024 steps
  2048 (2 vCPU)  → 4096 to 16384 MiB in 1024 steps
  4096 (4 vCPU)  → 8192 to 30720 MiB in 1024 steps

Your task
---------
  * `valid_fargate_size(cpu, memory)` for the table above,
  * `register_web_task(ecs, image_tag)`: family "web", Fargate, awsvpc,
    cpu 512 / memory 1024, the two roles below, one essential container
    "web" (image ECR_REPO:<tag>, port 8080, awslogs driver to group /ecs/web,
    environment STAGE=prod, secret DB_PASSWORD from DB_PASSWORD_PARAM).
    Return the task definition.
"""

# I AM NOT DONE

ACCOUNT, REGION = "123456789012", "eu-west-3"
ECR_REPO = f"{ACCOUNT}.dkr.ecr.{REGION}.amazonaws.com/web"
EXECUTION_ROLE = f"arn:aws:iam::{ACCOUNT}:role/ecsTaskExecutionRole"
APP_ROLE = f"arn:aws:iam::{ACCOUNT}:role/web-app"
DB_PASSWORD_PARAM = f"arn:aws:ssm:{REGION}:{ACCOUNT}:parameter/web/prod/db_password"


def valid_fargate_size(cpu: int, memory: int) -> bool:
    raise NotImplementedError  # TODO


def register_web_task(ecs, image_tag: str) -> dict:
    return ecs.register_task_definition(
        family="web",
        taskRoleArn=EXECUTION_ROLE,  # TODO: is this the right role here? And where is the other one?
        containerDefinitions=[
            {
                "name": "web",
                "image": f"{ECR_REPO}:{image_tag}",
                "environment": [{"name": "DB_PASSWORD", "value": "hunter2"}],  # TODO: never put secrets here
            }
        ],
        # TODO: Fargate compatibility, network mode, cpu/memory, ports, logs
    )["taskDefinition"]


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run ecs_1
# =============================================================================
import boto3  # noqa: E402


def test_fargate_sizes():
    assert valid_fargate_size(256, 512) and valid_fargate_size(256, 2048)
    assert not valid_fargate_size(256, 4096)
    assert valid_fargate_size(512, 3072) and not valid_fargate_size(512, 5120)
    assert valid_fargate_size(4096, 30720) and not valid_fargate_size(4096, 4096)
    assert not valid_fargate_size(3000, 4096)


def test_task_definition(aws):
    td = register_web_task(boto3.client("ecs"), "1.4.2")
    assert td["family"] == "web"
    assert td["requiresCompatibilities"] == ["FARGATE"] and td["networkMode"] == "awsvpc"
    assert (td["cpu"], td["memory"]) == ("512", "1024")
    assert valid_fargate_size(int(td["cpu"]), int(td["memory"]))
    assert td["executionRoleArn"] == EXECUTION_ROLE, "the agent pulls the image and reads secrets"
    assert td["taskRoleArn"] == APP_ROLE, "the application code uses the task role"


def test_container(aws):
    container = register_web_task(boto3.client("ecs"), "1.4.2")["containerDefinitions"][0]
    assert container["image"].endswith("/web:1.4.2") and container["essential"] is True
    assert container["portMappings"][0]["containerPort"] == 8080
    assert {"name": "STAGE", "value": "prod"} in container["environment"]
    assert all(e["name"] != "DB_PASSWORD" for e in container["environment"]), "secrets do not belong in environment"
    assert container["secrets"] == [{"name": "DB_PASSWORD", "valueFrom": DB_PASSWORD_PARAM}]
    assert container["logConfiguration"]["logDriver"] == "awslogs"
    assert container["logConfiguration"]["options"]["awslogs-group"] == "/ecs/web"
