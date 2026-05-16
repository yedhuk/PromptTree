from __future__ import annotations

import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_NONCE_SIZE = 12


def _key_bytes(key: str) -> bytes:
    return hashlib.sha256(key.encode()).digest()


def encrypt(plaintext: str, key: str) -> str:
    """AES-256-GCM encrypt. Returns base64(nonce || ciphertext)."""
    aes = AESGCM(_key_bytes(key))
    nonce = os.urandom(_NONCE_SIZE)
    ct = aes.encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ct).decode()


def decrypt(ciphertext: str, key: str) -> str:
    """AES-256-GCM decrypt from base64(nonce || ciphertext)."""
    aes = AESGCM(_key_bytes(key))
    raw = base64.b64decode(ciphertext)
    nonce, ct = raw[:_NONCE_SIZE], raw[_NONCE_SIZE:]
    return aes.decrypt(nonce, ct, None).decode()
