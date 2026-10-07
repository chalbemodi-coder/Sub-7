"""Encryption helpers for storing a Telethon StringSession in MongoDB."""

from cryptography.fernet import Fernet, InvalidToken


class SessionStoreError(RuntimeError):
    """Raised when an encrypted Telegram session cannot be read or written."""


def _fernet(key: str) -> Fernet:
    if not key:
        raise SessionStoreError(
            "Set SESSION_ENCRYPTION_KEY before using Telegram login."
        )
    try:
        return Fernet(key.encode("ascii"))
    except (UnicodeEncodeError, TypeError, ValueError) as exc:
        raise SessionStoreError(
            "SESSION_ENCRYPTION_KEY is invalid; generate a Fernet key and keep it secret."
        ) from exc


def validate_key(key: str) -> None:
    """Validate the configured encryption key without touching session data."""
    _fernet(key)


def encrypt_session(session: str, key: str) -> str:
    """Return an encrypted Fernet token for a Telethon StringSession."""
    if not session:
        raise SessionStoreError("Refusing to encrypt an empty Telegram session.")
    return _fernet(key).encrypt(session.encode("utf-8")).decode("ascii")


def decrypt_session(token: str, key: str) -> str:
    """Decrypt a stored Fernet token back into a Telethon StringSession."""
    try:
        return _fernet(key).decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise SessionStoreError(
            "Stored Telegram session could not be decrypted; check SESSION_ENCRYPTION_KEY."
        ) from exc
    except (UnicodeEncodeError, UnicodeDecodeError, TypeError) as exc:
        raise SessionStoreError("Encrypted Telegram session data is invalid.") from exc
