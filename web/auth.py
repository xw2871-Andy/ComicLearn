"""Lightweight password + session auth (stdlib only).

We use PBKDF2-HMAC-SHA256 with a per-user salt so we don't take a dependency
on bcrypt/passlib. Sessions are random 24-byte tokens stored in SQLite and
exposed to the browser via an httpOnly cookie.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from typing import Tuple

from . import db

PBKDF2_ITERATIONS = 200_000
SESSION_COOKIE = "c2c_sess"
SESSION_TTL_SECONDS = 60 * 60 * 24 * 30  # 30 days

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ----- Password hashing ------------------------------------------------------ #


def hash_password(password: str) -> Tuple[str, str]:
    """Return (salt_hex, hash_hex) for a fresh password."""

    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS, dklen=32
    )
    return salt.hex(), digest.hex()


def verify_password(password: str, salt_hex: str, hash_hex: str) -> bool:
    try:
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256", (password or "").encode("utf-8"), salt, PBKDF2_ITERATIONS, dklen=32
    )
    return hmac.compare_digest(digest, expected)


def is_valid_email(email: str) -> bool:
    return bool(email) and bool(_EMAIL_RE.match(email.strip()))


# ----- High-level signup / login -------------------------------------------- #


class AuthError(Exception):
    pass


def signup(email: str, display_name: str, password: str) -> Tuple[int, str]:
    """Create a user + first session token. Returns (user_id, session_token)."""

    email = (email or "").strip().lower()
    display_name = (display_name or "").strip() or email.split("@", 1)[0]
    if not is_valid_email(email):
        raise AuthError("Please provide a valid email address.")
    if db.get_user_by_email(email) is not None:
        raise AuthError("An account with this email already exists.")
    try:
        salt, h = hash_password(password)
    except ValueError as exc:
        raise AuthError(str(exc)) from exc
    uid = db.create_user(email, display_name, salt, h)
    token = db.create_session(uid, ttl_seconds=SESSION_TTL_SECONDS)
    return uid, token


def login(email: str, password: str) -> Tuple[int, str]:
    """Verify creds and return (user_id, fresh_session_token)."""

    email = (email or "").strip().lower()
    user = db.get_user_by_email(email)
    if not user or not verify_password(password, user["pwd_salt"], user["pwd_hash"]):
        raise AuthError("Email or password is incorrect.")
    token = db.create_session(user["id"], ttl_seconds=SESSION_TTL_SECONDS)
    return int(user["id"]), token


def resolve_session(token: str | None) -> dict | None:
    """Return the user record for a session token, or None."""

    if not token:
        return None
    sess = db.get_session(token)
    if not sess:
        return None
    return db.get_user(int(sess["user_id"]))


def logout(token: str | None) -> None:
    if token:
        db.delete_session(token)
