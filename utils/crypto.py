from __future__ import annotations

import hashlib
import hmac
import os
from typing import Tuple

from cryptography.fernet import Fernet


def get_encryption_key() -> bytes:
    """Get or derive encryption key from config."""
    from flask import current_app
    key = current_app.config.get("BACKUP_ENCRYPTION_KEY", "")
    if not key:
        # Derive from SECRET_KEY as fallback
        from flask import current_app
        import base64
        raw = hashlib.sha256(current_app.config["SECRET_KEY"].encode()).digest()
        return base64.urlsafe_b64encode(raw)
    return key.encode() if isinstance(key, str) else key


def encrypt_backup(plaintext_path: str, encrypted_path: str) -> str:
    """Encrypt a backup file. Returns the checksum."""
    key = get_encryption_key()
    f = Fernet(key)
    with open(plaintext_path, "rb") as fh:
        data = fh.read()
    encrypted = f.encrypt(data)
    with open(encrypted_path, "wb") as fh:
        fh.write(encrypted)
    checksum = hashlib.sha256(data).hexdigest()
    return checksum


def decrypt_backup(encrypted_path: str, plaintext_path: str) -> bool:
    """Decrypt a backup file. Returns True on success."""
    key = get_encryption_key()
    f = Fernet(key)
    with open(encrypted_path, "rb") as fh:
        encrypted = fh.read()
    decrypted = f.decrypt(encrypted)
    with open(plaintext_path, "wb") as fh:
        fh.write(decrypted)
    return True


def compute_checksum(filepath: str) -> str:
    """Compute SHA-256 checksum of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_checksum(filepath: str, expected: str) -> bool:
    """Verify file checksum matches expected value."""
    actual = compute_checksum(filepath)
    return hmac.compare_digest(actual, expected)


def is_password_breached(password: str) -> bool:
    """Check password against HaveIBeenPwned k-anonymity API.
    Returns True if password is found in breach database.
    """
    import urllib.request
    import urllib.error
    try:
        sha1 = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
        prefix, suffix = sha1[:5], sha1[5:]
        url = f"https://api.pwnedpasswords.com/range/{prefix}"
        req = urllib.request.Request(url, headers={"User-Agent": "AIM-System/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode("utf-8")
        for line in body.splitlines():
            hash_suffix, count = line.split(":")
            if hash_suffix.strip() == suffix and int(count) > 0:
                return True
        return False
    except Exception:
        # If API is unreachable, don't block user but log warning
        import logging
        logging.getLogger(__name__).warning("HaveIBeenPwned API unreachable, skipping breach check")
        return False
