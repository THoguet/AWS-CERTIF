---
name: check-exercise
description: Review the learner's current (or named) awslings exercise, run its tests, explain failures with graduated hints, and give exam-oriented feedback once it passes. Use when the learner is stuck on an exercise, says "check my code", "why does this fail", or "review my solution".
---

# /check-exercise — help with an awslings exercise

Exercise (optional): $ARGUMENTS (default: the current one).

1. Find it: `uv run awslings list` (▶ = current), then read the exercise file, its docstring, its
   tests and its hint in `exercises/info.toml`.
2. Run `uv run awslings run <name>` and read the failure.
3. If it fails, use the **hint ladder**:
   1. Point at the failing test and ask what it expects.
   2. Name the concept and the book section (and the botocore/boto3 call or parameter involved).
   3. Show a minimal snippet for the missing piece only, never the whole solution unless they ask.
   Do NOT edit the exercise file unless the learner asks you to.
4. If it passes:
   - review the code for AWS best practices (least privilege, retries, pagination, idempotency,
     no secrets in code, clients created once...),
   - connect it to the exam: "this is what a question about X looks like", with one original check question,
   - remind them to delete `# I AM NOT DONE` to move on, and that `uv run awslings solution <name>`
     shows the reference solution.
5. Note recurring difficulties in PROGRESS.md (mistake log / weak spots).
