"""Command line interface: `awslings [watch|list|run|hint|verify|solution|reset|quiz|mock|stats|record|validate]`."""

from __future__ import annotations

import argparse
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

from awslings import __version__, ui
from awslings import exercises as ex_mod
from awslings import quiz as quiz_mod

WATCH_HELP = "h + Enter: hint · l: list · r: re-run · q: quit"


def _status_icon(state: ex_mod.State, ex: ex_mod.Exercise, current: ex_mod.Exercise | None) -> str:
    if current is not None and ex.name == current.name:
        return ui.yellow("▶")
    if state.is_done(ex):
        return ui.green("✔")
    return ui.dim("·")


def cmd_list(root, exercises, state, args) -> int:
    current = ex_mod.first_pending(root, exercises, state)
    done = sum(state.is_done(e) for e in exercises)
    print(ui.bold(f"{'':2}{'Name':<16}{'Chapter':<16}{'Domain':<8}Path"))
    for e in exercises:
        print(f"{_status_icon(state, e, current)} {e.name:<16}{e.chapter:<16}{e.domain:<8}{ui.dim(e.rel)}")
    print()
    print(ui.progress_bar(done, len(exercises)))
    return 0


def _show_result(root, ex, exercises, state, passed, output):
    done = sum(state.is_done(e) for e in exercises)
    ui.clear_screen()
    print(ui.bold(f"awslings — {ex.name}") + ui.dim(f"  ({ex.rel} · {ex.chapter} · domain {ex.domain})"))
    print(ui.progress_bar(done, len(exercises)))
    print(ui.rule())
    print(output[-6000:] if output else "")
    print(ui.rule())
    if not passed:
        print(ui.red(f"✘ {ex.name}: tests are failing.") + " Edit " + ui.bold(ex.rel) + " and save — I re-run automatically.")
    elif ex.has_marker():
        print(ui.green(f"✔ {ex.name}: all tests pass!"))
        print("  Read the code once more, then delete the line " + ui.bold("# I AM NOT DONE") + " to move on.")
    print(ui.dim(WATCH_HELP))


def _stdin_reader(commands: queue.Queue):
    while True:
        try:
            line = sys.stdin.readline()
        except (OSError, ValueError):
            return
        if not line:
            commands.put("q")
            return
        commands.put(line.strip().lower())


def cmd_watch(root, exercises, state, args) -> int:
    commands: queue.Queue = queue.Queue()
    threading.Thread(target=_stdin_reader, args=(commands,), daemon=True).start()
    while True:
        ex = ex_mod.first_pending(root, exercises, state)
        if ex is None:
            ui.clear_screen()
            print(ui.green(ui.box("🎉 All awslings exercises are done!")))
            print("Next: `awslings mock` for a timed 65-question exam, or ask your tutor for a review session.")
            return 0
        passed, output = ex_mod.run_tests(root, ex)
        state.record(ex, passed)
        if passed and not ex.has_marker():
            continue  # finished right away, move on
        _show_result(root, ex, exercises, state, passed, output)
        last_mtime = ex.mtime()
        while True:
            try:
                command = commands.get(timeout=0.5)
            except queue.Empty:
                command = None
            if command in ("q", "quit", "exit"):
                return 0
            if command in ("h", "hint"):
                print(ui.rule())
                print(ui.cyan("Hint: ") + (ex.hint or "No hint for this one — read the docstring and the tests."))
                print(ui.dim(WATCH_HELP))
            elif command in ("l", "list"):
                print(ui.rule())
                cmd_list(root, exercises, state, args)
                print(ui.dim(WATCH_HELP))
            elif command in ("r", "run", "rerun"):
                break
            try:
                mtime = ex.mtime()
            except OSError:
                continue
            if mtime != last_mtime:
                time.sleep(0.15)  # let editors finish writing
                prev_done = state.is_done(ex)
                passed, output = ex_mod.run_tests(root, ex)
                state.record(ex, passed)
                if passed and not ex.has_marker():
                    if not prev_done:
                        print(ui.green(f"\n✔ {ex.name} done!") + ui.dim(f"  Reference solution: {ex.solution.relative_to(root)}"))
                        time.sleep(1.5)
                    break
                _show_result(root, ex, exercises, state, passed, output)
                last_mtime = ex.mtime()


def _target(root, exercises, state, name):
    if name:
        return ex_mod.find(exercises, name)
    ex = ex_mod.first_pending(root, exercises, state)
    if ex is None:
        raise SystemExit("All exercises are done! Pass a name to run a specific one.")
    return ex


def cmd_run(root, exercises, state, args) -> int:
    ex = _target(root, exercises, state, args.name)
    passed, output = ex_mod.run_tests(root, ex, verbose=args.verbose)
    state.record(ex, passed)
    print(output)
    print(ui.rule())
    if not passed:
        print(ui.red(f"✘ {ex.name}: tests are failing.") + ui.dim(f"  Need help? awslings hint {ex.name}"))
        return 1
    if ex.has_marker():
        print(ui.green(f"✔ {ex.name}: tests pass.") + " Remove `# I AM NOT DONE` to mark it done.")
    else:
        print(ui.green(f"✔ {ex.name}: done!"))
    return 0


def cmd_hint(root, exercises, state, args) -> int:
    ex = _target(root, exercises, state, args.name)
    print(ui.bold(f"Hint for {ex.name}") + ui.dim(f" ({ex.rel})"))
    print(ex.hint or "No hint for this one — read the docstring and the tests.")
    return 0


def cmd_verify(root, exercises, state, args) -> int:
    for i, ex in enumerate(exercises, 1):
        print(f"[{i}/{len(exercises)}] {ex.name:<16}", end="", flush=True)
        passed, output = ex_mod.run_tests(root, ex)
        state.record(ex, passed)
        if not passed:
            print(ui.red("FAIL"))
            print(output)
            return 1
        if ex.has_marker():
            print(ui.yellow("tests pass, but `# I AM NOT DONE` is still there"))
            return 1
        print(ui.green("ok"))
    print(ui.green("All exercises verified!"))
    return 0


def cmd_solution(root, exercises, state, args) -> int:
    ex = _target(root, exercises, state, args.name)
    if not state.is_done(ex) and not args.force:
        print(ui.yellow(f"Finish {ex.name} first (or use --force if you are really stuck)."))
        print(ui.dim(f"Hint: awslings hint {ex.name}"))
        return 1
    if not ex.solution.exists():
        print(ui.red(f"No reference solution found at {ex.solution.relative_to(root)}"))
        return 1
    text = ex.solution.read_text(encoding="utf-8")
    cut = text.find(ex_mod.TESTS_SEPARATOR)
    print(ui.dim(f"# {ex.solution.relative_to(root)}"))
    print(text[: text.rfind("\n", 0, cut)] if cut > 0 else text)
    return 0


def cmd_reset(root, exercises, state, args) -> int:
    ex = ex_mod.find(exercises, args.name)
    proc = subprocess.run(["git", "checkout", "--", ex.rel], cwd=root, capture_output=True, text=True)
    if proc.returncode != 0:
        print(ui.red(proc.stderr.strip() or "git checkout failed"))
        return 1
    print(ui.green(f"{ex.name} restored to its original state."))
    return 0


def cmd_quiz(root, exercises, state, args) -> int:
    bank = quiz_mod.load_bank(root)
    history = quiz_mod.read_history(root)
    questions = quiz_mod.select(
        bank,
        history,
        topics=args.topics,
        domain=args.domain,
        count=args.n,
        only_wrong=args.wrong,
        only_new=args.new,
    )
    if not questions:
        print(ui.yellow("No question matches these filters."))
        topics = sorted({q.topic for q in bank})
        print(ui.dim("Topics: " + ", ".join(topics)))
        return 1
    try:
        quiz_mod.run_quiz(root, questions)
    except (KeyboardInterrupt, EOFError):
        print(ui.dim("\nQuiz interrupted (answers given so far were not saved)."))
    return 0


def cmd_mock(root, exercises, state, args) -> int:
    bank = quiz_mod.load_bank(root)
    history = quiz_mod.read_history(root)
    questions = quiz_mod.select_mock(bank, history, count=args.n)
    if len(questions) < args.n:
        print(ui.yellow(f"Only {len(questions)} questions available for the domain mix."))
    minutes = args.minutes if args.minutes else round(quiz_mod.EXAM_MINUTES * len(questions) / quiz_mod.EXAM_QUESTIONS)
    try:
        quiz_mod.run_mock(root, questions, minutes=minutes, timer=not args.no_timer)
    except (KeyboardInterrupt, EOFError):
        print(ui.dim("\nMock exam interrupted (not saved)."))
    return 0


def cmd_stats(root, exercises, state, args) -> int:
    done = sum(state.is_done(e) for e in exercises)
    print(ui.bold("Exercises: ") + ui.progress_bar(done, len(exercises)))
    print()
    print(quiz_mod.stats(root, quiz_mod.load_bank(root)))
    return 0


def cmd_record(root, exercises, state, args) -> int:
    """Used by the tutor agent to log answers given in chat into progress/quiz-history.jsonl."""
    bank = {q.id: q for q in quiz_mod.load_bank(root)}
    entry = {"type": "answer", "ts": quiz_mod.now_iso(), "session": args.session or "tutor", "mode": "tutor"}
    if args.qid:
        q = bank.get(args.qid)
        if q is None:
            print(ui.red(f"Unknown question id {args.qid}"))
            return 1
        given = sorted({c for c in (args.given or "").upper() if c.isalpha()}) or None
        entry.update({"qid": q.id, "topic": q.topic, "domain": q.domain, "given": given, "correct": given == q.answer})
    else:
        if not (args.topic and args.domain and args.result):
            print(ui.red("Ad-hoc records need --topic, --domain and --result correct|wrong (or use --qid)."))
            return 1
        entry.update(
            {"qid": None, "topic": args.topic, "domain": args.domain, "given": None, "correct": args.result == "correct", "note": args.note}
        )
    quiz_mod.append_history(root, [entry])
    print(("✔ recorded correct" if entry["correct"] else "✘ recorded wrong") + f" · {entry['topic']} · domain {entry['domain']}")
    return 0


def cmd_validate(root, exercises, state, args) -> int:
    problems = quiz_mod.validate_bank(root)
    names = set()
    for e in exercises:
        if e.name in names:
            problems.append(f"info.toml: duplicate exercise name {e.name}")
        names.add(e.name)
        if not e.path.exists():
            problems.append(f"info.toml: {e.name}: missing file {e.rel}")
            continue
        if not e.solution.exists():
            problems.append(f"info.toml: {e.name}: missing solution {e.solution.relative_to(root)}")
        elif ex_mod.tests_section(e.source()) != ex_mod.tests_section(e.solution.read_text(encoding="utf-8")):
            problems.append(f"{e.name}: tests section differs between exercise and solution")
        if not e.has_marker():
            problems.append(f"{e.name}: exercise file has no `# I AM NOT DONE` marker")
        if not e.hint:
            problems.append(f"{e.name}: missing hint")
    bank = quiz_mod.load_bank(root) if not problems else []
    for p in problems:
        print(ui.red("✘ ") + p)
    if problems:
        return 1
    print(ui.green(f"✔ {len(exercises)} exercises and {len(bank)} questions look good."))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="awslings",
        description="Rustlings-style exercises, quizzes and mock exams for AWS DVA-C02. Without a command: watch mode.",
    )
    parser.add_argument("--version", action="version", version=f"awslings {__version__}")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("watch", help="work through the exercises in order, re-running tests on save (default)")
    sub.add_parser("list", help="show all exercises and their status")
    p = sub.add_parser("run", help="run the tests of one exercise (default: the current one)")
    p.add_argument("name", nargs="?")
    p.add_argument("-v", "--verbose", action="store_true")
    p = sub.add_parser("hint", help="show the hint of an exercise (default: the current one)")
    p.add_argument("name", nargs="?")
    sub.add_parser("verify", help="run every exercise in order and stop at the first unfinished one")
    p = sub.add_parser("solution", help="show the reference solution of a finished exercise")
    p.add_argument("name", nargs="?")
    p.add_argument("--force", action="store_true", help="show it even if the exercise is not done")
    p = sub.add_parser("reset", help="restore an exercise file to its original content (uses git)")
    p.add_argument("name")
    p = sub.add_parser("quiz", help="exam-style questions with immediate explanations")
    p.add_argument("topics", nargs="*", help="topics or chapters, e.g. lambda dynamodb ch07 (default: all)")
    p.add_argument("-n", type=int, default=10, help="number of questions (default 10)")
    p.add_argument("-d", "--domain", type=int, choices=[1, 2, 3, 4])
    p.add_argument("--wrong", action="store_true", help="only questions you got wrong last time")
    p.add_argument("--new", action="store_true", help="only questions you have never answered")
    p = sub.add_parser("mock", help="timed mock exam (65 questions / 130 minutes, weighted like DVA-C02)")
    p.add_argument("-n", type=int, default=quiz_mod.EXAM_QUESTIONS)
    p.add_argument("--minutes", type=int, default=0, help="time limit (default: 2 minutes per question)")
    p.add_argument("--no-timer", action="store_true")
    sub.add_parser("stats", help="exercise progress and quiz accuracy by domain/topic")
    p = sub.add_parser("record", help="(for the tutor agent) log an answer given in chat")
    p.add_argument("--qid", help="question id from the bank")
    p.add_argument("--given", help="letters chosen, e.g. B or AC")
    p.add_argument("--topic")
    p.add_argument("--domain", type=int, choices=[1, 2, 3, 4])
    p.add_argument("--result", choices=["correct", "wrong"])
    p.add_argument("--note")
    p.add_argument("--session")
    sub.add_parser("validate", help="check info.toml, exercises/solutions and the question bank")
    return parser


COMMANDS = {
    None: cmd_watch,
    "watch": cmd_watch,
    "list": cmd_list,
    "run": cmd_run,
    "hint": cmd_hint,
    "verify": cmd_verify,
    "solution": cmd_solution,
    "reset": cmd_reset,
    "quiz": cmd_quiz,
    "mock": cmd_mock,
    "stats": cmd_stats,
    "record": cmd_record,
    "validate": cmd_validate,
}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = ex_mod.find_root(Path.cwd())
    exercises = ex_mod.load_exercises(root)
    state = ex_mod.State(root)
    try:
        return COMMANDS[args.command](root, exercises, state, args) or 0
    except KeyboardInterrupt:
        print()
        return 130
