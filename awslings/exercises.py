"""Exercise discovery, status tracking and test execution."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

MARKER_RE = re.compile(r"^[ \t]*#[ \t]*I AM NOT DONE[ \t]*$", re.MULTILINE)
TESTS_SEPARATOR = "Tests — do not edit below this line"


def find_root(start: Path | None = None) -> Path:
    """Return the repository root (the directory that contains exercises/info.toml)."""
    candidates = [start or Path.cwd()]
    candidates.append(Path(__file__).resolve().parent.parent)
    for base in candidates:
        for directory in [base, *base.parents]:
            if (directory / "exercises" / "info.toml").is_file():
                return directory
    raise SystemExit("awslings: run me from inside the repository (exercises/info.toml not found).")


@dataclass
class Exercise:
    name: str
    path: Path
    rel: str
    chapter: str
    domain: str
    hint: str
    solution: Path

    def source(self) -> str:
        return self.path.read_text(encoding="utf-8")

    def has_marker(self) -> bool:
        return bool(MARKER_RE.search(self.source()))

    def digest(self) -> str:
        return hashlib.sha1(self.path.read_bytes()).hexdigest()

    def mtime(self) -> float:
        return self.path.stat().st_mtime


def load_exercises(root: Path) -> list[Exercise]:
    data = tomllib.loads((root / "exercises" / "info.toml").read_text(encoding="utf-8"))
    exercises = []
    for item in data["exercises"]:
        rel = item["path"]
        exercises.append(
            Exercise(
                name=item["name"],
                path=root / rel,
                rel=rel,
                chapter=item.get("chapter", ""),
                domain=str(item.get("domain", "")),
                hint=item.get("hint", "").strip(),
                solution=root / rel.replace("exercises/", "solutions/", 1),
            )
        )
    return exercises


class State:
    """Remembers the last test result of each exercise, keyed by file content hash."""

    def __init__(self, root: Path):
        self.file = root / ".awslings" / "state.json"
        try:
            self.data = json.loads(self.file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.data = {"results": {}}

    def save(self):
        self.file.parent.mkdir(parents=True, exist_ok=True)
        self.file.write_text(json.dumps(self.data, indent=2, sort_keys=True), encoding="utf-8")

    def cached_pass(self, ex: Exercise) -> bool | None:
        entry = self.data["results"].get(ex.name)
        if entry and entry.get("digest") == ex.digest():
            return bool(entry.get("passed"))
        return None

    def record(self, ex: Exercise, passed: bool):
        self.data["results"][ex.name] = {"digest": ex.digest(), "passed": passed}
        self.save()

    def is_done(self, ex: Exercise) -> bool:
        return self.cached_pass(ex) is True and not ex.has_marker()


def safe_env() -> dict[str, str]:
    """Environment for test subprocesses: fake credentials, never a real profile."""
    env = dict(os.environ)
    for key in ("AWS_PROFILE", "AWS_DEFAULT_PROFILE"):
        env.pop(key, None)
    env.update(
        {
            "AWS_ACCESS_KEY_ID": "testing",
            "AWS_SECRET_ACCESS_KEY": "testing",
            "AWS_SESSION_TOKEN": "testing",
            "AWS_DEFAULT_REGION": "eu-west-3",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    return env


def run_tests(root: Path, ex: Exercise, verbose: bool = False) -> tuple[bool, str]:
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(ex.path),
        "--no-header",
        "-p",
        "no:cacheprovider",
        "-W",
        "ignore::DeprecationWarning",
        "--tb=short",
        "-rN",
    ]
    cmd.append("-v" if verbose else "-q")
    proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True, env=safe_env())
    output = (proc.stdout + proc.stderr).strip()
    if proc.returncode == 5:
        return False, output + "\n\n(no tests were collected — did you delete the tests section?)"
    return proc.returncode == 0, output


def first_pending(root: Path, exercises: list[Exercise], state: State) -> Exercise | None:
    """First exercise (in order) that is not done. Re-runs tests when a file changed."""
    for ex in exercises:
        cached = state.cached_pass(ex)
        if cached is None:
            passed, _ = run_tests(root, ex)
            state.record(ex, passed)
            cached = passed
        if not cached or ex.has_marker():
            return ex
    return None


def find(exercises: list[Exercise], name: str) -> Exercise:
    for ex in exercises:
        if ex.name == name:
            return ex
    matches = [ex for ex in exercises if name in ex.name]
    if len(matches) == 1:
        return matches[0]
    names = ", ".join(ex.name for ex in matches) or "none"
    raise SystemExit(f"awslings: unknown exercise '{name}' (matches: {names}). Try `awslings list`.")


def tests_section(text: str) -> str:
    index = text.find(TESTS_SEPARATOR)
    return text[index:] if index >= 0 else ""
