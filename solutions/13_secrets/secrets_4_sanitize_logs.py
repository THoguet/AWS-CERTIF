"""
Exercise secrets_4 — Sanitize sensitive data before logging
===========================================================
Book: chapter 14, "Handling sensitive data" (book/src/ch14-secrets-config.md)
Exam: Domain 2 · Task 2.3 (data classification: PII/PHI, sanitizing sensitive data)

Logs end up in CloudWatch Logs, S3 exports, third-party tools... and are
read by many more people than your database. Never log secrets, tokens
or personal data in clear text. (CloudWatch Logs also offers data
protection policies that mask sensitive data at ingestion. Defense in
depth: do both.)

Your task
---------
Implement `sanitize(value)` returning a copy where:
  * values of dict keys containing password, secret, token, authorization
    or ssn (case-insensitive) are replaced by "***",
  * e-mail addresses keep only their domain: ada@example.com → ***@example.com,
  * AWS access key ids (AKIA... or ASIA... + 16 chars) become "AKIA****" / "ASIA****",
  * card numbers (13-16 digits, spaces/dashes allowed) become "****" + last 4 digits.
Lists, nested dicts and non-string values must be handled (numbers unchanged).
"""

import re

SENSITIVE_KEYS = ("password", "secret", "token", "authorization", "ssn")
EMAIL = re.compile(r"[\w.+-]+@([\w-]+\.[\w.-]+)")
ACCESS_KEY = re.compile(r"\b(AKIA|ASIA)[A-Z0-9]{16}\b")
CARD = re.compile(r"\b(?:\d[ -]?){12,15}\d\b")


def _mask_text(text: str) -> str:
    text = EMAIL.sub(r"***@\1", text)
    text = ACCESS_KEY.sub(lambda m: m.group(1) + "****", text)
    return CARD.sub(lambda m: "****" + re.sub(r"\D", "", m.group(0))[-4:], text)


def sanitize(value):
    if isinstance(value, dict):
        return {k: "***" if any(s in str(k).lower() for s in SENSITIVE_KEYS) else sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize(v) for v in value]
    if isinstance(value, str):
        return _mask_text(value)
    return value


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run secrets_4
# =============================================================================


def test_sensitive_keys():
    event = {"user": "ada", "Password": "hunter2", "headers": {"Authorization": "Bearer abc"}, "api_token": "t"}
    assert sanitize(event) == {"user": "ada", "Password": "***", "headers": {"Authorization": "***"}, "api_token": "***"}


def test_strings_are_masked():
    message = "user ada.lovelace@example.co.uk paid with 4111 1111 1111 1111 using key AKIAABCDEFGHIJKLMNOP"
    assert sanitize(message) == "user ***@example.co.uk paid with ****1111 using key AKIA****"


def test_nested_lists_and_numbers():
    payload = {"items": [{"email": "bob@example.com", "qty": 2}], "total": 19.99, "ok": True}
    assert sanitize(payload) == {"items": [{"email": "***@example.com", "qty": 2}], "total": 19.99, "ok": True}


def test_original_is_not_modified():
    event = {"password": "hunter2"}
    sanitize(event)
    assert event == {"password": "hunter2"}
