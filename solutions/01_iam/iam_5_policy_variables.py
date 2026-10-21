"""
Exercise iam_5 — Policy variables: one policy for every user
============================================================
Book: chapter 2, "Policy variables" (book/src/ch02-iam.md)
Exam: Domain 2 · Task 2.1 (defining permissions for principals, least privilege)

Every employee gets a private "home folder" in the `corp-docs` bucket:
`home/<their IAM user name>/`. Instead of writing one policy per user, use
the policy variable `${aws:username}`. IAM replaces it at evaluation time.

Careful: the variable must reach IAM *literally* as `${aws:username}`.
Building the policy with a Python f-string silently breaks it (try it!).

Your task
---------
Fix HOME_FOLDER_POLICY so that it has two statements:
  * "ListOwnFolder": s3:ListBucket on the bucket, only for prefixes
    `home/${aws:username}/` and `home/${aws:username}/*`,
  * "ManageOwnFiles": s3:GetObject, s3:PutObject and s3:DeleteObject on
    the objects under `home/${aws:username}/`.
"""

BUCKET = "corp-docs"

HOME_FOLDER_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "ListOwnFolder",
            "Effect": "Allow",
            "Action": "s3:ListBucket",
            "Resource": f"arn:aws:s3:::{BUCKET}",
            "Condition": {"StringLike": {"s3:prefix": ["home/${aws:username}/", "home/${aws:username}/*"]}},
        },
        {
            "Sid": "ManageOwnFiles",
            "Effect": "Allow",
            "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
            "Resource": "arn:aws:s3:::" + BUCKET + "/home/${aws:username}/*",
        },
    ],
}


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run iam_5
# =============================================================================
import fnmatch  # noqa: E402
import json  # noqa: E402


def _by_sid(sid):
    return next(s for s in HOME_FOLDER_POLICY["Statement"] if s.get("Sid") == sid)


def _as_list(value):
    return value if isinstance(value, list) else [value]


def _resolve(value, username):
    return json.loads(json.dumps(value).replace("${aws:username}", username))


def test_variable_is_kept_literally():
    text = json.dumps(HOME_FOLDER_POLICY)
    assert "${aws:username}" in text, "the policy must contain the literal ${aws:username} variable"
    assert "BUG" not in text and "{'username'" not in text


def test_list_bucket_statement():
    s = _by_sid("ListOwnFolder")
    assert _as_list(s["Action"]) == ["s3:ListBucket"]
    assert _as_list(s["Resource"]) == ["arn:aws:s3:::corp-docs"], "ListBucket is a bucket-level action"
    prefixes = set(_as_list(s["Condition"]["StringLike"]["s3:prefix"]))
    assert prefixes == {"home/${aws:username}/", "home/${aws:username}/*"}


def test_object_statement():
    s = _by_sid("ManageOwnFiles")
    assert set(_as_list(s["Action"])) == {"s3:GetObject", "s3:PutObject", "s3:DeleteObject"}
    assert _as_list(s["Resource"]) == ["arn:aws:s3:::corp-docs/home/${aws:username}/*"]


def test_alice_cannot_reach_bob_files():
    resources = _as_list(_resolve(_by_sid("ManageOwnFiles"), "alice")["Resource"])
    assert any(fnmatch.fnmatchcase("arn:aws:s3:::corp-docs/home/alice/cv.pdf", r) for r in resources)
    assert not any(fnmatch.fnmatchcase("arn:aws:s3:::corp-docs/home/bob/cv.pdf", r) for r in resources)
