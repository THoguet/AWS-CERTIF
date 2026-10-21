"""Cross-reference checks between the book, the exercises and the labs (run with `uv run pytest`)."""

import re
from pathlib import Path

from awslings import exercises as ex_mod
from awslings.exercises import MARKER_RE, find_root, load_exercises

ROOT = find_root(Path(__file__).parent)
EXERCISES = load_exercises(ROOT)
NAMES = {e.name for e in EXERCISES}
BOOK = sorted((ROOT / "book" / "src").glob("*.md"))


def test_exercises_and_solutions_are_consistent():
    assert len(NAMES) == len(EXERCISES), "duplicate exercise names in info.toml"
    for e in EXERCISES:
        assert e.path.is_file(), e.rel
        assert e.solution.is_file(), e.name
        assert MARKER_RE.search(e.source()), f"{e.name}: missing marker"
        assert not MARKER_RE.search(e.solution.read_text(encoding="utf-8")), f"{e.name}: solution has the marker"
        assert ex_mod.tests_section(e.source()) == ex_mod.tests_section(e.solution.read_text(encoding="utf-8")), e.name
        assert e.hint, f"{e.name}: missing hint"


def test_every_exercise_file_is_listed():
    listed = {e.path.resolve() for e in EXERCISES}
    on_disk = {p.resolve() for p in (ROOT / "exercises").rglob("*.py")}
    assert on_disk - listed == set()


def test_book_mentions_only_existing_exercises():
    pattern = re.compile(r"`([a-z]+_\d+)`")
    unknown = {(p.name, m) for p in BOOK for m in pattern.findall(p.read_text(encoding="utf-8"))
               if m not in NAMES and re.match(r"(intro|iam|sdk|s3|lambda|apigw|ddb|cache|sqs|sns|events|kinesis|sfn|res|cognito|kms|secrets|cfn|sam|cicd|ecs|beanstalk|cw|xray|opt)_\d+$", m)}
    assert unknown == set()


def test_summary_lists_every_chapter():
    summary = (ROOT / "book" / "src" / "SUMMARY.md").read_text(encoding="utf-8")
    linked = set(re.findall(r"\]\((?:\./)?([^)]+\.md)\)", summary))
    assert {p.name for p in BOOK} - {"SUMMARY.md"} == linked


def test_referenced_labs_exist():
    docs = [*BOOK, *ROOT.glob("*.md")]
    labs = {m for d in docs for m in re.findall(r"labs/(lab\d\d-[a-z0-9-]+)", d.read_text(encoding="utf-8"))}
    missing = sorted(lab for lab in labs if not (ROOT / "labs" / lab / "README.md").is_file())
    assert missing == []


LAB_TEMPLATES = sorted(
    [*(ROOT / "labs").glob("*/template.yaml"), *(ROOT / "labs").glob("*/pipeline.yaml"), *(ROOT / "labs").glob("*/app/template.yaml")]
)


def test_lab_templates_pass_cfn_lint():
    from cfnlint import api

    assert LAB_TEMPLATES, "no lab templates found"
    errors = {
        str(path.relative_to(ROOT)): [f"{m.rule.id} line {m.linenumber}: {m.message}" for m in matches]
        for path in LAB_TEMPLATES
        if (matches := [m for m in api.lint(path.read_text(encoding="utf-8"), regions=["eu-west-3"]) if str(m.rule.id).startswith("E")])
    }
    assert errors == {}


def test_every_lab_has_cost_and_teardown_sections():
    for readme in sorted((ROOT / "labs").glob("lab*/README.md")):
        text = readme.read_text(encoding="utf-8")
        assert "**Cost**" in text, f"{readme.parent.name}: missing cost estimate"
        assert "## Teardown" in text, f"{readme.parent.name}: missing teardown section"
        assert "## What to remember for the exam" in text, f"{readme.parent.name}: missing exam takeaways"
