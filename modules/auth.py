"""Password hashing for authentication. Stdlib only (PBKDF2-HMAC-SHA256 with a random salt) --
no extra dependency, since bcrypt/passlib wheels are not reliably available on this Python version."""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets

_ALGORITHM = "pbkdf2_sha256"
_ITERATIONS = 600_000


def hash_password(password: str) -> str:
    """Hash a password for storage. Format: "algorithm$iterations$salt_hex$hash_hex"."""
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return f"{_ALGORITHM}${_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    """Check a password against a hash produced by hash_password(). The iteration count is read
    from the hash itself (not _ITERATIONS), so a hash made under an older, lower setting still
    verifies correctly after _ITERATIONS is raised. Never raises -- a malformed or unrecognised
    hash is treated as a non-match rather than an error."""
    try:
        algorithm, iterations, salt_hex, hash_hex = password_hash.split("$")
        if algorithm != _ALGORITHM:
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations))
        return hmac.compare_digest(digest.hex(), hash_hex)
    except (ValueError, AttributeError):
        return False


def generate_token() -> str:
    """A random session token (not a password hash -- nothing to verify, just an opaque id the
    sessions table maps back to a user)."""
    return secrets.token_urlsafe(32)
