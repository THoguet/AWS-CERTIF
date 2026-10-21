"""
Exercise kms_2 — Envelope encryption
====================================
Book: chapter 13, "Envelope encryption" (book/src/ch13-kms-encryption.md)
Exam: Domain 2 · Task 2.2 (client-side encryption, using encryption keys)

To encrypt a 10 MB file you cannot call KMS Encrypt (4 KB max), and
sending all your data to KMS would be slow anyway. Envelope encryption:

  1. GenerateDataKey → KMS returns a fresh data key twice: in PLAINTEXT
     and ENCRYPTED under your KMS key,
  2. encrypt the data LOCALLY with the plaintext data key (AES-256-GCM),
     then erase the plaintext key from memory,
  3. store the ENCRYPTED data key next to the ciphertext (the "envelope"),
  4. to decrypt: KMS Decrypt the data key, then decrypt the data locally.

The AWS Encryption SDK and S3 client-side encryption do this for you.
(GenerateDataKeyWithoutPlaintext is useful when the key will only be
used later, by another component.)

Your task
---------
  * `encrypt_document(kms, key_id, data)` → {"encrypted_key", "nonce", "ciphertext"},
  * `decrypt_document(kms, envelope)` → original bytes.
"""

# I AM NOT DONE

import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def encrypt_document(kms, key_id: str, data: bytes) -> dict:
    # TODO: KMS Encrypt cannot take more than 4 KB, use a data key instead
    return {"ciphertext": kms.encrypt(KeyId=key_id, Plaintext=data)["CiphertextBlob"]}


def decrypt_document(kms, envelope: dict) -> bytes:
    raise NotImplementedError  # TODO


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run kms_2
# =============================================================================
from unittest import mock  # noqa: E402

import boto3  # noqa: E402
import pytest  # noqa: E402


@pytest.fixture
def kms(aws):
    client = boto3.client("kms")
    return client, client.create_key(Description="documents")["KeyMetadata"]["KeyId"]


def test_round_trip_large_document(kms):
    client, key_id = kms
    document = os.urandom(1024 * 1024)
    envelope = encrypt_document(client, key_id, document)
    assert envelope["ciphertext"] != document
    assert decrypt_document(client, envelope) == document


def test_plaintext_key_is_not_stored(kms):
    client, key_id = kms
    real = client.generate_data_key
    seen = {}

    def spy(**kwargs):
        response = real(**kwargs)
        seen["plaintext"] = response["Plaintext"]
        return response

    with mock.patch.object(client, "generate_data_key", side_effect=spy):
        envelope = encrypt_document(client, key_id, b"secret plans")
    assert seen, "use generate_data_key"
    assert seen["plaintext"] not in envelope.values()
    assert set(envelope) == {"encrypted_key", "nonce", "ciphertext"}


def test_tampering_is_detected(kms):
    client, key_id = kms
    envelope = encrypt_document(client, key_id, b"pay 100 EUR")
    envelope["ciphertext"] = envelope["ciphertext"][:-1] + bytes([envelope["ciphertext"][-1] ^ 1])
    with pytest.raises(Exception):
        decrypt_document(client, envelope)
