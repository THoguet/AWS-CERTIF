---
name: today
description: Plan today's DVA-C02 study session from STUDY_PLAN.md and PROGRESS.md (reading, awslings exercises, quiz, spaced-repetition reviews). Use when the learner starts a session, says "what do I do today", "let's study", or gives no instruction.
---

# /today — plan the study session

1. Read `PROGRESS.md` and `STUDY_PLAN.md`. Get today's date with `date +%F`.
2. Work out:
   - the plan day matching today's date, or the next unfinished day if they are behind or ahead,
   - days left until the booked exam (or until 2026-11-30 if not booked),
   - review items due today in the "Weak spots" table,
   - exercise progress: `uv run awslings list` (current exercise is marked ▶).
3. Propose a session of about 60–90 minutes as a short checklist:
   - **Warm-up (5–10 min)**: 3–5 quick recall questions on the weak spots due today
     (ask them one at a time, then log them with `uv run awslings record`).
   - **Read (30–40 min)**: the chapter and sections, with 3 things to watch for in the exam.
   - **Practice (20–30 min)**: exercises to do (`uv run awslings`).
   - **Check (10–15 min)**: the quiz command (`uv run awslings quiz <topic> -n 10`), or an in-chat quiz with `/quiz`.
4. If they are behind schedule, say so plainly and suggest how to catch up: merge a review day,
   skip optional labs, shorten the reading by focusing on the "Exam tip" callouts. Remember that
   DVA-C02 cannot be taken after 30 Nov 2026.
5. Ask which block they want to start with. Keep the whole answer short.
