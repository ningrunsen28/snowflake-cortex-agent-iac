"""Snowflake key-pair JWT authentication for REST APIs."""

from __future__ import annotations

import hashlib
import time
from pathlib import Path

import jwt
from cryptography.hazmat.primitives import serialization


def _load_private_key(key_path: str) -> serialization.PrivateKeyTypes:
    p = Path(key_path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"Private key not found: {p}")
    with p.open("rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def _public_key_fingerprint(private_key: serialization.PrivateKeyTypes) -> str:
    """SHA-256 fingerprint of the DER-encoded public key, prefixed with SHA256:."""
    pub_der = private_key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    digest = hashlib.sha256(pub_der).digest()
    import base64

    return "SHA256:" + base64.b64encode(digest).decode("ascii")


def generate_jwt(
    account: str,
    user: str,
    private_key_path: str,
    lifetime_seconds: int = 3500,
) -> str:
    """Generate a JWT for Snowflake REST API key-pair auth.

    Args:
        account: Snowflake account identifier (e.g. "MYORG-MYACCOUNT").
        user: Snowflake username.
        private_key_path: Path to the PEM private key file.
        lifetime_seconds: Token validity in seconds (max 3600).
    """
    private_key = _load_private_key(private_key_path)
    fp = _public_key_fingerprint(private_key)

    account_upper = account.upper().replace(".", "-")
    user_upper = user.upper()

    now = int(time.time())
    payload = {
        "iss": f"{account_upper}.{user_upper}.{fp}",
        "sub": f"{account_upper}.{user_upper}",
        "iat": now,
        "exp": now + lifetime_seconds,
    }
    return jwt.encode(payload, private_key, algorithm="RS256")
