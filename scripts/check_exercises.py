"""Maintainer check: every solution passes, every untouched exercise fails, tests are identical.

Usage:  uv run python scripts/check_exercises.py [name-filter]
"""

import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from awslings import exercises as ex_mod  # noqa: E402

# Exercises whose tests are expected to pass before any change (only the marker must go).
PASS_INITIALLY = {"intro_1"}


def check(root, ex):
    problems = []
    sol = ex_mod.Exercise(ex.name, ex.solution, str(ex.solution), ex.chapter, ex.domain, ex.hint, ex.solution)
    ok_sol, out_sol = ex_mod.run_tests(root, sol)
    if not ok_sol:
        problems.append("solution FAILS:\n" + out_sol[-3000:])
    if sol.has_marker():
        problems.append("solution still contains the marker")
    ok_ex, _ = ex_mod.run_tests(root, ex)
    if ok_ex and ex.name not in PASS_INITIALLY:
        problems.append("untouched exercise already PASSES its tests")
    if not ex.has_marker():
        problems.append("exercise has no marker")
    if ex_mod.tests_section(ex.source()) != ex_mod.tests_section(ex.solution.read_text(encoding="utf-8")):
        problems.append("tests sections differ")
    if not ex_mod.tests_section(ex.source()):
        problems.append("no tests separator found")
    return ex.name, problems


def main():
    root = ex_mod.find_root()
    exercises = ex_mod.load_exercises(root)
    if len(sys.argv) > 1:
        exercises = [e for e in exercises if sys.argv[1] in e.name]
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda e: check(root, e), exercises))
    failed = 0
    for name, problems in results:
        if problems:
            failed += 1
            print(f"✘ {name}")
            for p in problems:
                print("   " + p.replace("\n", "\n   "))
        else:
            print(f"✔ {name}")
    print(f"\n{len(results) - failed}/{len(results)} exercises OK")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
