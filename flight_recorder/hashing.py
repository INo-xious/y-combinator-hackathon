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

Floats are permitted by default and canonicalize via Python's ``repr``
(shortest round-trip form — stable across platforms within CPython 3.10+,
not guaranteed cross-language). Callers who need cross-language exactness
can construct hash inputs with ``float_hex`` strings instead, or set
``float_policy="reject"`` to have any float raise at validation time.

Hash semantics (``timestamp``, ``latency_ms``, ``event_id``, ``run_id`` and
``call_sequence_index`` are never hashed):

- ``argument_hash`` = SHA-256(canonical_json({event_type, name, payload}))
  with payload post-redaction; used for replay matching; null on metadata.
- ``context_hash`` = SHA-256(canonical_json({parent_context_hashes,
  event_type, name, payload, historical_response, status, stable_error})) where
  ``parent_context_hashes`` lists the parents' context hashes in
  ``parent_event_ids`` order (order is part of the hash — pinned, not
  implementation-defined); ``stable_error`` excludes diagnostic tracebacks;
  null on metadata; ``[]`` on root_input.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any

_HEX64_RE = re.compile(r"\A[0-9a-f]{64}\Z")
ValidationCache = dict[int, Any]

FLOAT_POLICY_ALLOW = "allow"
FLOAT_POLICY_REJECT = "reject"
FLOAT_POLICIES = (FLOAT_POLICY_ALLOW, FLOAT_POLICY_REJECT)


def float_hex(value: float) -> str:
    """Return *value* as a bit-exact hex string (``float.hex()`` form).

    The escape hatch for cross-language float exactness: store
    ``float_hex(x)`` strings in payloads instead of raw floats, and recover
    them with ``float.fromhex``. Unlike decimal repr, the hex form encodes
    the IEEE 754 bits directly, so any language reads back the same double.
    """
    if type(value) is not float:
        raise TypeError(f"float_hex expects a float, got {type(value).__name__}")
    if math.isnan(value) or math.isinf(value):
        raise ValueError("NaN and Infinity have no canonical form")
    return value.hex()


def new_validation_cache() -> ValidationCache:
    """Return an event-local strict JSON validation cache."""
    return {}


def _check_float_policy(float_policy: str) -> None:
    if float_policy not in FLOAT_POLICIES:
        raise ValueError(
            f"float_policy must be one of {FLOAT_POLICIES}, got {float_policy!r}"
        )


def validate_json_value(
    obj: Any,
    path: str = "$",
    *,
    validation_cache: ValidationCache | None = None,
    float_policy: str = FLOAT_POLICY_ALLOW,
) -> None:
    """Raise ValueError unless *obj* canonicalizes deterministically.

    ``path`` locates the offending value in error messages (``$.key[3]``).
    Under ``float_policy="reject"`` any float raises — for callers who need
    cross-language hash exactness and store ``float_hex`` strings instead.
    """
    _check_float_policy(float_policy)
    if validation_cache is not None:
        obj_id = id(obj)
        if validation_cache.get(obj_id) is obj:
            return
    obj_type = type(obj)
    if obj_type is dict:
        for key, value in obj.items():
            if type(key) is not str:
                raise ValueError(
                    f"non-string dict key {key!r} ({type(key).__name__}) at {path}: "
                    "json.dumps would silently stringify it"
                )
            validate_json_value(
                value,
                f"{path}.{key}",
                validation_cache=validation_cache,
                float_policy=float_policy,
            )
    elif obj_type is list:
        for index, item in enumerate(obj):
            validate_json_value(
                item,
                f"{path}[{index}]",
                validation_cache=validation_cache,
                float_policy=float_policy,
            )
    elif obj_type is float:
        if math.isnan(obj) or math.isinf(obj):
            raise ValueError(f"NaN and Infinity are not allowed at {path}")
        if float_policy == FLOAT_POLICY_REJECT:
            raise ValueError(
                f"float {obj!r} at {path} rejected by float_policy='reject': "
                "store float_hex(value) strings for cross-language exactness"
            )
    elif obj_type in (bytes, bytearray):
        raise ValueError(f"bytes are not allowed at {path}: no canonical JSON text form")
    elif obj_type in (str, int, bool, type(None)):
        pass
    else:
        raise ValueError(
            f"unsupported type {obj_type.__name__!r} at {path}: only exact "
            "dict/list/str/int/float/bool/None values canonicalize deterministically"
        )
    if validation_cache is not None:
        validation_cache[id(obj)] = obj


def canonical_json(
    obj: Any,
    *,
    validation_cache: ValidationCache | None = None,
    float_policy: str = FLOAT_POLICY_ALLOW,
) -> str:
    """Return the canonical JSON text of *obj*, validating strictness first."""
    validate_json_value(obj, validation_cache=validation_cache, float_policy=float_policy)
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha256_of_canonical(
    obj: Any,
    *,
    validation_cache: ValidationCache | None = None,
    float_policy: str = FLOAT_POLICY_ALLOW,
) -> str:
    return hashlib.sha256(
        canonical_json(
            obj,
            validation_cache=validation_cache,
            float_policy=float_policy,
        ).encode("utf-8")
    ).hexdigest()


def argument_hash(
    event_type: str,
    name: str | None,
    payload: Any,
    *,
    validation_cache: ValidationCache | None = None,
    float_policy: str = FLOAT_POLICY_ALLOW,
) -> str:
    """Hash the request side of an event, for replay matching.

    ``payload`` must already be redacted — the raw value never touches a hash.
    Metadata events carry a null argument_hash, so hashing one is a bug.
    """
    if event_type == "metadata":
        raise ValueError("metadata events have no argument_hash (the field is null)")
    return _sha256_of_canonical(
        {"event_type": event_type, "name": name, "payload": payload},
        validation_cache=validation_cache,
        float_policy=float_policy,
    )


def stable_error_for_hash(
    error: dict | None,
    *,
    include_traceback: bool = False,
) -> dict | None:
    """Return the deterministic error payload used by ``context_hash``."""
    if error is None:
        return None
    if include_traceback:
        return error
    return {
        key: error[key]
        for key in ("type", "message")
        if key in error
    }


def context_hash(
    parent_context_hashes: list[str],
    event_type: str,
    name: str | None,
    payload: Any,
    historical_response: Any,
    status: str,
    error: dict | None,
    *,
    validation_cache: ValidationCache | None = None,
    include_error_traceback_for_legacy: bool = False,
    float_policy: str = FLOAT_POLICY_ALLOW,
) -> str:
    """Hash an event plus its causal ancestry.

    ``parent_context_hashes`` must be the parents' context hashes in
    ``parent_event_ids`` order; any upstream change ripples downstream.
    ``payload`` and ``historical_response`` must already be redacted.
    ``error.traceback`` is intentionally excluded from new hashes because it
    contains machine-local diagnostics such as absolute file paths. Metadata
    events carry a null context_hash, so hashing one is a bug.
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
            "error": stable_error_for_hash(
                error,
                include_traceback=include_error_traceback_for_legacy,
            ),
        },
        validation_cache=validation_cache,
        float_policy=float_policy,
    )
