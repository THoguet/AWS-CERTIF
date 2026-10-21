---
name: quiz
description: Run an exam-style DVA-C02 quiz in chat, one question at a time, on a topic, a domain or the learner's weak spots, using the repo's question bank plus original questions, with explanations, and log every answer. Use when the learner says "quiz me", "test me", "ask me questions about X".
---

# /quiz — exam-style questions in chat

Arguments (optional): topic slug(s), domain number, count, e.g. `/quiz lambda 10` or `/quiz d2`.
Requested: $ARGUMENTS

## Pick the questions
1. Default: 10 questions on the topics due in PROGRESS.md's weak-spot queue, otherwise on the
   current plan chapter.
2. Prefer bank questions the learner has never answered or got wrong. Read
   `quizzes/bank/*.yaml` and look up their history in `progress/quiz-history.jsonl` (lines with
   `"type": "answer"` and a `qid`).
3. Mix in about 30% ORIGINAL questions you write, aimed at the learner's mistake log. Use the
   exam style: a realistic scenario, 4 options (one answer) or 5 options with "(Choose TWO.)",
   plausible distractors, one clearly best answer. Never reproduce real exam questions.

## Ask
- One question at a time. Show the id for bank questions. Do NOT reveal the answer, and wait.
- After the answer: ✔/✘, the correct option(s), why it is right, and why EACH distractor is wrong.
  Name the deciding keyword in the question. Point to the book section.
- If they answer with a guess ("not sure, B?"), still log it but note the uncertainty.

## Log
After each answer:
- bank question: `uv run awslings record --qid <id> --given <letters>`
- your question: `uv run awslings record --topic <slug> --domain <n> --result correct|wrong --note "<concept tested>"`

## Wrap up
Show the score, the concepts missed and the next action. Update PROGRESS.md: weak-spot queue
(+1/+3/+7 days for each missed concept), mistake log, session log.
