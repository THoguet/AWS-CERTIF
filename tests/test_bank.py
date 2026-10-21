"""Checks on the question bank and the quiz logic (run with `uv run pytest`)."""

import re
from collections import Counter
from pathlib import Path

import pytest

from awslings.exercises import find_root
from awslings.quiz import Question, load_bank, parse_answer, select, select_mock, validate_bank

ROOT = find_root(Path(__file__).parent)


@pytest.fixture(scope="module")
def bank():
    return load_bank(ROOT)


def test_bank_is_valid():
    assert validate_bank(ROOT) == []


def test_refs_point_to_existing_files(bank):
    missing = [(q.id, ref) for q in bank for ref in q.refs if not (ROOT / ref).is_file()]
    assert missing == []


def test_every_topic_used_in_the_docs_exists(bank):
    topics = {q.topic for q in bank}
    docs = [*ROOT.glob("*.md"), *(ROOT / "book" / "src").glob("*.md"), *(ROOT / ".claude").rglob("*.md")]
    used = {m for doc in docs for m in re.findall(r"awslings quiz ([a-z][a-z0-9-]*)", doc.read_text(encoding="utf-8"))}
    assert used - topics == set()


def test_mock_exam_follows_the_domain_weights(bank):
    questions = select_mock(bank, history=[], seed=1)
    assert len(questions) == 65
    assert len({q.id for q in questions}) == 65
    assert Counter(q.domain for q in questions) == {1: 21, 2: 17, 3: 16, 4: 11}


def test_each_domain_can_fill_several_mock_exams(bank):
    per_domain = Counter(q.domain for q in bank)
    assert all(per_domain[d] >= 2 * n for d, n in {1: 21, 2: 17, 3: 16, 4: 11}.items())


def _question(qid, answer=("A",), topic="t", domain=1):
    return Question(id=qid, topic=topic, chapter="ch00", domain=domain, task="1.1", difficulty=2,
                    question="Q? (Choose TWO.)" if len(answer) > 1 else "Q?",
                    options={k: k.lower() for k in "ABCDE"}, answer=sorted(answer), explanation="")


def test_parse_answer_accepts_letters_in_any_format():
    q = _question("t-1", answer=("A", "C"))
    assert parse_answer("a, c", q) == ["A", "C"]
    assert parse_answer("C A", q) == ["A", "C"]
    assert parse_answer("ca", q) == ["A", "C"]
    assert parse_answer("F", q) is None
    assert parse_answer("", q) is None


def test_select_prefers_unseen_then_wrong_then_right():
    qs = [_question(f"t-{i}") for i in range(1, 5)]
    history = [
        {"type": "answer", "qid": "t-1", "correct": True},
        {"type": "answer", "qid": "t-2", "correct": False},
    ]
    picked = [q.id for q in select(qs, history, count=4, seed=3)]
    assert set(picked[:2]) == {"t-3", "t-4"}
    assert picked[2:] == ["t-2", "t-1"]


def test_validator_flags_unbalanced_answer_letters(tmp_path):
    bank_dir = tmp_path / "quizzes" / "bank"
    bank_dir.mkdir(parents=True)
    lines = ["chapter: ch00", "topic: t", "questions:"]
    for i in range(1, 41):
        lines += [
            f"  - id: t-{i:03d}",
            "    domain: 1",
            "    question: Q?",
            "    options: {A: a, B: b, C: c, D: d}",
            "    answer: [A]",
            "    explanation: E.",
        ]
    (bank_dir / "t.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    problems = validate_bank(tmp_path)
    assert len(problems) == 1 and "unbalanced" in problems[0]
