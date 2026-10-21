# AWS-CERTIF — pass DVA-C02, the hands-on way

A self-paced course for the **AWS Certified Developer – Associate (DVA-C02)** exam, built like
*The Rust Programming Language* book + *rustlings*: read a chapter, then make failing tests pass,
one small exercise at a time. A Claude Code tutor keeps track of your progress between sessions.

> **Deadline** — DVA-C02 can be taken until **30 November 2026**. DVA-C03 replaces it on
> 1 December 2026. Book your slot early (see `book/src/ch00-exam-strategy.md`).

| Piece | Where | What you get |
|---|---|---|
| 📖 **Book** | `book/src/` | 27 chapters (ch00–ch26) + glossary, mapped to the four exam domains, with exam tips, traps and self-checks |
| 🦀→☁️ **awslings** | `exercises/` | 83 Python + boto3 exercises, tested offline against **moto** (mocked AWS): no account, no cost |
| ❓ **Question bank** | `quizzes/bank/` | 313 original exam-style questions with explanations, 23 topics, and timed **65-question mock exams** |
| 🧪 **Labs** | `labs/` | 7 optional labs on a real AWS account (SAM canary, Cognito, Step Functions, CI/CD, X-Ray, Beanstalk), with costs and teardown |
| 🧑‍🏫 **Tutor** | `CLAUDE.md`, `.claude/skills/` | A Claude Code coach: plans your day, quizzes you, explains, drills numbers, and updates `PROGRESS.md` |
| 🗓️ **Plan** | `STUDY_PLAN.md`, `EXAM_GUIDE.md` | 35 days, about 1–1.5 h per day, from 22 Oct to the exam, plus exam facts and the domain → content map |

## Quick start

You need **Python ≥ 3.11** and [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
git clone <this repository> AWS-CERTIF && cd AWS-CERTIF
uv sync                  # installs boto3, moto, pytest, cfn-lint... in .venv
uv run awslings          # watch mode: shows the current exercise and re-runs its tests on every save
```

Open the exercise file it names in your editor, read the instructions at the top, write the code,
save. When the tests pass, delete the `# I AM NOT DONE` line to move on. In watch mode, type
`h` + Enter for a hint, `l` for the list, `r` to re-run, `q` to quit.

Read the book in any Markdown viewer, or as a website with [mdBook](https://rust-lang.github.io/mdBook/):
`mdbook serve book --open`.

## A day of study

`STUDY_PLAN.md` gives one row per day. Each session follows the same loop:

1. **Read** the chapter of the day (30–45 min).
2. **Practice** its exercises: `uv run awslings` (20–30 min).
3. **Check** yourself with a quiz: `uv run awslings quiz <topic>` (10–15 min).
4. **Debrief** with the tutor: `/progress` in Claude Code.

Two weeks before the exam, switch to mock exams. You are ready when you score **≥ 80%** on mocks and
**≥ 70% in every domain**.

## Commands

```bash
uv run awslings                         # watch mode (default)
uv run awslings list                    # all exercises and their status
uv run awslings run [name]              # run one exercise's tests
uv run awslings hint [name]             # hint for the current (or named) exercise
uv run awslings verify                  # re-check everything, stop at the first unfinished exercise
uv run awslings solution <name>         # reference solution (once the exercise is done; --force if stuck)
uv run awslings reset <name>            # restore an exercise to its original content

uv run awslings quiz lambda dynamodb -n 15    # questions on topics, with immediate explanations
uv run awslings quiz -d 2 -n 20               # questions from one domain (1-4)
uv run awslings quiz --wrong                  # replay the questions you got wrong
uv run awslings mock                          # 65 questions, 130 minutes, weighted 32/26/24/18%
uv run awslings stats                         # exercise progress, accuracy by domain and topic
```

Quiz topics: foundations, iam, sdk, s3, lambda, apigw, dynamodb, caching, messaging, streaming,
patterns, cognito, kms, secrets, cloudformation, sam, cicd, containers, testing, monitoring, xray,
troubleshooting, optimization.

## The tutor (Claude Code)

Run `claude` at the root of the repository. Claude Code loads `CLAUDE.md`, which makes it your coach
for DVA-C02: it knows the plan, the book, the exercises and your progress. Slash commands:

| Command | What it does |
|---|---|
| `/today` | Plans today's session from `STUDY_PLAN.md` and `PROGRESS.md`, including spaced-repetition reviews |
| `/quiz [topic]` | Exam-style questions in chat, one at a time, logged to your history |
| `/explain <concept>` | How something works, the exam angle, the traps, where to practice |
| `/drill` | Rapid-fire recall of numbers, limits, defaults and "which service" one-liners |
| `/check-exercise [name]` | Runs your exercise, explains failures with graduated hints |
| `/mock-exam` | Prepares or debriefs a mock exam: misses by domain, patterns, review plan |
| `/progress` | Recomputes and updates `PROGRESS.md` (domains, weak spots, mistake log) |

Your answers are logged to `progress/quiz-history.jsonl` (by the CLI and the tutor), and the
tutor's notes go to `PROGRESS.md`. **Commit these two files** regularly: they are your memory
between sessions and machines. The tutor never commits or pushes unless you ask.

## Labs (optional, real AWS)

The exercises never touch AWS. The labs do: they deploy small applications to your account, break
them on purpose, and show how AWS reacts (CodeDeploy rollbacks, Step Functions catches, alarms,
immutable deployments...). Start with `labs/lab00-account-setup` (budget alert, MFA, CLI profile),
read `labs/README.md`, and always run the **Teardown** section at the end.

## Repository map

```text
book/src/            the course (mdBook): SUMMARY.md is the table of contents
exercises/           awslings exercises, ordered by exercises/info.toml (which also holds the hints)
solutions/           reference solutions (same tests)
quizzes/bank/        the question bank, one YAML file per chapter (format: quizzes/README.md)
labs/                optional real-AWS labs (lab00 to lab06)
progress/            your quiz history (written by awslings and the tutor)
awslings/            the CLI: exercise runner, quizzes, mock exams, stats
.claude/skills/      the tutor's slash commands
CLAUDE.md            the tutor's standing instructions
EXAM_GUIDE.md        exam facts, domains → chapters/exercises/topics, AWS changes since the exam guide
STUDY_PLAN.md        the day-by-day plan
PROGRESS.md          your progress (maintained by the tutor)
tests/, scripts/     checks for the repository itself
```

## Checking the repository

```bash
uv run awslings validate                     # info.toml, exercises vs solutions, question bank rules
uv run pytest                                # tool tests, lab unit tests (moto), lab templates (cfn-lint)
uv run python scripts/check_exercises.py     # every solution passes, every untouched exercise fails
```

## Accuracy and disclaimer

- This is an independent study project. It is not affiliated with or endorsed by Amazon Web Services.
- Every question is original. None comes from the real exam or from "dumps".
- AWS changes faster than the exam guide (v2.1, December 2024). `EXAM_GUIDE.md` lists the changes
  that matter (SQS 1 MiB messages, X-Ray SDKs in maintenance mode, CodeCommit back to general
  availability...) and what the exam is likely to expect. When in doubt, the official AWS
  documentation wins. Please fix this repository when you find a mistake.
- Labs use a real AWS account and can cost money. Use a budget alert and tear everything down.
