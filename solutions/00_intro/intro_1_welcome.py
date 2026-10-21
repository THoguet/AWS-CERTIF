"""
Exercise intro_1 — Welcome to awslings!
=======================================
Book: Introduction (book/src/introduction.md)

awslings works like rustlings: every exercise is a small Python file with
  * a task description (this docstring),
  * some code for you to complete,
  * tests at the bottom of the file.

`uv run awslings` (watch mode) re-runs the tests of the current exercise
every time you save. An exercise is done when:
  1. all its tests pass, and
  2. you have deleted the `# I AM NOT DONE` line.

All tests run offline against moto, an in-memory mock of AWS: no account,
no cost, no risk of touching real resources.

Your task
---------
The tests already pass. Read the code below, then delete the
`# I AM NOT DONE` line and save the file.
"""

EXAM_CODE = "DVA-C02"
DOMAINS = {
    1: "Development with AWS Services",
    2: "Security",
    3: "Deployment",
    4: "Troubleshooting and Optimization",
}


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run intro_1
# =============================================================================


def test_exam_code():
    assert EXAM_CODE == "DVA-C02"


def test_four_domains():
    assert len(DOMAINS) == 4
