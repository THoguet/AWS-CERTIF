"""Helpers shared by the exercise tests (you do not need to read this to solve exercises)."""

from __future__ import annotations

import io
import uuid
import zipfile

import yaml


class FakeContext:
    """Minimal stand-in for the Lambda context object passed to handlers."""

    def __init__(self, function_name="my-function", remaining_ms=30_000, memory_mb=128, request_id=None):
        self.function_name = function_name
        self.function_version = "$LATEST"
        self.invoked_function_arn = f"arn:aws:lambda:eu-west-3:123456789012:function:{function_name}"
        self.memory_limit_in_mb = memory_mb
        self.aws_request_id = request_id or str(uuid.uuid4())
        self.log_group_name = f"/aws/lambda/{function_name}"
        self.log_stream_name = "2026/10/21/[$LATEST]0123456789abcdef"
        self._remaining_ms = remaining_ms

    def get_remaining_time_in_millis(self):
        return self._remaining_ms


class _CfnLoader(yaml.SafeLoader):
    """YAML loader that understands CloudFormation short-form intrinsic functions (!Ref, !Sub...)."""


def _cfn_constructor(loader, tag_suffix, node):
    if isinstance(node, yaml.ScalarNode):
        value = loader.construct_scalar(node)
    elif isinstance(node, yaml.SequenceNode):
        value = loader.construct_sequence(node, deep=True)
    else:
        value = loader.construct_mapping(node, deep=True)
    if tag_suffix == "Ref":
        return {"Ref": value}
    if tag_suffix == "GetAtt" and isinstance(value, str):
        value = value.split(".", 1)
    if tag_suffix == "Condition":
        return {"Condition": value}
    return {f"Fn::{tag_suffix}": value}


_CfnLoader.add_multi_constructor("!", _cfn_constructor)


def load_cfn(text: str) -> dict:
    """Parse a CloudFormation/SAM YAML template into plain Python data."""
    return yaml.load(text, Loader=_CfnLoader)  # noqa: S506 (SafeLoader subclass)


def lambda_zip(files: dict[str, str] | None = None) -> bytes:
    """Build an in-memory deployment package."""
    files = files or {"app.py": "def handler(event, context):\n    return {'ok': True}\n"}
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return buffer.getvalue()
