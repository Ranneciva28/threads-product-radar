from __future__ import annotations

import base64
import hashlib
import hmac
import time


COOKIE_NAME = "threads_radar_auth"
COOKIE_MAX_AGE_SECONDS = 30 * 24 * 60 * 60


def _signing_key(secret: str) -> bytes:
    if not secret:
        raise ValueError("Session signing secret tidak boleh kosong.")
    return hashlib.sha256(
        ("threads-product-radar:session:v2\0" + secret).encode("utf-8")
    ).digest()


def create_session_token(
    username: str,
    secret: str,
    *,
    now: int | None = None,
    max_age_seconds: int = COOKIE_MAX_AGE_SECONDS,
) -> str:
    issued_at = int(time.time() if now is None else now)
    expires_at = issued_at + int(max_age_seconds)
    payload = (username + "\n" + str(expires_at)).encode("utf-8")
    signature = hmac.new(_signing_key(secret), payload, hashlib.sha256).hexdigest()
    raw = payload + b"\n" + signature.encode("ascii")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def get_session_username(
    token: str | None,
    secret: str,
    *,
    now: int | None = None,
) -> str | None:
    if not token or not secret:
        return None
    try:
        padded = token + "=" * (-len(token) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
        token_username, expires_raw, signature = raw.split("\n", 2)
        expires_at = int(expires_raw)
    except (ValueError, UnicodeDecodeError, base64.binascii.Error):
        return None

    current = int(time.time() if now is None else now)
    if expires_at <= current:
        return None

    payload = (token_username + "\n" + str(expires_at)).encode("utf-8")
    expected = hmac.new(
        _signing_key(secret), payload, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    return token_username


def validate_session_token(
    token: str | None,
    username: str,
    secret: str,
    *,
    now: int | None = None,
) -> bool:
    return get_session_username(token, secret, now=now) == username
