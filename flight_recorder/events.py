"""Trace event schema for the flight recorder (PLAN §1).

One :class:`TraceEvent` per JSONL line. Events form a causal DAG: an entry in
``parent_event_ids`` means this event consumed that parent's output, and the
list order is significant (it is preserved as given by the caller and pinned
into ``context_hash``).

This module validates *single-event* structure only. Trace-level invariants —
metadata first, monotonic sequence indices with no gaps, every parent having a
strictly lower ``call_sequence_index``, unique event ids, single ``run_id``
per file — live in ``dag.py``.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import asdict, dataclass, fields
from datetime import datetime
from typing import Any, Optional

from .hashing import validate_json_value

SCHEMA_VERSION = "1.0"
RECORDER_VERSION = "0.1.0"

EVENT_TYPE_METADATA = "metadata"
EVENT_TYPE_ROOT_INPUT = "root_input"
EVENT_TYPE_LLM_CALL = "llm_call"
EVENT_TYPE_TOOL_CALL = "tool_call"
EVENT_TYPE_FINAL_OUTPUT = "final_output"

EVENT_TYPES = (
    EVENT_TYPE_METADATA,
    EVENT_TYPE_ROOT_INPUT,
    EVENT_TYPE_LLM_CALL,
    EVENT_TYPE_TOOL_CALL,
    EVENT_TYPE_FINAL_OUTPUT,
)
BOUNDARY_EVENT_TYPES = (EVENT_TYPE_LLM_CALL, EVENT_TYPE_TOOL_CALL)

STATUS_OK = "ok"
STATUS_ERROR = "error"
STATUSES = (STATUS_OK, STATUS_ERROR)

METADATA_PAYLOAD_KEYS = frozenset(
    {"schema_version", "recorder_version", "trace_creation_time", "run_id", "agent_id"}
)
_ERROR_ALLOWED_KEYS = frozenset({"type", "message", "traceback"})
_HEX64_RE = re.compile(r"\A[0-9a-f]{64}\Z")


def _fail(message: str) -> None:
    raise ValueError(f"invalid event: {message}")


def _check_uuid_str(value: Any, field: str) -> None:
    if type(value) is not str:
        _fail(f"{field} must be a UUID string, got {type(value).__name__}")
    try:
        uuid.UUID(value)
    except ValueError:
        _fail(f"{field} is not a valid UUID: {value!r}")


def _check_iso8601(value: Any, field: str) -> None:
    if type(value) is not str or not value:
        _fail(f"{field} must be a non-empty ISO 8601 string")
    # Python 3.10's fromisoformat does not accept a trailing "Z".
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        datetime.fromisoformat(candidate)
    except ValueError:
        _fail(f"{field} is not ISO 8601: {value!r}")


@dataclass
class TraceEvent:
    """A single boundary event; field order matches the PLAN §1 schema.

    ``timestamp`` and ``latency_ms`` are informational only and never hashed;
    neither are ``event_id``, ``run_id`` or ``call_sequence_index``.
    """

    event_id: str
    run_id: str
    agent_id: str
    parent_event_ids: list[str]
    call_sequence_index: int
    event_type: str
    name: Optional[str]
    timestamp: str
    payload: Any
    historical_response: Any
    status: str
    error: Optional[dict]
    argument_hash: Optional[str]
    context_hash: Optional[str]
    latency_ms: Optional[int]

    def validate(self) -> None:
        """Raise ValueError unless this event satisfies every per-event invariant."""
        _check_uuid_str(self.event_id, "event_id")
        _check_uuid_str(self.run_id, "run_id")
        if type(self.agent_id) is not str or not self.agent_id:
            _fail("agent_id must be a non-empty string")
        if self.event_type not in EVENT_TYPES:
            _fail(f"event_type {self.event_type!r} is not one of {EVENT_TYPES}")
        if self.status not in STATUSES:
            _fail(f"status {self.status!r} is not one of {STATUSES}")

        is_metadata = self.event_type == EVENT_TYPE_METADATA
        is_boundary = self.event_type in BOUNDARY_EVENT_TYPES

        if type(self.call_sequence_index) is not int:
            _fail("call_sequence_index must be an int")
        if is_metadata and self.call_sequence_index != 0:
            _fail("metadata event must have call_sequence_index 0")
        if not is_metadata and self.call_sequence_index < 1:
            _fail(
                f"{self.event_type} event must have call_sequence_index >= 1 "
                "(0 is reserved for the metadata event)"
            )

        if type(self.parent_event_ids) is not list:
            _fail("parent_event_ids must be a list")
        for index, parent_id in enumerate(self.parent_event_ids):
            _check_uuid_str(parent_id, f"parent_event_ids[{index}]")
        if self.event_type in (EVENT_TYPE_METADATA, EVENT_TYPE_ROOT_INPUT) and self.parent_event_ids:
            _fail(f"{self.event_type} event must have empty parent_event_ids")

        if is_boundary:
            if type(self.name) is not str or not self.name:
                _fail(f"name is required (non-empty string) for {self.event_type} events")
        elif self.name is not None:
            _fail(f"name must be null for {self.event_type} events")

        _check_iso8601(self.timestamp, "timestamp")

        if not is_boundary and self.status != STATUS_OK:
            _fail(
                f"status must be 'ok' for {self.event_type} events "
                "(only boundary calls can record errors)"
            )
        if self.status == STATUS_OK:
            if self.error is not None:
                _fail("error must be null when status is 'ok'")
        else:
            self._validate_error_dict()

        try:
            validate_json_value(self.payload)
        except ValueError as exc:
            _fail(f"payload is not strict JSON: {exc}")
        if is_metadata:
            self._validate_metadata_payload()

        if is_boundary and self.status == STATUS_OK:
            if self.historical_response is None:
                _fail("historical_response is required for successful boundary calls")
            try:
                validate_json_value(self.historical_response)
            except ValueError as exc:
                _fail(f"historical_response is not strict JSON: {exc}")
        elif self.historical_response is not None:
            _fail(
                "historical_response must be null except on successful boundary calls "
                f"(event_type={self.event_type!r}, status={self.status!r})"
            )

        if is_metadata:
            if self.argument_hash is not None or self.context_hash is not None:
                _fail("argument_hash and context_hash must be null on the metadata event")
        else:
            for field_name, value in (
                ("argument_hash", self.argument_hash),
                ("context_hash", self.context_hash),
            ):
                if type(value) is not str or not _HEX64_RE.match(value):
                    _fail(
                        f"{field_name} must be a 64-char lowercase hex SHA-256 digest, "
                        f"got {value!r}"
                    )

        if self.latency_ms is not None and (type(self.latency_ms) is not int or self.latency_ms < 0):
            _fail(f"latency_ms must be null or a non-negative int, got {self.latency_ms!r}")

    def _validate_error_dict(self) -> None:
        if type(self.error) is not dict:
            _fail("error must be a dict when status is 'error'")
        unknown = set(self.error) - _ERROR_ALLOWED_KEYS
        if unknown:
            _fail(
                f"error has unsupported keys {sorted(map(repr, unknown))}; "
                "allowed: type, message, traceback"
            )
        for key in ("type", "message"):
            if key not in self.error or type(self.error[key]) is not str:
                _fail(f"error.{key} is required and must be a string")
        if not self.error["type"]:
            _fail("error.type must be a non-empty string")
        if "traceback" in self.error and type(self.error["traceback"]) is not str:
            _fail("error.traceback must be a string when present")

    def _validate_metadata_payload(self) -> None:
        payload = self.payload
        if type(payload) is not dict:
            _fail("metadata payload must be a dict")
        version = payload.get("schema_version")
        if version != SCHEMA_VERSION:
            _fail(
                f"unsupported schema_version {version!r}; "
                f"this recorder supports {SCHEMA_VERSION!r}"
            )
        keys = set(payload)
        if keys != METADATA_PAYLOAD_KEYS:
            missing = sorted(METADATA_PAYLOAD_KEYS - keys)
            extra = sorted(keys - METADATA_PAYLOAD_KEYS)
            _fail(f"metadata payload keys mismatch: missing {missing}, unexpected {extra}")
        for key in ("recorder_version", "trace_creation_time"):
            if type(payload[key]) is not str or not payload[key]:
                _fail(f"metadata payload {key} must be a non-empty string")
        if payload["run_id"] != self.run_id:
            _fail("metadata payload run_id must match the event's run_id")
        if payload["agent_id"] != self.agent_id:
            _fail("metadata payload agent_id must match the event's agent_id")

    def to_dict(self) -> dict:
        """Project to a plain dict (deep-copied) in schema field order."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Any) -> "TraceEvent":
        """Build and validate an event from a decoded JSONL object.

        Strict: every schema field must be present and no others.
        """
        if type(data) is not dict:
            _fail(f"event must be a JSON object, got {type(data).__name__}")
        missing = [name for name in EVENT_FIELDS if name not in data]
        if missing:
            _fail(f"missing fields: {', '.join(missing)}")
        unknown = [key for key in data if key not in _EVENT_FIELD_SET]
        if unknown:
            _fail(f"unknown fields: {', '.join(map(repr, unknown))}")
        event = cls(**{name: data[name] for name in EVENT_FIELDS})
        event.validate()
        return event


EVENT_FIELDS: tuple[str, ...] = tuple(f.name for f in fields(TraceEvent))
_EVENT_FIELD_SET = frozenset(EVENT_FIELDS)
