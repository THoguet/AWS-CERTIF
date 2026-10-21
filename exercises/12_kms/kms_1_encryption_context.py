"""
Exercise kms_1 — KMS Encrypt/Decrypt and encryption context
===========================================================
Book: chapter 13, "AWS KMS" (book/src/ch13-kms-encryption.md)
Exam: Domain 2 · Task 2.2 (using encryption keys to encrypt or decrypt data)

KMS Encrypt/Decrypt work on SMALL payloads only: at most 4 KB of
plaintext. That fits secrets, tokens and identifiers, not files.

ENCRYPTION CONTEXT: a set of non-secret key/value pairs bound to the
ciphertext as additional authenticated data (AAD).
  * Decrypt fails (InvalidCiphertextException) unless you pass EXACTLY
    the same context,
  * it appears in CloudTrail logs (so never put secrets in it),
  * it can be required in key policies/grants (kms:EncryptionContext:*).
Using the customer id as context prevents someone from copying customer
A's ciphertext into customer B's record.

Your task
---------
  * `encrypt_ssn(kms, key_id, ssn, customer_id)` → ciphertext bytes,
  * `decrypt_ssn(kms, blob, customer_id)` → the SSN string.
Both must use {"customer_id": customer_id} as encryption context, and
encryption must refuse plaintexts larger than KMS_MAX_PLAINTEXT.
"""

# I AM NOT DONE

KMS_MAX_PLAINTEXT = 4096


def encrypt_ssn(kms, key_id: str, ssn: str, customer_id: str) -> bytes:
    data = ssn.encode()
    return kms.encrypt(KeyId=key_id, Plaintext=data)["CiphertextBlob"]  # TODO: size check + encryption context


def decrypt_ssn(kms, blob: bytes, customer_id: str) -> str:
    return kms.decrypt(CiphertextBlob=blob)["Plaintext"].decode()  # TODO: encryption context


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run kms_1
# =============================================================================
import boto3  # noqa: E402
import pytest  # noqa: E402
from botocore.exceptions import ClientError  # noqa: E402


@pytest.fixture
def kms(aws):
    client = boto3.client("kms")
    return client, client.create_key(Description="pii")["KeyMetadata"]["KeyId"]


def test_round_trip(kms):
    client, key_id = kms
    blob = encrypt_ssn(client, key_id, "1 85 05 78 006 084 36", "c-42")
    assert b"1 85 05" not in blob
    assert decrypt_ssn(client, blob, "c-42") == "1 85 05 78 006 084 36"


def test_ciphertext_is_bound_to_customer(kms):
    client, key_id = kms
    blob = encrypt_ssn(client, key_id, "123-45-6789", "c-42")
    with pytest.raises(ClientError) as error:
        decrypt_ssn(client, blob, "c-99")
    assert error.value.response["Error"]["Code"] == "InvalidCiphertextException"


def test_large_payloads_are_refused(kms):
    client, key_id = kms
    with pytest.raises(ValueError):
        encrypt_ssn(client, key_id, "x" * 5000, "c-42")
