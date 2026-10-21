"""
Exercise cicd_1 — A CodeBuild buildspec
=======================================
Book: chapter 17, "CodeBuild" (book/src/ch17-cicd.md)
Exam: Domain 3 · Tasks 3.3 / 3.4 (automated testing in CI/CD, deploying with AWS CI/CD services)

CodeBuild reads `buildspec.yml` at the root of the source (or a path you
configure). Complete BUILDSPEC:
  * version 0.2,
  * env:
      variables: ARTIFACT_BUCKET = my-artifacts-bucket
      parameter-store: SONAR_TOKEN = /ci/sonar/token   (never hard-code secrets)
  * phases:
      install:    runtime-versions python 3.12, then `pip install -r requirements.txt`
      pre_build:  `pytest --junitxml=reports/junit.xml`
      build:      `sam build` and
                  `sam package --s3-bucket $ARTIFACT_BUCKET --output-template-file packaged.yaml`
      post_build: `echo Build completed on $(date)`
  * reports: group "unit-tests" with JUnit XML files from reports/,
  * artifacts: packaged.yaml (handed to the next pipeline stage),
  * cache: pip's cache directory /root/.cache/pip/**/* (faster builds).
"""

BUILDSPEC = """
version: 0.2

env:
  variables:
    ARTIFACT_BUCKET: my-artifacts-bucket
  parameter-store:
    SONAR_TOKEN: /ci/sonar/token

phases:
  install:
    runtime-versions:
      python: 3.12
    commands:
      - pip install -r requirements.txt
  pre_build:
    commands:
      - pytest --junitxml=reports/junit.xml
  build:
    commands:
      - sam build
      - sam package --s3-bucket $ARTIFACT_BUCKET --output-template-file packaged.yaml
  post_build:
    commands:
      - echo Build completed on $(date)

reports:
  unit-tests:
    files:
      - junit.xml
    base-directory: reports
    file-format: JUNITXML

artifacts:
  files:
    - packaged.yaml

cache:
  paths:
    - /root/.cache/pip/**/*
"""


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run cicd_1
# =============================================================================
import yaml  # noqa: E402

SPEC = yaml.safe_load(BUILDSPEC)


def test_version_and_env():
    assert str(SPEC["version"]) == "0.2"
    assert SPEC["env"]["variables"] == {"ARTIFACT_BUCKET": "my-artifacts-bucket"}
    assert SPEC["env"]["parameter-store"] == {"SONAR_TOKEN": "/ci/sonar/token"}


def test_phases():
    phases = SPEC["phases"]
    assert list(phases) == ["install", "pre_build", "build", "post_build"]
    assert str(phases["install"]["runtime-versions"]["python"]) == "3.12"
    assert "pip install -r requirements.txt" in phases["install"]["commands"]
    assert any("pytest" in c and "--junitxml=reports/junit.xml" in c for c in phases["pre_build"]["commands"])
    assert phases["build"]["commands"][0] == "sam build"
    assert any("sam package" in c and "$ARTIFACT_BUCKET" in c and "packaged.yaml" in c for c in phases["build"]["commands"])


def test_reports_artifacts_cache():
    report = SPEC["reports"]["unit-tests"]
    assert report["file-format"] == "JUNITXML" and report["base-directory"] == "reports"
    assert SPEC["artifacts"]["files"] == ["packaged.yaml"]
    assert SPEC["cache"]["paths"] == ["/root/.cache/pip/**/*"]
