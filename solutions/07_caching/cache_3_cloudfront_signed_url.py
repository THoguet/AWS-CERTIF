"""
Exercise cache_3 — CloudFront signed URLs
=========================================
Book: chapter 8, "CloudFront" (book/src/ch08-caching-databases-cdn.md)
Exam: Domain 2 · Task 2.1 (securing applications), Domain 1 · Task 1.3

Paying customers download videos through CloudFront. The S3 origin is
private (Origin Access Control). CloudFront only serves a file if the URL
carries a valid signature made with a private key whose public key is
registered in a trusted KEY GROUP.

  * signed URL     → one file (works for any client, including curl),
  * signed cookies → many files (e.g. every segment of an HLS stream),
  * canned policy  → only an expiry date (short URL with Expires=...),
  * custom policy  → expiry + optional start date + IP range (URL with Policy=...).
Not to be confused with S3 presigned URLs (s3_2), which are signed with
IAM credentials and go to S3 directly.

Your task
---------
  * `make_signer(key_pair_id, private_key_pem)`: a botocore CloudFrontSigner,
  * `signed_url(signer, url, expires_at)`: canned policy,
  * `signed_url_for_office(signer, url, expires_at, cidr)`: custom policy
    restricted to an IP range.
"""

from datetime import datetime

from botocore.signers import CloudFrontSigner
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


def make_signer(key_pair_id: str, private_key_pem: bytes) -> CloudFrontSigner:
    private_key = serialization.load_pem_private_key(private_key_pem, password=None)

    def rsa_signer(message: bytes) -> bytes:
        return private_key.sign(message, padding.PKCS1v15(), hashes.SHA1())  # noqa: S303 (required by CloudFront)

    return CloudFrontSigner(key_pair_id, rsa_signer)


def signed_url(signer: CloudFrontSigner, url: str, expires_at: datetime) -> str:
    return signer.generate_presigned_url(url, date_less_than=expires_at)


def signed_url_for_office(signer: CloudFrontSigner, url: str, expires_at: datetime, cidr: str) -> str:
    policy = signer.build_policy(url, expires_at, ip_address=cidr)
    return signer.generate_presigned_url(url, policy=policy)


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run cache_3
# =============================================================================
import base64  # noqa: E402
import json  # noqa: E402
from datetime import timezone  # noqa: E402
from urllib.parse import parse_qs, urlparse  # noqa: E402

import pytest  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import rsa  # noqa: E402

URL = "https://d111111abcdef8.cloudfront.net/videos/course-1.mp4"
EXPIRES = datetime(2030, 1, 1, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def keys():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    return key.public_key(), pem


def _cf_b64decode(value):
    return base64.b64decode(value.replace("-", "+").replace("_", "=").replace("~", "/"))


def test_canned_policy_url(keys):
    public_key, pem = keys
    signer = make_signer("K2JCJMDEHXQW5F", pem)
    query = parse_qs(urlparse(signed_url(signer, URL, EXPIRES)).query)
    assert query["Expires"] == [str(int(EXPIRES.timestamp()))]
    assert query["Key-Pair-Id"] == ["K2JCJMDEHXQW5F"]
    canned = signer.build_policy(URL, EXPIRES).encode()
    public_key.verify(_cf_b64decode(query["Signature"][0]), canned, padding.PKCS1v15(), hashes.SHA1())


def test_custom_policy_url(keys):
    _, pem = keys
    signer = make_signer("K2JCJMDEHXQW5F", pem)
    query = parse_qs(urlparse(signed_url_for_office(signer, URL, EXPIRES, "203.0.113.0/24")).query)
    assert "Expires" not in query and "Policy" in query
    policy = json.loads(_cf_b64decode(query["Policy"][0]))
    condition = policy["Statement"][0]["Condition"]
    assert condition["IpAddress"]["AWS:SourceIp"] == "203.0.113.0/24"
    assert condition["DateLessThan"]["AWS:EpochTime"] == int(EXPIRES.timestamp())
