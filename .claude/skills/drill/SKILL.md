---
name: drill
description: Rapid-fire recall drill of DVA-C02 numbers, limits, defaults, API names and "which service" one-liners, with spaced repetition. Use when the learner says "drill", "flashcards", "numbers", "limits", or before the exam.
---

# /drill — rapid-fire recall

Scope (optional): $ARGUMENTS (a topic slug, "week1", "all", or "weak").

1. Build 15 short prompts from `book/src/ch24-numbers-limits.md` and the chapter(s) in scope.
   Favor the learner's weak spots and mistake log in PROGRESS.md. Mix three kinds:
   - numbers ("Lambda max timeout?", "DynamoDB max item size?", "SQS max visibility timeout?"),
   - defaults ("Default SQS retention?", "Default API Gateway cache TTL?"),
   - one-liners ("Ordered, replayable stream with multiple consumers → ?", "Header that gives temporary
     credentials to a container → ?").
2. Ask them in batches of 5, numbered. The learner answers all 5 in one message.
3. Correct briefly (one line each) and add the memory hook when there is one.
4. Log each answer with `uv run awslings record --topic <slug> --domain <n> --result correct|wrong --note "<fact>"`.
5. Missed facts go to the weak-spot queue in PROGRESS.md (+1/+3/+7 days).
Only use numbers you are sure of. Flag the values that changed after the exam guide
(SQS / Lambda async payload sizes, API Gateway timeout).
