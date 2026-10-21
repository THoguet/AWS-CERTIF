---
name: mock-exam
description: Prepare, debrief or run a DVA-C02 mock exam - analyze `awslings mock` results by domain and topic, review every missed question, find patterns, and update PROGRESS.md. Use when the learner says "mock exam", "practice exam", "I finished the mock", or "am I ready".
---

# /mock-exam — rehearse and debrief

Mode (optional): $ARGUMENTS ("debrief" by default, "run" to do a mock in chat, "mini" for 20 questions).

## Before a mock (if the learner has not done it yet)
- Recommend the timed CLI version: `uv run awslings mock` (65 questions, 130 min, flagging, no
  feedback until the end), done in ONE sitting with no notes.
- Exam technique reminders: about 2 min per question, flag and move on, read the LAST sentence
  first (what is asked), eliminate two options, look for the deciding keyword, never leave blanks.

## Debrief (after `awslings mock`)
1. Read the latest `"type": "summary"` line with `"mode": "mock"` in `progress/quiz-history.jsonl`
   and the answers of that session (same `session` id).
2. Report: overall score, score per domain against the exam weights, time used, and the
   comparison with previous mocks (trend).
3. Group the misses by CONCEPT, not by question (e.g. "Lambda async vs sync error handling" ×3).
   For each group: the rule to remember in one sentence and where to review it (book section, exercise).
4. Ask the learner to re-answer 3–5 of the missed questions in their own words. Log them with
   `uv run awslings record`.
5. Readiness verdict (be honest): ready if ≥ 80% on two consecutive mocks and every domain ≥ 70%.
   Otherwise give a concrete 2–3 day plan before the next mock. Remember the deadline: 30 Nov 2026.
6. Update PROGRESS.md: mock scores, domain table, weak spots, mistake log, session log.

## Run in chat ("run" / "mini")
Pick questions weighted by domain (32/26/24/18%) from the bank (unseen first) plus original ones.
Ask them one by one WITHOUT feedback, collect the answers, then grade everything at the end and
debrief as above. Log each answer with `uv run awslings record`.
