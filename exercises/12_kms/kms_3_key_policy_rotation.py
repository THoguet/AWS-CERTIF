"""
Exercise kms_3 — Key policies, cross-account access and rotation
================================================================
Book: chapter 13, "Key policies" and "Key rotation" (book/src/ch13-kms-encryption.md)
Exam: Domain 2 · Task 2.2 (using encryption across account boundaries, enabling key rotation)

Every KMS key has exactly one KEY POLICY (a resource-based policy). Unlike
most resources, IAM policies alone are NOT enough: the key policy must
allow access, either directly or by trusting the account root, which
delegates to IAM policies.

Cross-account use (account B decrypting with a key of account A) needs BOTH:
  1. the key policy in A allows account B (or a role in B),
  2. an IAM policy in B allows that principal to use the key ARN.

Rotation: automatic rotation of a customer managed key creates new key
material (yearly by default, configurable from 90 to 2560 days) while
keeping the key id, so old ciphertexts still decrypt. AWS managed keys
(aws/s3, aws/lambda...) rotate yearly automatically. Imported key material
and asymmetric keys cannot rotate automatically (rotate manually by
creating a new key and moving the alias).

Your task
---------
  * `key_policy(account, admin_role_arn, partner_account)` with three
    statements: Sids "EnableRootPermissions", "KeyAdministrators"
    (kms:Create*, kms:Describe*, kms:Enable*, kms:List*, kms:Put*,
    kms:Update*, kms:Revoke*, kms:Disable*, kms:Get*, kms:Delete*,
    kms:ScheduleKeyDeletion, kms:CancelKeyDeletion) and
    "PartnerDecrypt" (kms:Decrypt, kms:DescribeKey),
  * `create_orders_key(kms, policy)`: create the key with this policy,
    enable rotation, create alias "alias/orders-data". Return the key id.
"""

# I AM NOT DONE

import json

ADMIN_ACTIONS = [
    "kms:Create*", "kms:Describe*", "kms:Enable*", "kms:List*", "kms:Put*", "kms:Update*",
    "kms:Revoke*", "kms:Disable*", "kms:Get*", "kms:Delete*", "kms:ScheduleKeyDeletion", "kms:CancelKeyDeletion",
]


def key_policy(account: str, admin_role_arn: str, partner_account: str) -> dict:
    # TODO: three statements
    raise NotImplementedError


def create_orders_key(kms, policy: dict) -> str:
    key_id = kms.create_key(Description="orders data")["KeyMetadata"]["KeyId"]  # TODO: policy, rotation, alias
    return key_id


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run kms_3
# =============================================================================
import boto3  # noqa: E402

ACCOUNT, PARTNER = "123456789012", "210987654321"
ADMIN = f"arn:aws:iam::{ACCOUNT}:role/security-admins"


def _by_sid(policy, sid):
    return next(s for s in policy["Statement"] if s.get("Sid") == sid)


def test_policy_statements():
    policy = key_policy(ACCOUNT, ADMIN, PARTNER)
    root = _by_sid(policy, "EnableRootPermissions")
    assert root["Principal"] == {"AWS": f"arn:aws:iam::{ACCOUNT}:root"} and root["Action"] in ("kms:*", ["kms:*"])
    admins = _by_sid(policy, "KeyAdministrators")
    assert admins["Principal"] == {"AWS": ADMIN}
    assert set(admins["Action"]) == set(ADMIN_ACTIONS)
    assert "kms:Decrypt" not in admins["Action"], "administrators manage the key, they do not use it"
    partner = _by_sid(policy, "PartnerDecrypt")
    assert partner["Principal"] == {"AWS": f"arn:aws:iam::{PARTNER}:root"}
    assert set(partner["Action"]) == {"kms:Decrypt", "kms:DescribeKey"}


def test_key_creation(aws):
    kms = boto3.client("kms")
    key_id = create_orders_key(kms, key_policy(ACCOUNT, ADMIN, PARTNER))
    stored = json.loads(kms.get_key_policy(KeyId=key_id, PolicyName="default")["Policy"])
    assert _by_sid(stored, "PartnerDecrypt")["Principal"] == {"AWS": f"arn:aws:iam::{PARTNER}:root"}
    assert kms.get_key_rotation_status(KeyId=key_id)["KeyRotationEnabled"] is True
    aliases = {a["AliasName"]: a.get("TargetKeyId") for a in kms.list_aliases()["Aliases"]}
    assert aliases.get("alias/orders-data") == key_id
