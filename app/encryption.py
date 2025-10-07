"""Utilities for encrypting and decrypting chat history."""

from __future__ import annotations

import base64
import hmac
import os
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Optional


KEY_SIZE = 64  # 32 bytes for keystream derivation, 32 bytes for authentication
NONCE_SIZE = 16
TAG_SIZE = 32  # sha256 digest size

_KEY_FILE = Path("data") / "chat_encryption.key"
_cipher: Optional["ChatCipher"] = None


class EncryptionError(Exception):
    """Raised when encrypted chat history cannot be decrypted."""


def _load_or_create_key() -> bytes:
    """Load the encryption key from disk, generating one if needed."""

    _KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    if _KEY_FILE.exists():
        key = _KEY_FILE.read_bytes()
        if len(key) == KEY_SIZE:
            return key

    key = os.urandom(KEY_SIZE)
    _KEY_FILE.write_bytes(key)
    return key


def _derive_keystream(enc_key: bytes, nonce: bytes, length: int) -> bytes:
    """Derive a keystream using HMAC-SHA256 in counter mode."""

    keystream = bytearray()
    counter = 0
    while len(keystream) < length:
        counter_bytes = counter.to_bytes(8, "big")
        block = hmac.new(enc_key, nonce + counter_bytes, sha256).digest()
        keystream.extend(block)
        counter += 1
    return bytes(keystream[:length])


@dataclass
class ChatCipher:
    """Symmetric stream cipher with authentication for chat history."""

    encryption_key: bytes
    authentication_key: bytes

    @classmethod
    def from_master_key(cls, key: bytes) -> "ChatCipher":
        if len(key) != KEY_SIZE:
            raise ValueError("Chat encryption key must be 64 bytes long.")
        return cls(key[: KEY_SIZE // 2], key[KEY_SIZE // 2 :])

    def encrypt(self, data: bytes) -> str:
        nonce = os.urandom(NONCE_SIZE)
        keystream = _derive_keystream(self.encryption_key, nonce, len(data))
        ciphertext = bytes(a ^ b for a, b in zip(data, keystream))
        tag = hmac.new(self.authentication_key, nonce + ciphertext, sha256).digest()
        return base64.urlsafe_b64encode(nonce + ciphertext + tag).decode("ascii")

    def decrypt(self, token: str) -> bytes:
        raw = base64.urlsafe_b64decode(token.encode("ascii"))
        if len(raw) < NONCE_SIZE + TAG_SIZE:
            raise EncryptionError("Ciphertext is too short to contain authentication data.")

        nonce = raw[:NONCE_SIZE]
        tag = raw[-TAG_SIZE:]
        ciphertext = raw[NONCE_SIZE:-TAG_SIZE]

        expected_tag = hmac.new(self.authentication_key, nonce + ciphertext, sha256).digest()
        if not hmac.compare_digest(tag, expected_tag):
            raise EncryptionError("Encrypted chat history failed authentication.")

        keystream = _derive_keystream(self.encryption_key, nonce, len(ciphertext))
        return bytes(a ^ b for a, b in zip(ciphertext, keystream))


def initialize_encryption() -> "ChatCipher":
    """Initialise the global cipher and ensure the key exists on disk."""

    global _cipher
    key = _load_or_create_key()
    _cipher = ChatCipher.from_master_key(key)
    return _cipher


def get_cipher() -> "ChatCipher":
    """Return the global cipher, initialising it on first use."""

    global _cipher
    if _cipher is None:
        return initialize_encryption()
    return _cipher


def get_key_path() -> Path:
    """Return the path where the chat encryption key is stored."""

    return _KEY_FILE

