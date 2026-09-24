from __future__ import annotations

import base64
import hashlib
import hmac
import time


COOKIE_NAME = "threads_radar_auth"
COOKIE_MAX_AGE_SECONDS = 30 * 24 * 60 * 60


def _secret(username: str, password: str) -> bytes:
    material = f"threads-product-radar:v1\0{username}\0{password}".encode("utf-8")
    return hashlib.sha256(material).digest()


def create_session_token(
    username: str,
    password: str,
    *,
    now: int | None = None,
    max_age_seconds: int = COOKIE_MAX_AGE_SECONDS,
) -> str:
    issued_at = int(time.time() if now is None else now)
    expires_at = issued_at + int(max_age_seconds)
    payload = f"{username}\n{expires_at}".encode("utf-8")
    signature = hmac.new(_secret(username, password), payload, hashlib.sha256).hexdigest()
    raw = payload + b"\n" + signature.encode("ascii")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def validate_session_token(
    token: str | None,
    username: str,
    password: str,
    *,
    now: int | None = None,
) -> bool:
    if not token or not username or not password:
        return False
    try:
        padded = token + "=" * (-len(token) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
        token_username, expires_raw, signature = raw.split("\n", 2)
        expires_at = int(expires_raw)
    except (ValueError, UnicodeDecodeError, base64.binascii.Error):
        return False

    if token_username != username:
        return False

    current = int(time.time() if now is None else now)
    if expires_at <= current:
        return False

    payload = f"{token_username}\n{expires_at}".encode("utf-8")
    expected = hmac.new(
        _secret(username, password), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)
