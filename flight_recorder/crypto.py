"""Optional payload encryption: a storage-layer transform applied after hashing.

Sensitive prompts and tool responses can be encrypted at rest without
changing any replay semantics: hashes (and signatures) are computed over the
redacted *plaintext* exactly as before, then the ciphertext replaces
``payload`` and ``historical_response`` in the JSONL file only. Reading
decrypts back to plaintext before per-event validation, hash verification,
and replay matching — none of which know encryption exists.

This module imports without the ``cryptography`` package; only
:func:`load_fernet_cipher` needs it (``pip install flight-recorder[crypto]``).
Any object with ``encrypt(text) -> token`` / ``decrypt(token) -> text``
satisfies the :class:`Cipher` protocol, so custom KMS-backed ciphers plug in
the same way.

Key resolution mirrors signing: explicit argument, then the
``AGENT_RR_ENCRYPTION_KEY`` environment variable.

TODO: field-level selective encryption, key rotation, and encrypting
``error.message`` / ``error.traceback``.
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional, Protocol, Union

from .hashing import canonical_json

ENCRYPTED_MARKER = "__agent_rr_encrypted__"
ENCRYPTION_KEY_ENV_VAR = "AGENT_RR_ENCRYPTION_KEY"

# The fields encrypted at rest. Hashes/signature stay plaintext (they are
# one-way digests computed pre-encryption); error dicts are TODO (see above).
_ENCRYPTED_FIELDS = ("payload", "historical_response")


class Cipher(Protocol):
    """Anything that maps text to an opaque token string and back."""

    def encrypt(self, text: str) -> str: ...

    def decrypt(self, token: str) -> str: ...


def is_encrypted_value(value: Any) -> bool:
    """True when *value* is the stored form of an encrypted field."""
    return type(value) is dict and ENCRYPTED_MARKER in value


def is_encrypted_event_dict(data: Any) -> bool:
    """True when any encryptable field of a decoded event dict is ciphertext."""
    return type(data) is dict and any(
        is_encrypted_value(data.get(field)) for field in _ENCRYPTED_FIELDS
    )


def encrypt_event_fields(data: dict, cipher: Cipher) -> dict:
    """Return a copy of a JSON event dict with sensitive fields encrypted.

    The metadata event stays plaintext: it holds only recorder-generated
    versioning, and readers need it to identify the trace. ``None`` values
    stay ``None`` (encrypting the absence of a response leaks nothing and
    would break the null-field invariants).
    """
    if data.get("event_type") == "metadata":
        return data
    encrypted = dict(data)
    alg = getattr(cipher, "alg", type(cipher).__name__)
    for field in _ENCRYPTED_FIELDS:
        if encrypted.get(field) is None:
            continue
        token = cipher.encrypt(canonical_json(encrypted[field]))
        encrypted[field] = {ENCRYPTED_MARKER: {"alg": alg, "token": token}}
    return encrypted


def decrypt_event_fields(data: dict, cipher: Cipher) -> dict:
    """Return a copy of a JSON event dict with encrypted fields decrypted."""
    decrypted = dict(data)
    for field in _ENCRYPTED_FIELDS:
        value = decrypted.get(field)
        if not is_encrypted_value(value):
            continue
        token = value[ENCRYPTED_MARKER]["token"]
        decrypted[field] = json.loads(cipher.decrypt(token))
    return decrypted


class _FernetCipher:
    """Fernet (AES-128-CBC + HMAC) adapter satisfying the Cipher protocol."""

    alg = "fernet"

    def __init__(self, fernet: Any):
        self._fernet = fernet

    def encrypt(self, text: str) -> str:
        return self._fernet.encrypt(text.encode("utf-8")).decode("ascii")

    def decrypt(self, token: str) -> str:
        return self._fernet.decrypt(token.encode("ascii")).decode("utf-8")


def load_fernet_cipher(key: Union[bytes, str, None] = None) -> Optional[_FernetCipher]:
    """Build a Fernet cipher from *key* or ``AGENT_RR_ENCRYPTION_KEY``.

    Returns None when no key is configured. Requires the optional
    ``cryptography`` dependency (``pip install flight-recorder[crypto]``);
    generate a key with ``Fernet.generate_key()``.
    """
    if key is None:
        key = os.environ.get(ENCRYPTION_KEY_ENV_VAR) or None
        if key is None:
            return None
    try:
        from cryptography.fernet import Fernet
    except ImportError as exc:
        raise ImportError(
            "payload encryption needs the optional 'cryptography' dependency: "
            "pip install flight-recorder[crypto]"
        ) from exc
    if type(key) is str:
        key = key.encode("ascii")
    return _FernetCipher(Fernet(key))
