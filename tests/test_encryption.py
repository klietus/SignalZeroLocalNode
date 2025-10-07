import base64

import pytest

from app import encryption


@pytest.fixture(autouse=True)
def reset_cipher(monkeypatch):
    """Ensure each test starts with a clean encryption module state."""

    monkeypatch.setattr(encryption, "_cipher", None)


def _deterministic_bytes(length: int) -> bytes:
    return bytes((i % 256 for i in range(length)))


def test_initialize_encryption_creates_key_file(monkeypatch, tmp_path):
    key_path = tmp_path / "chat.key"
    monkeypatch.setattr(encryption, "_KEY_FILE", key_path)
    monkeypatch.setattr(encryption.os, "urandom", _deterministic_bytes)

    cipher = encryption.initialize_encryption()

    assert key_path.exists(), "encryption key should be created on disk"
    assert key_path.read_bytes() == _deterministic_bytes(encryption.KEY_SIZE)
    assert isinstance(cipher, encryption.ChatCipher)
    assert encryption.get_cipher() is cipher, "initialize_encryption should set the global cipher"


def test_chat_cipher_encrypt_decrypt_roundtrip(monkeypatch, tmp_path):
    key_path = tmp_path / "chat.key"
    monkeypatch.setattr(encryption, "_KEY_FILE", key_path)
    key_bytes = _deterministic_bytes(encryption.KEY_SIZE)
    key_path.write_bytes(key_bytes)

    cipher = encryption.initialize_encryption()

    nonce = b"\xAA" * encryption.NONCE_SIZE
    monkeypatch.setattr(encryption.os, "urandom", lambda size: nonce)

    message = b"secret history"
    token = cipher.encrypt(message)

    assert cipher.decrypt(token) == message

    decoded = bytearray(base64.urlsafe_b64decode(token.encode("ascii")))
    decoded[-1] ^= 0x01
    tampered_token = base64.urlsafe_b64encode(bytes(decoded)).decode("ascii")

    with pytest.raises(encryption.EncryptionError):
        cipher.decrypt(tampered_token)


def test_chat_cipher_key_length_validation():
    with pytest.raises(ValueError):
        encryption.ChatCipher.from_master_key(b"short")
