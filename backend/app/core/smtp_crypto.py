from __future__ import annotations

import base64
import hashlib
import logging
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

_PREFIX = 'fernet:'


def _cipher(key: str) -> Fernet:
    """Derive a Fernet cipher from an arbitrary string key via SHA-256."""
    key_bytes = hashlib.sha256(key.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def encrypt_smtp_password(plaintext: str, key: str) -> str:
    """Encrypt a plaintext SMTP password. Returns 'fernet:<ciphertext>'."""
    token = _cipher(key).encrypt(plaintext.encode()).decode()
    return f'{_PREFIX}{token}'


def decrypt_smtp_password(stored: str, key: str) -> str:
    """Decrypt a stored SMTP password.

    Handles both encrypted ('fernet:<token>') and legacy plaintext values so
    that existing rows continue to work after the key is first introduced.
    """
    if not stored.startswith(_PREFIX):
        return stored  # legacy plaintext passthrough
    token = stored[len(_PREFIX):]
    try:
        return _cipher(key).decrypt(token.encode()).decode()
    except InvalidToken:
        logger.error('Failed to decrypt SMTP password — invalid key or corrupted value')
        raise ValueError('Cannot decrypt SMTP password: invalid key or corrupted value')


def is_encrypted(stored: Optional[str]) -> bool:
    return bool(stored and stored.startswith(_PREFIX))
