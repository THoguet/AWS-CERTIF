"""Question bank, interactive quizzes, timed mock exams and answer history."""

from __future__ import annotations

import json
import random
import re
import textwrap
import time
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

from awslings import ui

# DVA-C02 content domains and their weight in the scored part of the exam.
DOMAINS = {
    1: ("Development with AWS Services", 0.32),
    2: ("Security", 0.26),
    3: ("Deployment", 0.24),
    4: ("Troubleshooting and Optimization", 0.18),
}
EXAM_QUESTIONS = 65
EXAM_MINUTES = 130


@dataclass
class Question:
    id: str
    topic: str
    chapter: str
    domain: int
    task: str
    difficulty: int
    question: str
    options: dict[str, str]
    answer: list[str]
    explanation: str
    refs: list[str] = field(default_factory=list)
    source: str = ""

    @property
    def multi(self) -> bool:
        return len(self.answer) > 1


def load_bank(root: Path) -> list[Question]:
    questions = []
    for path in sorted((root / "quizzes" / "bank").glob("*.yaml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for raw in doc.get("questions", []):
            questions.append(
                Question(
                    id=str(raw["id"]),
                    topic=str(raw.get("topic", doc.get("topic", ""))),
                    chapter=str(doc.get("chapter", "")),
                    domain=int(raw["domain"]),
                    task=str(raw.get("task", "")),
                    difficulty=int(raw.get("difficulty", 2)),
                    question=str(raw["question"]).strip(),
                    options={str(k): str(v).strip() for k, v in raw["options"].items()},
                    answer=sorted(str(a) for a in raw["answer"]),
                    explanation=str(raw.get("explanation", "")).strip(),
                    refs=list(raw.get("refs", [])),
                    source=path.name,
                )
            )
    return questions


def validate_bank(root: Path) -> list[str]:
    """Return a list of problems found in the question bank (empty list = OK)."""
    problems = []
    seen = {}
    single_letters = Counter()
    for path in sorted((root / "quizzes" / "bank").glob("*.yaml")):
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            problems.append(f"{path.name}: invalid YAML: {exc}")
            continue
        for key in ("chapter", "topic", "questions"):
            if key not in doc:
                problems.append(f"{path.name}: missing top-level key '{key}'")
        for i, raw in enumerate(doc.get("questions", []) or []):
            where = f"{path.name}#{i + 1} ({raw.get('id', '?')})"
            for key in ("id", "domain", "question", "options", "answer", "explanation"):
                if key not in raw:
                    problems.append(f"{where}: missing '{key}'")
            if "id" in raw:
                if raw["id"] in seen:
                    problems.append(f"{where}: duplicate id (also in {seen[raw['id']]})")
                seen[raw["id"]] = path.name
            if raw.get("domain") not in (1, 2, 3, 4):
                problems.append(f"{where}: domain must be 1, 2, 3 or 4")
            options = raw.get("options") or {}
            answer = raw.get("answer") or []
            if len(options) < 4:
                problems.append(f"{where}: needs at least 4 options")
            if not answer or any(str(a) not in options for a in answer):
                problems.append(f"{where}: answer {answer} not in options {list(options)}")
            text = str(raw.get("question", ""))
            choose = re.search(r"\(Choose (TWO|THREE)\.\)", text)
            if len(answer) > 1 and not choose:
                problems.append(f"{where}: multi-answer question must say '(Choose TWO.)' or '(Choose THREE.)'")
            if choose and len(answer) != {"TWO": 2, "THREE": 3}[choose.group(1)]:
                problems.append(f"{where}: '(Choose {choose.group(1)}.)' does not match {len(answer)} answers")
            if len(answer) == 1 and len(options) == 4:
                single_letters[str(answer[0])] += 1
    # The correct answer must not sit in the same position most of the time, or learners pick up the pattern.
    total = sum(single_letters.values())
    if total >= 40:
        letter, count = single_letters.most_common(1)[0]
        if count / total > 0.4:
            problems.append(
                f"correct answers are unbalanced: {count}/{total} single-answer questions use {letter} "
                f"({dict(sorted(single_letters.items()))}). Vary the position of the correct option."
            )
    return problems


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------


def history_file(root: Path) -> Path:
    return root / "progress" / "quiz-history.jsonl"


def append_history(root: Path, entries: list[dict]):
    path = history_file(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for entry in entries:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_history(root: Path) -> list[dict]:
    path = history_file(root)
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except ValueError:
                continue
    return entries


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------


def last_result_by_question(history: list[dict]) -> dict[str, bool]:
    result = {}
    for entry in history:
        if entry.get("type") == "answer" and entry.get("qid"):
            result[entry["qid"]] = bool(entry.get("correct"))
    return result


def select(
    bank: list[Question],
    history: list[dict],
    topics: list[str] | None = None,
    domain: int | None = None,
    count: int = 10,
    only_wrong: bool = False,
    only_new: bool = False,
    seed: int | None = None,
) -> list[Question]:
    rng = random.Random(seed)
    pool = bank
    if topics:
        wanted = {t.lower() for t in topics}
        pool = [q for q in pool if q.topic.lower() in wanted or q.chapter.lower() in wanted]
    if domain:
        pool = [q for q in pool if q.domain == domain]
    last = last_result_by_question(history)
    if only_wrong:
        pool = [q for q in pool if last.get(q.id) is False]
    if only_new:
        pool = [q for q in pool if q.id not in last]
    # Prefer unseen questions, then previously-wrong ones, then the rest.
    unseen = [q for q in pool if q.id not in last]
    wrong = [q for q in pool if last.get(q.id) is False]
    right = [q for q in pool if last.get(q.id) is True]
    for group in (unseen, wrong, right):
        rng.shuffle(group)
    return (unseen + wrong + right)[:count]


def select_mock(bank: list[Question], history: list[dict], count: int = EXAM_QUESTIONS, seed=None) -> list[Question]:
    rng = random.Random(seed)
    by_domain = defaultdict(list)
    for q in bank:
        by_domain[q.domain].append(q)
    last = last_result_by_question(history)
    # Floor each domain's share, then give the remaining questions to the heaviest domains
    # (65 questions -> 21/17/16/11).
    targets = {d: int(count * w) for d, (_, w) in DOMAINS.items()}
    heaviest = sorted(DOMAINS, key=lambda d: -DOMAINS[d][1])
    for d in heaviest[: count - sum(targets.values())]:
        targets[d] += 1
    chosen = []
    for d, n in targets.items():
        pool = by_domain.get(d, [])
        unseen = [q for q in pool if q.id not in last]
        seen = [q for q in pool if q.id in last]
        rng.shuffle(unseen)
        rng.shuffle(seen)
        chosen.extend((unseen + seen)[:n])
    rng.shuffle(chosen)
    return chosen


# ---------------------------------------------------------------------------
# Interaction
# ---------------------------------------------------------------------------


def _wrap(text: str, indent: str = "") -> str:
    out = []
    for paragraph in text.split("\n"):
        if not paragraph.strip():
            out.append("")
            continue
        out.append(textwrap.fill(paragraph, width=ui.width(), initial_indent=indent, subsequent_indent=indent))
    return "\n".join(out)


def render_question(q: Question, index: int, total: int, extra: str = "") -> str:
    header = ui.bold(f"Question {index}/{total}") + ui.dim(f"  [{q.id} · domain {q.domain} · {q.topic}]") + extra
    lines = [header, "", _wrap(q.question), ""]
    for letter, text in q.options.items():
        lines.append(_wrap(f"{letter}. {text}", indent="   ").replace("   ", "  ", 1))
    return "\n".join(lines)


def parse_answer(raw: str, q: Question) -> list[str] | None:
    letters = sorted(set(re.findall(r"[A-Za-z]", raw.upper())))
    if not letters or any(letter not in q.options for letter in letters):
        return None
    return letters


def explain(q: Question, given: list[str] | None) -> str:
    correct = given == q.answer
    verdict = ui.green("✔ Correct!") if correct else ui.red("✘ Incorrect.")
    lines = [verdict + f"  Answer: {ui.bold(', '.join(q.answer))}" + (f"  (you chose {', '.join(given)})" if given and not correct else "")]
    if q.explanation:
        lines += ["", _wrap(q.explanation)]
    if q.refs:
        lines += ["", ui.dim("Read more: " + ", ".join(q.refs))]
    return "\n".join(lines)


def run_quiz(root: Path, questions: list[Question], mode: str = "quiz") -> dict:
    """Ask questions one by one with immediate feedback."""
    session = uuid.uuid4().hex[:8]
    entries = []
    print(ui.dim("Type the letter(s) of your answer (e.g. B or A,C). 's' skips, 'q' quits.\n"))
    for i, q in enumerate(questions, 1):
        print(ui.rule())
        print(render_question(q, i, len(questions)))
        print()
        started = time.monotonic()
        while True:
            raw = input(ui.cyan("Your answer: ")).strip()
            if raw.lower() in ("q", "quit", "exit"):
                return _finish(root, session, mode, entries, questions[: i - 1])
            if raw.lower() in ("s", "skip"):
                given = None
                break
            given = parse_answer(raw, q)
            if given is None:
                print(ui.yellow(f"Please answer with option letters among {', '.join(q.options)}."))
                continue
            if q.multi and len(given) != len(q.answer):
                print(ui.yellow(f"This question needs exactly {len(q.answer)} answers."))
                continue
            break
        elapsed = round(time.monotonic() - started)
        correct = given == q.answer
        entries.append(_entry(session, mode, q, given, correct, elapsed))
        print()
        print(explain(q, given))
        print()
    return _finish(root, session, mode, entries, questions)


def run_mock(root: Path, questions: list[Question], minutes: int = EXAM_MINUTES, timer: bool = True) -> dict:
    """Exam simulation: no feedback until the end, flag for review, time limit."""
    session = uuid.uuid4().hex[:8]
    answers: dict[str, list[str] | None] = {q.id: None for q in questions}
    flagged: set[str] = set()
    deadline = time.monotonic() + minutes * 60 if timer else None
    print(ui.box(f"Mock exam — {len(questions)} questions — {minutes} minutes" if timer else f"Mock exam — {len(questions)} questions"))
    print(ui.dim("Answer with letters (e.g. B or A,C). Add 'f' to flag for review (e.g. 'C f'). 'q' ends the exam early.\n"))

    def remaining() -> str:
        if deadline is None:
            return ""
        left = max(0, int(deadline - time.monotonic()))
        return ui.dim(f"  ⏱ {left // 60:02d}:{left % 60:02d} left")

    def ask(q: Question, i: int) -> bool:
        print(ui.rule())
        current = answers[q.id]
        extra = remaining() + (ui.yellow("  ⚑ flagged") if q.id in flagged else "")
        print(render_question(q, i, len(questions), extra))
        if current:
            print(ui.dim(f"\nCurrent answer: {', '.join(current)} (press Enter to keep)"))
        print()
        while True:
            if deadline is not None and time.monotonic() > deadline:
                print(ui.red("Time is up!"))
                return False
            raw = input(ui.cyan("Your answer: ")).strip()
            if raw.lower() in ("q", "quit", "exit"):
                return False
            if not raw and current:
                return True
            flag = bool(re.search(r"\bf\b", raw.lower()))
            raw = re.sub(r"\bf\b", "", raw, flags=re.IGNORECASE)
            if not raw.strip() and flag:
                flagged.add(q.id)
                if current:
                    return True
                print(ui.yellow("Flagged. Now give an answer (you can change it during review)."))
                continue
            given = parse_answer(raw, q)
            if given is None or (q.multi and len(given) != len(q.answer)):
                need = f"exactly {len(q.answer)} letters" if q.multi else "one letter"
                print(ui.yellow(f"Please answer with {need} among {', '.join(q.options)}."))
                continue
            answers[q.id] = given
            if flag:
                flagged.add(q.id)
            else:
                flagged.discard(q.id)
            return True

    started = time.monotonic()
    stopped = False
    for i, q in enumerate(questions, 1):
        if not ask(q, i):
            stopped = True
            break
    while not stopped and flagged and (deadline is None or time.monotonic() < deadline):
        print(ui.rule())
        print(ui.yellow(f"{len(flagged)} question(s) flagged for review."))
        choice = input(ui.cyan("Review flagged questions now? [Y/n] ")).strip().lower()
        if choice.startswith("n"):
            break
        for i, q in enumerate(questions, 1):
            if q.id in flagged:
                if not ask(q, i):
                    stopped = True
                    break
        else:
            continue
        break

    elapsed = time.monotonic() - started
    entries = []
    for q in questions:
        given = answers[q.id]
        entries.append(_entry(session, "mock", q, given, given == q.answer, None))
    summary = _finish(root, session, "mock", entries, questions, minutes_used=round(elapsed / 60, 1))
    wrong = [q for q in questions if answers[q.id] != q.answer]
    if wrong:
        choice = input(ui.cyan(f"\nReview the {len(wrong)} missed question(s) with explanations? [Y/n] ")).strip().lower()
        if not choice.startswith("n"):
            for i, q in enumerate(wrong, 1):
                print(ui.rule())
                print(render_question(q, i, len(wrong)))
                print()
                print(explain(q, answers[q.id]))
                if i < len(wrong):
                    if input(ui.dim("\n[Enter] next · q to stop ")).strip().lower() == "q":
                        break
    return summary


def _entry(session, mode, q: Question, given, correct, seconds) -> dict:
    return {
        "type": "answer",
        "ts": now_iso(),
        "session": session,
        "mode": mode,
        "qid": q.id,
        "topic": q.topic,
        "domain": q.domain,
        "given": given,
        "correct": bool(correct),
        "seconds": seconds,
    }


def _finish(root: Path, session, mode, entries: list[dict], questions, minutes_used=None) -> dict:
    if not entries:
        print(ui.dim("No answers recorded."))
        return {}
    by_domain = defaultdict(lambda: [0, 0])
    by_topic = defaultdict(lambda: [0, 0])
    for e in entries:
        by_domain[e["domain"]][1] += 1
        by_topic[e["topic"]][1] += 1
        if e["correct"]:
            by_domain[e["domain"]][0] += 1
            by_topic[e["topic"]][0] += 1
    score = sum(e["correct"] for e in entries) / len(entries)
    summary = {
        "type": "summary",
        "ts": now_iso(),
        "session": session,
        "mode": mode,
        "n": len(entries),
        "score": round(score, 3),
        "by_domain": {str(d): v for d, v in sorted(by_domain.items())},
        "by_topic": {t: v for t, v in sorted(by_topic.items())},
        "minutes": minutes_used,
    }
    append_history(root, entries + [summary])
    print(ui.rule("═"))
    color = ui.green if score >= 0.8 else ui.yellow if score >= 0.7 else ui.red
    print(ui.bold("Result: ") + color(f"{score:.0%}") + f"  ({sum(e['correct'] for e in entries)}/{len(entries)})")
    if mode == "mock":
        print(ui.dim("Rule of thumb: aim for 80%+ on mock exams before the real one (pass mark is 720/1000, scaled)."))
    for d, (ok, total) in sorted(by_domain.items()):
        name = DOMAINS.get(d, ("?", 0))[0]
        print(f"  Domain {d} · {name:<34} {ok}/{total}  {ok / total:.0%}")
    print(ui.dim(f"Saved to {history_file(root).relative_to(root)} (session {session})."))
    return summary


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


def stats(root: Path, bank: list[Question]) -> str:
    history = read_history(root)
    answers = [e for e in history if e.get("type") == "answer"]
    if not answers:
        return "No quiz history yet. Start with `awslings quiz` or `awslings mock`."
    lines = []
    total = len(answers)
    ok = sum(e["correct"] for e in answers)
    lines.append(ui.bold(f"Answers recorded: {total} · overall accuracy {ok / total:.0%}"))
    recent = answers[-200:]
    by_domain = defaultdict(lambda: [0, 0])
    by_topic = defaultdict(lambda: [0, 0])
    for e in recent:
        by_domain[e["domain"]][1] += 1
        by_domain[e["domain"]][0] += e["correct"]
        by_topic[e["topic"]][1] += 1
        by_topic[e["topic"]][0] += e["correct"]
    lines.append("")
    lines.append(ui.bold("By domain (last 200 answers)"))
    for d in sorted(DOMAINS):
        good, n = by_domain.get(d, [0, 0])
        pct = f"{good / n:.0%}" if n else "—"
        lines.append(f"  {d}. {DOMAINS[d][0]:<34} {pct:>5}  ({good}/{n})")
    lines.append("")
    lines.append(ui.bold("Weakest topics (min. 3 answers)"))
    ranked = sorted(((g / n, t, g, n) for t, (g, n) in by_topic.items() if n >= 3))
    for pct, topic, good, n in ranked[:8]:
        lines.append(f"  {topic:<20} {pct:.0%}  ({good}/{n})")
    seen = {e["qid"] for e in answers if e.get("qid")}
    lines.append("")
    lines.append(f"Bank coverage: {len(seen & {q.id for q in bank})}/{len(bank)} questions seen.")
    mocks = [e for e in history if e.get("type") == "summary" and e.get("mode") == "mock"]
    if mocks:
        lines.append(ui.bold("Mock exams: ") + ", ".join(f"{m['score']:.0%} ({m['ts'][:10]})" for m in mocks[-5:]))
    counts = Counter(q.topic for q in bank)
    lines.append(ui.dim("Topics in bank: " + ", ".join(f"{t}({n})" for t, n in sorted(counts.items()))))
    return "\n".join(lines)
