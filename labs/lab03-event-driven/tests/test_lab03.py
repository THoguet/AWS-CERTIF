"""Offline tests for lab03. Run from the repo root: uv run pytest labs/lab03-event-driven"""

import importlib.util
import json
import re
from pathlib import Path

import boto3
import pytest

from awslings.testing import load_cfn

LAB = Path(__file__).resolve().parents[1]
ASL_PATH = LAB / "statemachine" / "process_upload.asl.json"


def load_validate():
    spec = importlib.util.spec_from_file_location("lab03_validate", LAB / "src" / "validate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --- the Lambda function ---------------------------------------------------------------------------

def test_summarize_the_samples():
    validate = load_validate()
    small = validate.summarize((LAB / "sample" / "orders-small.csv").read_text())
    large = validate.summarize((LAB / "sample" / "orders-large.csv").read_text())
    assert small == {"rows": 3, "total": "145.49", "total_cents": 14549}
    assert large == {"rows": 4, "total": "1188.89", "total_cents": 118889}
    assert small["total_cents"] <= 100000 < large["total_cents"]   # the Choice threshold


@pytest.mark.parametrize("text", [
    (LAB / "sample" / "broken.csv").read_text(),
    "order_id,amount\no-1,abc\n",
    "order_id,amount\no-1,1,extra\n",
    "order_id,amount\n",
    "",
])
def test_invalid_files_raise_invalid_file(text):
    validate = load_validate()
    with pytest.raises(validate.InvalidFile):
        validate.summarize(text)


def test_handler_reads_the_object_from_s3(aws):
    s3 = boto3.client("s3")
    s3.create_bucket(Bucket="uploads", CreateBucketConfiguration={"LocationConstraint": "eu-west-3"})
    s3.put_object(Bucket="uploads", Key="incoming/orders-small.csv",
                  Body=(LAB / "sample" / "orders-small.csv").read_bytes())
    validate = load_validate()
    assert validate.handler({"bucket": "uploads", "key": "incoming/orders-small.csv"}, None)["rows"] == 3


# --- the state machine definition ------------------------------------------------------------------

def substituted_definition():
    template = load_cfn((LAB / "template.yaml").read_text())
    subs = template["Resources"]["ProcessUploadStateMachine"]["Properties"]["DefinitionSubstitutions"]
    text = ASL_PATH.read_text()
    placeholders = set(re.findall(r"\$\{(\w+)\}", text))
    assert placeholders == set(subs), "placeholders and DefinitionSubstitutions must match"
    for name in placeholders:
        text = text.replace("${%s}" % name, f"value-of-{name}")
    return text


def test_definition_parses():
    from moto.stepfunctions.parser.asl.parse.asl_parser import AmazonStateLanguageParser

    AmazonStateLanguageParser.parse(substituted_definition())   # raises on syntax errors


def test_definition_graph_is_consistent():
    asl = json.loads(substituted_definition())
    states = asl["States"]
    assert asl["StartAt"] in states
    edges = {}
    for name, state in states.items():
        targets = [state[k] for k in ("Next", "Default") if k in state]
        targets += [c["Next"] for c in state.get("Choices", []) + state.get("Catch", [])]
        assert all(t in states for t in targets), f"{name} points to an unknown state"
        if state["Type"] not in ("Choice", "Fail", "Succeed"):
            assert ("Next" in state) != bool(state.get("End")), f"{name} needs exactly one of Next/End"
        edges[name] = targets
    reachable, todo = set(), [asl["StartAt"]]
    while todo:
        current = todo.pop()
        if current not in reachable:
            reachable.add(current)
            todo.extend(edges[current])
    assert reachable == set(states), f"unreachable states: {set(states) - reachable}"


def test_catch_keeps_the_original_input():
    states = json.loads(substituted_definition())["States"]
    catch = states["ValidateFile"]["Catch"][0]
    assert catch["ErrorEquals"] == ["InvalidFile"] and catch["ResultPath"] == "$.error"
    # tasks whose output is not needed must not overwrite the state's input
    assert states["AlertLargeTotal"]["ResultPath"] is None
