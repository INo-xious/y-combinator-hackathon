"""Trace-level DAG and lifecycle invariant validation (PLAN §1).

Cycles are structurally impossible by construction: every
``parent_event_id`` must reference an event with a *strictly lower*
``call_sequence_index`` in the same ``run_id``, so every edge points
backwards in sequence order and no separate cycle-detection pass is needed.

Per-event schema checks live on ``TraceEvent.validate`` (events.py); this
module checks the cross-event invariants:

- the first event is the metadata event (per-event validation already pins
  metadata to sequence 0 and everything else to >= 1, so there can only be
  one and it can only be first),
- ``call_sequence_index`` is monotonic from 0 with no gaps,
- event ids are unique; all events share one ``run_id`` and one ``agent_id``,
- every parent exists, has a strictly lower sequence index, and is not the
  metadata event (metadata produces no output and has no ``context_hash``
  to chain from),
- root_input immediately follows metadata — hence precedes every boundary
  call — and appears at most once; final_output appears at most once, only
  as the last event.

Every prefix of a valid trace is itself structurally valid; that is what
lets crash-truncated traces validate line-by-line. Pass
``require_complete=True`` to additionally demand that the root_input and
final_output events are present (CLI ``validate`` semantics).
"""

from __future__ import annotations

from typing import Iterable

from .events import (
    EVENT_TYPE_FINAL_OUTPUT,
    EVENT_TYPE_METADATA,
    EVENT_TYPE_ROOT_INPUT,
    TraceEvent,
)
from .hashing import argument_hash, context_hash


def _fail(message: str) -> None:
    raise ValueError(f"invalid trace: {message}")


def validate_trace(events: Iterable[TraceEvent], *, require_complete: bool = False) -> None:
    """Raise ValueError unless *events* satisfy every trace-level invariant.

    Hashes are format-checked only; use :func:`verify_hashes` to recompute
    and compare them.
    """
    events = list(events)
    if not events:
        _fail("empty trace (the metadata event is required)")

    by_id: dict[str, TraceEvent] = {}
    for position, event in enumerate(events):
        try:
            event.validate()
        except ValueError as exc:
            _fail(f"event at position {position}: {exc}")
        if event.call_sequence_index != position:
            _fail(
                "call_sequence_index must be monotonic from 0 with no gaps: "
                f"event at position {position} has index {event.call_sequence_index}"
            )
        if event.event_id in by_id:
            _fail(f"duplicate event_id {event.event_id}")
        by_id[event.event_id] = event

    metadata = events[0]
    if metadata.event_type != EVENT_TYPE_METADATA:
        _fail(f"first event must be metadata, got {metadata.event_type!r}")
    for event in events[1:]:
        if event.run_id != metadata.run_id:
            _fail(
                f"mixed run_ids: event {event.event_id} has run_id {event.run_id}, "
                f"expected {metadata.run_id} (one trace file per run)"
            )
        if event.agent_id != metadata.agent_id:
            _fail(
                f"mixed agent_ids: event {event.event_id} has agent_id "
                f"{event.agent_id!r}, expected {metadata.agent_id!r}"
            )

    # DAG invariant: edges always point strictly backwards in sequence order,
    # which is what makes cycles structurally impossible (module docstring).
    for event in events:
        for parent_id in event.parent_event_ids:
            parent = by_id.get(parent_id)
            if parent is None:
                _fail(f"event {event.event_id} references unknown parent {parent_id}")
            if parent.call_sequence_index >= event.call_sequence_index:
                _fail(
                    f"event {event.event_id} (sequence {event.call_sequence_index}) "
                    f"references parent {parent_id} with sequence "
                    f"{parent.call_sequence_index}; parents must have a strictly "
                    "lower call_sequence_index"
                )
            if parent.event_type == EVENT_TYPE_METADATA:
                _fail(
                    f"event {event.event_id} lists the metadata event as a parent; "
                    "metadata produces no output and has no context_hash"
                )

    root_positions = [i for i, e in enumerate(events) if e.event_type == EVENT_TYPE_ROOT_INPUT]
    final_positions = [i for i, e in enumerate(events) if e.event_type == EVENT_TYPE_FINAL_OUTPUT]
    if len(events) > 1 and events[1].event_type != EVENT_TYPE_ROOT_INPUT:
        _fail(
            "second event must be root_input (root input is recorded exactly "
            f"once, before any boundary call), got {events[1].event_type!r}"
        )
    if len(root_positions) > 1:
        _fail("multiple root_input events (root input is recorded exactly once)")
    if len(final_positions) > 1:
        _fail("multiple final_output events (final output is recorded exactly once)")
    if final_positions and final_positions[0] != len(events) - 1:
        _fail("final_output must be the last event")

    if require_complete:
        if not root_positions:
            _fail("incomplete trace: no root_input event")
        if not final_positions:
            _fail("incomplete trace: no final_output event")


def verify_hashes(events: Iterable[TraceEvent]) -> None:
    """Recompute ``argument_hash`` and ``context_hash`` for every event and
    compare against the stored values; raise ValueError on any mismatch.

    Expects a trace that already passed :func:`validate_trace` (parents
    resolved, metadata first). Any upstream tampering ripples downstream
    because each context hash chains its parents' hashes in
    ``parent_event_ids`` order (PLAN §6).
    """
    events = list(events)
    by_id = {event.event_id: event for event in events}
    for event in events:
        if event.event_type == EVENT_TYPE_METADATA:
            continue
        expected_argument = argument_hash(event.event_type, event.name, event.payload)
        if expected_argument != event.argument_hash:
            _fail(
                f"argument_hash mismatch on event {event.event_id} (sequence "
                f"{event.call_sequence_index}): stored {event.argument_hash}, "
                f"recomputed {expected_argument}"
            )
        parent_hashes = []
        for parent_id in event.parent_event_ids:
            parent = by_id.get(parent_id)
            if parent is None or parent.context_hash is None:
                _fail(
                    f"event {event.event_id} parent {parent_id} has no "
                    "context_hash to chain from (run validate_trace first)"
                )
            parent_hashes.append(parent.context_hash)
        expected_context = context_hash(
            parent_hashes,
            event.event_type,
            event.name,
            event.payload,
            event.historical_response,
            event.status,
            event.error,
        )
        if expected_context != event.context_hash:
            _fail(
                f"context_hash mismatch on event {event.event_id} (sequence "
                f"{event.call_sequence_index}): stored {event.context_hash}, "
                f"recomputed {expected_context}"
            )
