"""Print the header and claims of a JWT, without checking its signature (for learning only).

Usage: python3 scripts/decode_jwt.py "$ID_TOKEN"

Real code must verify the signature with the user pool's public keys (JWKS), and check exp, iss,
token_use and the audience/client id, for example with the aws-jwt-verify library.
"""

import base64
import json
import sys
from datetime import datetime, timezone


def b64url_decode(part: str) -> bytes:
    return base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))


def decode(token: str) -> tuple[dict, dict, bytes]:
    header, payload, signature = token.strip().split(".")
    return json.loads(b64url_decode(header)), json.loads(b64url_decode(payload)), b64url_decode(signature)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    header, claims, signature = decode(argv[1])
    print("header:", json.dumps(header, indent=2))
    print("claims:", json.dumps(claims, indent=2))
    for key in ("auth_time", "iat", "exp"):
        if key in claims:
            print(f"{key:>9}: {datetime.fromtimestamp(claims[key], tz=timezone.utc).isoformat()}")
    print(f"signature: {len(signature)} bytes ({header.get('alg')}), not verified by this script")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
