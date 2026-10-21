---
name: explain
description: Explain an AWS concept or compare services for the DVA-C02 exam (how it works, exam angle, traps, limits, a tiny example, where to practice). Use when the learner asks "what is", "how does", "difference between", "when should I use", or is confused by a quiz explanation.
---

# /explain — teach one concept for the exam

Concept: $ARGUMENTS

1. Find the relevant section in `book/src/` (grep the concept) and stay consistent with it.
   If the book is wrong or outdated, say so and suggest a fix.
2. Answer in this order, compactly:
   1. **In one sentence**: what it is / the answer.
   2. **How it works**: the mechanism, with a small diagram in text or a table if it helps.
   3. **Exam angle**: which domain/task, how questions are phrased, the keywords pointing to it.
   4. **Traps**: common distractors and misconceptions (check the learner's mistake log in PROGRESS.md).
   5. **Numbers to remember**: only the ones you are sure of. Flag anything that changed recently.
   6. **Tiny example**: CLI/boto3/template snippet (≤ 10 lines) when useful.
   7. **Practice**: exercise id(s) and `uv run awslings quiz <topic>`.
3. Finish with ONE check question (original, exam style) to confirm understanding. Log the answer
   with `uv run awslings record`.
4. For comparisons ("SQS vs SNS vs EventBridge vs Kinesis"), lead with a decision table:
   rows = criteria (delivery, ordering, retention, consumers, throughput, typical use), columns = services.
