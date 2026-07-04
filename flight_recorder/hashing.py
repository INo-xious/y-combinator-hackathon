"""Strict canonical JSON and SHA-256 hashing for trace events (PLAN §6).

Canonical form: ``json.dumps(obj, sort_keys=True, separators=(",", ":"),
ensure_ascii=False, allow_nan=False)`` hashed over its UTF-8 encoding.

Beyond what ``json.dumps`` enforces, validation rejects values that would
canonicalize surprisingly or non-deterministically:

- non-string dict keys — ``json.dumps`` silently stringifies them, so
  ``{1: "x"}`` and ``{"1": "x"}`` would collide,
- bytes / bytearray — no canonical JSON text form,
- NaN / Infinity — ``allow_nan=False`` would reject them anyway; we fail
  earlier with a clearer error,
- anything whose type is not *exactly* ``dict``, ``list``, ``str``,
  ``int``, ``float``, ``bool`` or ``None`` — tuples, sets, Decimals,
  datetimes, Enums and dict/str/int subclasses are all rejected rather
  than serialized through whatever ``json.dumps`` happens to do with them.

Floats are permitted but canonicalize via Python's ``repr``; prefer ints or
strings when exactness matters (stable within CPython 3.10+, not guaranteed
cross-language).

Hash semantics (``timestamp``, ``latency_ms``, ``event_id``, ``run_id`` and
``call_sequence_index`` are never hashed):

- ``argument_hash`` = SHA-256(canonical_json({event_type, name, payload}))
  with payload post-redaction; used for replay matching; null on metadata.
- ``context_hash`` = SHA-256(canonical_json({parent_context_hashes,
  event_type, name, payload, historical_response, status, error})) where
  ``parent_context_hashes`` lists the parents' context hashes in
  ``parent_event_ids`` order (order is part of the hash — pinned, not
  implementation-defined); null on metadata; ``[]`` on root_input.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any

_HEX64_RE = re.compile(r"\A[0-9a-f]{64}\Z")


def validate_json_value(obj: Any, path: str = "$") -> None:
    """Raise ValueError unless *obj* canonicalizes deterministically.

    ``path`` locates the offending value in error messages (``$.key[3]``).
    """
    obj_type = type(obj)
    if obj_type is dict:
        for key, value in obj.items():
            if type(key) is not str:
                raise ValueError(
                    f"non-string dict key {key!r} ({type(key).__name__}) at {path}: "
                    "json.dumps would silently stringify it"
                )
            validate_json_value(value, f"{path}.{key}")
    elif obj_type is list:
        for index, item in enumerate(obj):
            validate_json_value(item, f"{path}[{index}]")
    elif obj_type is float:
        if math.isnan(obj) or math.isinf(obj):
            raise ValueError(f"NaN and Infinity are not allowed at {path}")
    elif obj_type in (bytes, bytearray):
        raise ValueError(f"bytes are not allowed at {path}: no canonical JSON text form")
    elif obj_type in (str, int, bool, type(None)):
        pass
    else:
        raise ValueError(
            f"unsupported type {obj_type.__name__!r} at {path}: only exact "
            "dict/list/str/int/float/bool/None values canonicalize deterministically"
        )


def canonical_json(obj: Any) -> str:
    """Return the canonical JSON text of *obj*, validating strictness first."""
    validate_json_value(obj)
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha256_of_canonical(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def argument_hash(event_type: str, name: str | None, payload: Any) -> str:
    """Hash the request side of an event, for replay matching.

    ``payload`` must already be redacted — the raw value never touches a hash.
    Metadata events carry a null argument_hash, so hashing one is a bug.
    """
    if event_type == "metadata":
        raise ValueError("metadata events have no argument_hash (the field is null)")
    return _sha256_of_canonical({"event_type": event_type, "name": name, "payload": payload})


def context_hash(
    parent_context_hashes: list[str],
    event_type: str,
    name: str | None,
    payload: Any,
    historical_response: Any,
    status: str,
    error: dict | None,
) -> str:
    """Hash an event plus its causal ancestry.

    ``parent_context_hashes`` must be the parents' context hashes in
    ``parent_event_ids`` order; any upstream change ripples downstream.
    ``payload`` and ``historical_response`` must already be redacted.
    Metadata events carry a null context_hash, so hashing one is a bug.
    """
    if event_type == "metadata":
        raise ValueError("metadata events have no context_hash (the field is null)")
    if type(parent_context_hashes) is not list:
        raise ValueError("parent_context_hashes must be a list (in parent_event_ids order)")
    for index, parent_hash in enumerate(parent_context_hashes):
        if type(parent_hash) is not str or not _HEX64_RE.match(parent_hash):
            raise ValueError(
                f"parent_context_hashes[{index}] is not a 64-char lowercase hex "
                f"SHA-256 digest: {parent_hash!r}"
            )
    return _sha256_of_canonical(
        {
            "parent_context_hashes": parent_context_hashes,
            "event_type": event_type,
            "name": name,
            "payload": payload,
            "historical_response": historical_response,
            "status": status,
            "error": error,
        }
    )
