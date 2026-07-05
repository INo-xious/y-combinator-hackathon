"""Optional HMAC-SHA256 trace signing: tamper evidence for trace files.

``verify_hashes`` proves internal consistency but not authenticity — anyone
who edits a trace can recompute the SHA-256 hashes. Signing closes that gap:
with a secret key, every event gets a ``signature`` the editor cannot forge.

What one signature covers: the event's identity (``event_id``, ``run_id``,
``call_sequence_index``, ``event_type``) plus its ``argument_hash`` and
``context_hash``. The context hash already commits to the payload, response,
error, and the full causal ancestry, so a per-event signature is transitively
a signature over everything upstream of it; the identity fields block
reordering, cross-trace splicing, and replaying a signed event elsewhere.
The metadata event has null hashes, so its ``payload`` is signed directly.

Signatures are computed after hashing and are never hashed themselves.
Unsigned traces are unaffected: no key means no ``signature`` field and
byte-identical output to previous versions.

Key resolution order: explicit argument, then the ``AGENT_M2_SIGNING_KEY``
environment variable, then no signing at all.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from typing import TYPE_CHECKING, Optional, Union

from .hashing import canonical_json

if TYPE_CHECKING:
    from .events import TraceEvent

SIGNING_KEY_ENV_VAR = "AGENT_M2_SIGNING_KEY"


def resolve_signing_key(key: Union[bytes, str, None]) -> Optional[bytes]:
    """Resolve the HMAC key: explicit *key* wins, else the env var, else None."""
    if key is None:
        env_value = os.environ.get(SIGNING_KEY_ENV_VAR)
        if not env_value:
            return None
        return env_value.encode("utf-8")
    if type(key) is str:
        if not key:
            raise ValueError("signing key must be non-empty")
        return key.encode("utf-8")
    if type(key) in (bytes, bytearray):
        if not key:
            raise ValueError("signing key must be non-empty")
        return bytes(key)
    raise TypeError(f"signing key must be bytes or str, got {type(key).__name__}")


def _signed_projection(event: "TraceEvent") -> dict:
    projection = {
        "event_id": event.event_id,
        "run_id": event.run_id,
        "call_sequence_index": event.call_sequence_index,
        "event_type": event.event_type,
        "argument_hash": event.argument_hash,
        "context_hash": event.context_hash,
    }
    if event.argument_hash is None and event.context_hash is None:
        # Metadata event: no hashes commit to its payload, so sign it directly.
        projection["payload"] = event.payload
    return projection


def sign_event(event: "TraceEvent", key: bytes) -> str:
    """Return the HMAC-SHA256 hex signature of *event* under *key*."""
    message = canonical_json(_signed_projection(event)).encode("utf-8")
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def verify_signatures(
    events: list["TraceEvent"],
    key: bytes,
    *,
    require: bool = False,
) -> None:
    """Raise ValueError on any forged signature; on missing ones only if *require*.

    Unsigned events pass by default so pre-signing traces keep verifying;
    ``require=True`` rejects them (every event must carry a valid signature).
    """
    for event in events:
        if event.signature is None:
            if require:
                raise ValueError(
                    f"invalid trace: event {event.event_id} "
                    f"(sequence {event.call_sequence_index}) is unsigned but "
                    "signatures are required"
                )
            continue
        expected = sign_event(event, key)
        if not hmac.compare_digest(expected, event.signature):
            raise ValueError(
                f"invalid trace: event {event.event_id} "
                f"(sequence {event.call_sequence_index}) has a signature that "
                "does not verify — the trace was tampered with or signed with "
                "a different key"
            )
