---
name: progress
description: Recompute and update PROGRESS.md (exercise completion, quiz accuracy by domain/topic, weak-spot review queue, mistake log, session log, readiness, days left) from awslings data and the current conversation. Use at the end of a study session, when the learner says "update my progress", "where am I", or "how am I doing".
---

# /progress — update the learner's state

1. Gather the data:
   - `date +%F` (today) and the exam date from PROGRESS.md (default deadline 2026-11-30) → days left,
   - `uv run awslings stats` → accuracy by domain, weakest topics, mock scores, exercises done,
   - `uv run awslings list` → exercises done per chapter,
   - what happened in this conversation (chapters read, difficulties, misconceptions).
2. Update `PROGRESS.md` in place:
   - **Snapshot**: current plan day, exercises done, questions answered, mock scores, readiness
     estimate (not ready / getting there / ready) with one line of justification,
   - **Domain readiness**: accuracy and trend (↗ ↘ →) compared with the previous values in the file,
   - **Chapters**: tick what was read, exercise counts, quiz done, confidence (ask the learner for a 1–5 if unknown),
   - **Weak spots**: add new weak topics (next review at +1 day). Move reviewed ones to +3 then +7 days,
     and remove them after two successful reviews,
   - **Mistake log**: one dated line per new misconception,
   - **Session log**: one line for today.
3. Show the learner a 5-line summary: days left, today's wins, the top 3 weak spots, the next session's focus.
Do not commit unless asked.
