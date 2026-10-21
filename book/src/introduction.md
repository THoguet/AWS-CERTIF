# Introduction

Welcome! This book is the theory half of a complete preparation for the
**AWS Certified Developer – Associate** exam (code **DVA-C02**). The practice half lives next to it:

| Piece | Where | What it does |
|---|---|---|
| 📖 The book | `book/src/` | 27 chapters covering the four exam domains, with exam tips, traps and self-checks |
| 🦀→☁️ awslings | `exercises/` | 83 small coding exercises (Python + boto3), checked offline against a mocked AWS, rustlings style |
| ❓ Question bank | `quizzes/bank/` | Original exam-style questions with explanations, timed mock exams |
| 🧪 Labs | `labs/` | Optional guided labs on a real AWS account, with cost estimates and teardown |
| 🧑‍🏫 Tutor | `CLAUDE.md`, `.claude/skills/` | A Claude Code coach that quizzes you, explains, and tracks your progress |

The structure is inspired by *The Rust Programming Language* book and the *rustlings* exercises:
read a chapter, then make failing tests pass, one small exercise at a time.

## Who this is for

You have written code before and have touched AWS a little (created a bucket, deployed a Lambda
function, clicked around the console). You want to pass DVA-C02 in a few weeks and, along the way,
actually understand how to build applications on AWS.

> **Deadline** — DVA-C02 can be taken until **30 November 2026**. DVA-C03 replaces it on
> 1 December 2026. Book your slot early. See [Exam strategy](ch00-exam-strategy.md).

## How to use this book

Follow `STUDY_PLAN.md` at the root of the repository. Each day:

1. **Read** one chapter (or half of a long one). Focus on the callouts:
   > **Exam tip** — what the exam tends to ask, and how to recognize the right answer.

   > **Trap** — a classic wrong answer, or a misconception that costs points.
2. **Practice** with the chapter's exercises: `uv run awslings`.
3. **Check** with a quiz: `uv run awslings quiz <topic>`.
4. **Debrief** with the tutor: `/progress` in Claude Code.

Each chapter ends with **Check yourself** questions. Answer them out loud before opening
the hidden answers. Retrieving an answer from memory is what makes it stick.

## Reading the book

The chapters are plain Markdown and render nicely in Gitea. For a searchable website with
a sidebar, install [mdBook](https://rust-lang.github.io/mdBook/) and run:

```bash
cargo install mdbook        # or download a release binary
mdbook serve book --open    # http://localhost:3000
```

## Setting up the exercises

```bash
# Python 3.11+ and uv (https://docs.astral.sh/uv/)
uv sync                  # creates .venv with boto3, moto, pytest...
uv run awslings          # watch mode: shows the current exercise and re-runs its tests on save
```

You do **not** need an AWS account for the exercises. They run against
[moto](https://github.com/getmoto/moto), an in-memory implementation of AWS APIs, and fake
credentials are forced by `conftest.py`, so nothing can reach your real account by accident.

A few commands to know:

| Command | Purpose |
|---|---|
| `uv run awslings` | Watch mode (type `h` + Enter for a hint, `l` for the list, `q` to quit) |
| `uv run awslings list` | All exercises and their status |
| `uv run awslings hint [name]` | Hint for the current (or named) exercise |
| `uv run awslings solution <name>` | Reference solution, once the exercise is done |
| `uv run awslings quiz lambda -n 10` | 10 exam-style questions on Lambda |
| `uv run awslings mock` | Full timed mock exam (65 questions, 130 minutes) |
| `uv run awslings stats` | Your accuracy by domain and topic |

## Working with the tutor

Open the repository with [Claude Code](https://claude.com/claude-code) (`claude` in the repo root).
It reads `CLAUDE.md`, which tells it who you are, how to coach you, and where everything is.
Useful slash commands:

| Command | What happens |
|---|---|
| `/today` | Plans today's session from the study plan and your weak spots |
| `/quiz [topic] [n]` | Exam-style questions in chat, one at a time, logged to your history |
| `/explain <concept>` | A focused explanation with the exam angle and traps |
| `/drill [topic]` | Rapid-fire numbers and limits |
| `/check-exercise [name]` | Help on an exercise with graduated hints |
| `/mock-exam` | Debrief of a mock exam, readiness verdict |
| `/progress` | Updates `PROGRESS.md` |

## Conventions

- Code samples use **Python 3.12 + boto3** and the **AWS CLI v2**. The exam is language-agnostic,
  but the concepts (SDK retries, pagination, credentials, idempotency) are the same in every SDK.
- Region examples use **eu-west-3 (Paris)**.
- "MB/GB" follow AWS documentation usage. When it matters (Lambda memory, Kinesis), we note it.
- Limits and defaults are those documented by AWS as of late 2026. Where AWS changed something
  after the exam guide was written (v2.1, December 2024), the book tells you what the exam is
  likely to expect. See also `EXAM_GUIDE.md`.

Let's start with the exam itself.
