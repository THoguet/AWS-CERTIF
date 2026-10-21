"""
Exercise beanstalk_1 — .ebextensions and worker cron jobs
=========================================================
Book: chapter 18, "Elastic Beanstalk" (book/src/ch18-beanstalk-containers.md)
Exam: Domain 3 · Task 3.1 (organizing files and a directory structure for deployment)

Elastic Beanstalk reads YAML/JSON configuration files from the
`.ebextensions/` directory at the root of your source bundle (files must
end with `.config`, applied in alphabetical order). They can set option
settings, install packages, create files and run commands.

Worker environments pull messages from an SQS queue through the "sqsd"
daemon, which POSTs them to your app. Periodic tasks are declared in
`cron.yaml` at the bundle root.

Your task
---------
  * EBEXTENSIONS_CONFIG: environment properties STAGE=prod and
    LOG_LEVEL=INFO, auto scaling between 2 and 6 instances, deployment
    policy Immutable, X-Ray daemon enabled,
  * CRON_YAML: version 1, one task "nightly-report" calling /tasks/report
    at 02:00 UTC every day,
  * `config_path(name)`: where a config file named `name` goes in the bundle.
"""

EBEXTENSIONS_CONFIG = """
option_settings:
  aws:elasticbeanstalk:application:environment:
    STAGE: prod
    LOG_LEVEL: INFO
  aws:autoscaling:asg:
    MinSize: 2
    MaxSize: 6
  aws:elasticbeanstalk:command:
    DeploymentPolicy: Immutable
  aws:elasticbeanstalk:xray:
    XRayEnabled: true
"""

CRON_YAML = """
version: 1
cron:
  - name: nightly-report
    url: /tasks/report
    schedule: "0 2 * * *"
"""


def config_path(name: str) -> str:
    return f".ebextensions/{name}.config"


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run beanstalk_1
# =============================================================================
import yaml  # noqa: E402


def test_option_settings():
    settings = yaml.safe_load(EBEXTENSIONS_CONFIG)["option_settings"]
    assert settings["aws:elasticbeanstalk:application:environment"] == {"STAGE": "prod", "LOG_LEVEL": "INFO"}
    assert settings["aws:autoscaling:asg"] == {"MinSize": 2, "MaxSize": 6}
    assert settings["aws:elasticbeanstalk:command"]["DeploymentPolicy"] == "Immutable"
    assert settings["aws:elasticbeanstalk:xray"]["XRayEnabled"] is True


def test_cron():
    cron = yaml.safe_load(CRON_YAML)
    assert cron["version"] == 1
    assert cron["cron"] == [{"name": "nightly-report", "url": "/tasks/report", "schedule": "0 2 * * *"}]


def test_config_path():
    assert config_path("01-env") == ".ebextensions/01-env.config"
