# Question bank

Original, exam-style practice questions, one YAML file per book chapter. They power:

- `uv run awslings quiz [topics...]`: questions with immediate explanations,
- `uv run awslings mock`: 65-question timed mock exams weighted like DVA-C02 (32/26/24/18%),
- the tutor's `/quiz` and `/mock-exam` skills in Claude Code.

None of these are real exam questions. They were written to train the same skills: reading a
scenario, spotting the deciding keyword, and eliminating plausible distractors.

## Format

```yaml
chapter: ch05          # book chapter
topic: lambda          # topic slug used by `awslings quiz lambda`
questions:
  - id: lambda-001     # unique, <topic>-NNN
    domain: 1          # 1 Development · 2 Security · 3 Deployment · 4 Troubleshooting & Optimization
    task: "1.2"        # exam guide task statement
    difficulty: 2      # 1 easy · 2 exam level · 3 hard
    question: |
      A developer ... Which solution meets these requirements with the LEAST operational overhead?
    options:
      A: ...
      B: ...
      C: ...
      D: ...
    answer: [B]        # several letters = multiple response; the question must then say "(Choose TWO.)"
    explanation: |
      Why B is right, and why A, C and D are wrong.
    refs: [book/src/ch05-lambda.md]
```

Validate after editing: `uv run awslings validate`.

## History

Every answer (CLI or tutor) is appended to `progress/quiz-history.jsonl`. `awslings quiz` shows
unseen questions first, then the ones you got wrong. `awslings quiz --wrong` replays only your
mistakes. `awslings stats` summarizes accuracy by domain and topic.
