"""Encryption helpers for storing a Telethon StringSession in MongoDB."""

import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken


class SessionStoreError(RuntimeError):
    """Raised when an encrypted Telegram session cannot be read or written."""


DEFAULT_KEY_PATH = Path(".state/session-encryption.key")


def _fernet(key: str) -> Fernet:
    if not key:
        raise SessionStoreError("No session encryption key is available.")
    try:
        return Fernet(key.encode("ascii"))
    except (UnicodeEncodeError, TypeError, ValueError) as exc:
        raise SessionStoreError(
            "The session encryption key is invalid; restore its backup or set SESSION_ENCRYPTION_KEY."
        ) from exc


def validate_key(key: str) -> None:
    """Validate an explicitly configured Fernet key."""
    _fernet(key)


def _read_key_file(path: Path) -> str:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "r", encoding="ascii") as key_file:
        return key_file.read().strip()


def get_session_key(configured_key: str = "", create: bool = True, path=None) -> str:
    """Get a configured key or persist an auto-generated key in the Docker volume."""
    configured_key = (configured_key or "").strip()
    if configured_key:
        _fernet(configured_key)
        return configured_key

    key_path = Path(path) if path is not None else DEFAULT_KEY_PATH
    try:
        key_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            key = _read_key_file(key_path)
        except FileNotFoundError:
            if not create:
                raise SessionStoreError(
                    "The saved Telegram session key is missing. Restore the persistent .state volume "
                    "or set SESSION_ENCRYPTION_KEY to the original key."
                )
            generated_key = Fernet.generate_key().decode("ascii")
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
            try:
                descriptor = os.open(key_path, flags, 0o600)
            except FileExistsError:
                key = _read_key_file(key_path)
            else:
                with os.fdopen(descriptor, "w", encoding="ascii") as key_file:
                    key_file.write(generated_key + "\n")
                    key_file.flush()
                    os.fsync(key_file.fileno())
                key = generated_key
        os.chmod(key_path.parent, 0o700)
        os.chmod(key_path, 0o600)
        _fernet(key)
        return key
    except SessionStoreError:
        raise
    except (OSError, UnicodeError, TypeError) as exc:
        raise SessionStoreError(
            "Cannot read or create the session key in .state. Ensure the persistent Docker volume is mounted and writable."
        ) from exc


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
            "Stored Telegram session could not be decrypted; restore its original key or volume."
        ) from exc
    except (UnicodeEncodeError, UnicodeDecodeError, TypeError) as exc:
        raise SessionStoreError("Encrypted Telegram session data is invalid.") from exc
