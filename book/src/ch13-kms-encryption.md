# KMS and encryption

> **In this chapter**
> - Encryption at rest vs in transit, client-side vs server-side
> - AWS KMS: key types, key policies, grants, the Encrypt/Decrypt/GenerateDataKey APIs, limits
> - Envelope encryption and encryption context
> - Key rotation, multi-Region keys, cross-account use, KMS quotas
> - Certificates: ACM and AWS Private CA; SSH keys and certificates for development; CloudHSM
>
> **Exam weight**: Domain 2 Task 2.2 · **Exercises**: `kms_1`–`kms_3`, `s3_4`
> · **Quiz**: `uv run awslings quiz kms`

## Vocabulary

- **Encryption at rest**: data stored on disk is encrypted (S3, EBS, RDS, DynamoDB, SQS...). On AWS this is
  usually a checkbox backed by KMS.
- **Encryption in transit**: data on the network is encrypted (TLS/HTTPS). AWS endpoints use TLS. Enforce it
  with policies (`aws:SecureTransport`) and HTTPS listeners.
- **Server-side encryption (SSE)**: the service encrypts data after receiving it and decrypts it when
  you read it. Transparent to the client.
- **Client-side encryption**: your application encrypts before sending. AWS only ever stores ciphertext
  (AWS Encryption SDK, S3 encryption client, DynamoDB Encryption Client / Database Encryption SDK).

> **Exam tip** — "Data must be encrypted **before** it leaves the application / AWS must never see
> plaintext" → **client-side encryption** (with KMS data keys). "Encrypted at rest with an auditable
> key we control" → **SSE-KMS with a customer managed key**.

## AWS KMS keys

| Key type | Created and managed by | Key policy | Rotation | Cost |
|---|---|---|---|---|
| **AWS owned keys** | AWS, used across many accounts | Not visible | AWS | Free |
| **AWS managed keys** (`aws/s3`, `aws/lambda`, `aws/dynamodb`...) | AWS, in **your** account, for one service | **Cannot be edited** | Automatic, yearly | No monthly fee (usage billed) |
| **Customer managed keys (CMK)** | **You** | **You control it** (cross-account, grants, conditions) | Optional automatic rotation (default yearly, configurable **90–2,560 days**), on-demand rotation | ~$1/month per key + API calls |

- **Symmetric** keys (AES-256, the default): the key material never leaves KMS. Used for Encrypt/Decrypt/GenerateDataKey.
- **Asymmetric** keys (RSA, ECC): sign/verify, or encrypt with the public key outside AWS. **HMAC** keys: generate/verify MACs.
- **Aliases** (`alias/orders-data`) are friendly names you can repoint, which is how manual rotation works.
- Key material origin: KMS (default), **imported** (BYOK, you manage expiry, no automatic rotation),
  **CloudHSM custom key store**, external key store.
- Deleting a key requires a **waiting period of 7–30 days** (default 30). Data encrypted under it becomes
  unrecoverable after deletion, so prefer **disabling** first.

> **Exam tip** — "Need to control the key policy / share across accounts / audit and disable the key"
> → **customer managed key**. AWS managed keys cannot be used cross-account and their policies cannot change.

## Key policies and grants

Every KMS key has exactly **one key policy** (resource-based). **No principal can use a key unless
the key policy allows it**: directly, or by allowing the account root, which **delegates to IAM
policies**:

```json
{"Sid": "EnableIAMPolicies", "Effect": "Allow",
 "Principal": {"AWS": "arn:aws:iam::123456789012:root"}, "Action": "kms:*", "Resource": "*"}
```

- Separate **key administrators** (`kms:Create*`, `Put*`, `Enable*`, `Disable*`, `ScheduleKeyDeletion`...)
  from **key users** (`kms:Encrypt`, `Decrypt`, `GenerateDataKey*`, `ReEncrypt*`, `DescribeKey`) (exercise `kms_3`).
- **Grants**: temporary, programmatic delegations of key use (AWS services such as EBS and RDS create them for you).
- Useful condition keys: `kms:ViaService` (only through a given service, e.g. `s3.eu-west-3.amazonaws.com`),
  `kms:EncryptionContext:*`, `kms:CallerAccount`.
- **Cross-account**: (1) the key policy in account A allows account B (or a role in B), **and** (2) an IAM
  policy in account B allows the principal to use the key ARN.

> **Trap** — "The role has `kms:Decrypt` in its IAM policy but still gets AccessDenied" → the **key policy**
> does not allow the account/role (or the call comes from another account without both sides allowing it).

## The cryptographic APIs

| API | Does | Limit |
|---|---|---|
| `Encrypt` | Encrypts plaintext with the KMS key | Plaintext ≤ **4 KB** |
| `Decrypt` | Decrypts (the key id is embedded in symmetric ciphertext, no need to pass it) | — |
| `ReEncrypt` | Decrypt + encrypt under another key, server-side (plaintext never exposed) | — |
| `GenerateDataKey` | Returns a data key **in plaintext and encrypted** under the KMS key | Key spec AES_128/AES_256 |
| `GenerateDataKeyWithoutPlaintext` | Returns only the encrypted data key (for later use by another component) | — |
| `GenerateRandom` | Cryptographically secure random bytes | — |
| `Sign` / `Verify` | Asymmetric signatures | — |

## Envelope encryption

To encrypt anything larger than 4 KB (files, payloads), or to avoid sending your data to KMS:

```text
ENCRYPT                                              DECRYPT
1. GenerateDataKey(KeyId) → plaintext key + encrypted key    1. Decrypt(encrypted key) → plaintext key
2. AES-GCM encrypt the data locally with the plaintext key  2. AES-GCM decrypt the data locally
3. Erase the plaintext key from memory                      3. Erase the plaintext key
4. Store ciphertext + encrypted key (+ nonce) together
```

This is what S3 (SSE-KMS), EBS, the AWS Encryption SDK and most services do internally (exercise `kms_2`).
The **AWS Encryption SDK** implements envelope encryption, a standard message format, and
**data key caching** (fewer KMS calls → lower cost and less throttling).

> **Exam tip** — "Encrypt a 5 MB file with KMS" → **`GenerateDataKey`** and local encryption
> (envelope encryption), NOT `Encrypt`.

## Encryption context

Non-secret key/value pairs passed to Encrypt/GenerateDataKey and **required again to decrypt**:

```python
blob = kms.encrypt(KeyId=key, Plaintext=ssn, EncryptionContext={"customer_id": "c-42"})["CiphertextBlob"]
kms.decrypt(CiphertextBlob=blob, EncryptionContext={"customer_id": "c-42"})     # other context → InvalidCiphertextException
```

- It is **additional authenticated data (AAD)**: it binds the ciphertext to its context (it prevents copying
  customer A's encrypted value into customer B's record).
- It appears **in plaintext in CloudTrail**: great for auditing, but never put secrets in it.
- Key policies can require it (`kms:EncryptionContext:customer_id`) (exercise `kms_1`).

## Rotation, quotas, multi-Region keys

- **Automatic rotation** (customer managed symmetric keys): new key material on schedule. The key id/ARN stays the
  same, and old ciphertexts still decrypt (KMS keeps old material). Nothing changes for applications.
- **Manual rotation**: create a new key and repoint the alias. Use it for imported material, asymmetric
  keys, or immediate rotation needs. Old data needs the old key (or re-encryption).
- **KMS request quotas**: cryptographic operations are throttled per account and Region (shared quotas, thousands
  of requests per second depending on the Region and operation). Symptoms: `ThrottlingException` on S3
  SSE-KMS uploads or Lambda decrypts. Fixes: **S3 Bucket Keys**, **data key caching**, backoff and retries, a quota increase.
- **Multi-Region keys**: related keys with the same key id and material in several Regions. Encrypt in one Region,
  decrypt in another (global tables, DR) without cross-Region calls.

## Certificates and keys for developers

- **AWS Certificate Manager (ACM)**: **free public TLS certificates** with **automatic renewal**,
  validated by DNS (recommended) or email. Deployed to **ELB, CloudFront, API Gateway, App Runner**
  (you cannot download the private key of a public ACM certificate to install on EC2).
  CloudFront and edge-optimized API Gateway require certificates in **us-east-1**. You can also import third-party certificates (no auto-renewal).
- **AWS Private CA**: your own private certificate authority, for internal TLS, **mutual TLS**, IoT and service mesh
  certificates (paid). ACM can issue and renew private certificates from it.
- **SSH keys for development**: EC2 key pairs (create or import a public key), and **EC2 Instance Connect** /
  **Systems Manager Session Manager** to avoid managing SSH keys and open ports at all. For local TLS testing,
  self-signed certificates (`openssl req -x509 ...`) or a private CA.
- **CloudHSM**: dedicated single-tenant HSMs (FIPS 140-3 level 3) when you must fully control the HSM. KMS
  is the managed default.

## Encryption across services (cheat list)

| Service | At rest | Notes |
|---|---|---|
| S3 | SSE-S3 by default, SSE-KMS, DSSE-KMS, SSE-C | Bucket Keys for SSE-KMS, policies to force encryption |
| DynamoDB | Always on (owned / AWS managed / CMK) | — |
| Lambda environment variables | KMS (AWS managed or CMK) | Encryption helpers for in-transit encryption of sensitive values |
| SQS / SNS | SSE (SQS-managed or KMS) | The KMS key policy must allow publishers (e.g. S3 → SNS) |
| EBS / RDS | KMS, chosen at creation | Encrypt an existing DB: snapshot → encrypted copy → restore |
| Secrets Manager / Parameter Store SecureString | KMS | Reading requires `kms:Decrypt` on the key |
| CloudWatch Logs | KMS (associate a key with the log group) | — |

## Hands-on

| Exercise | Skill |
|---|---|
| `kms_1` | Encrypt/Decrypt with an encryption context, the 4 KB limit |
| `kms_2` | Envelope encryption with GenerateDataKey + AES-GCM |
| `kms_3` | Key policy (admins vs users vs partner account), rotation, alias |
| `s3_4` | SSE-KMS on S3 and Bucket Keys |

## Summary

- At rest vs in transit. SSE (the service encrypts) vs client-side (you encrypt before sending).
- AWS owned / AWS managed (fixed policy, yearly rotation) / customer managed (your policy, optional rotation, cross-account).
- The key policy is mandatory. The root statement delegates to IAM. Cross-account = key policy + IAM policy.
- `Encrypt` ≤ 4 KB. Use `GenerateDataKey` + local AES for anything larger (envelope encryption).
- Encryption context = AAD, logged in CloudTrail, required to decrypt.
- ACM = free public certificates with auto-renewal for ELB/CloudFront/API Gateway (us-east-1 for CloudFront).

## Check yourself

1. Why can't you call `kms:Encrypt` on a 10 MB file, and what do you do instead?
2. A Lambda function in account B must decrypt data encrypted with a CMK in account A. What two things are needed?
3. What happens to existing ciphertexts when automatic key rotation runs?
4. How do you prevent a ciphertext from being decrypted in the wrong tenant's context?
5. Uploads to an SSE-KMS bucket fail with throttling at high volume. Two fixes?

<details><summary>Answers</summary>

1. `Encrypt` accepts at most 4 KB. Use envelope encryption: `GenerateDataKey`, encrypt locally, store the encrypted data key.
2. The key policy in A must allow account B (or the function's role). The function's execution role in B must allow `kms:Decrypt` on the key ARN.
3. Nothing. KMS keeps previous key material, so old ciphertexts still decrypt. New encryptions use the new material.
4. Use an **encryption context** (e.g. `tenant_id`) at encryption. Decryption then requires the same context.
5. Enable **S3 Bucket Keys**, and request a KMS quota increase (plus SDK retries with backoff).

</details>

## Further reading

- [AWS KMS concepts](https://docs.aws.amazon.com/kms/latest/developerguide/concepts.html) and [KMS FAQ](https://aws.amazon.com/kms/faqs/)
- [Key policies in AWS KMS](https://docs.aws.amazon.com/kms/latest/developerguide/key-policies.html)
- [Envelope encryption](https://docs.aws.amazon.com/kms/latest/developerguide/kms-cryptography.html#enveloping)
- [AWS Encryption SDK](https://docs.aws.amazon.com/encryption-sdk/latest/developer-guide/introduction.html)
- [AWS Certificate Manager](https://docs.aws.amazon.com/acm/latest/userguide/acm-overview.html)
