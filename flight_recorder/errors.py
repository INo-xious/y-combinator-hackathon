"""Error types shared by the recorder and replayer (PLAN §2, §3).

``ReplayedError`` (the wrapper for historical non-builtin exceptions) lives in
``replayer.py`` per the repository layout; everything else is here.
"""

from __future__ import annotations

import json
from typing import Any, Optional

# reason -> one-line human diagnosis, filled with .format(parent=...).
_LIKELY_CAUSES = {
    "argument_hash mismatch": (
        "Your agent changed the arguments it generates after {parent}."
    ),
    "name mismatch": (
        "Your agent now calls a different LLM/tool at this point than it did "
        "when the trace was recorded."
    ),
    "event_type mismatch": (
        "Your agent swapped an LLM call for a tool call (or vice versa) at "
        "this point in the flow."
    ),
    "parent_event_ids mismatch": (
        "Your agent rewired the data flow: this call now depends on different "
        "upstream events than the recorded run."
    ),
    "trace exhausted": (
        "Your agent makes more calls than the recorded run — an extra step "
        "was added after recording."
    ),
    "final output mismatch": (
        "Your agent produced a different final answer from the same recorded "
        "inputs — check logic that post-processes the last response after {parent}."
    ),
    "structured payload mismatch": (
        "The JSON *shape* of the arguments changed after {parent} (structured "
        "mode ignores values, so a key was added, removed, or re-typed)."
    ),
    "unconsumed events at exit": (
        "Your agent makes fewer calls than the recorded run — a recorded step "
        "was removed or skipped."
    ),
}


def _compact(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError):
        return repr(value)


class FlightRecorderError(Exception):
    """Base class for every error this package raises on purpose."""


class LifecycleError(FlightRecorderError):
    """A record/replay method was called out of order.

    Raised immediately at call time, before anything is written, so bad
    traces never reach disk (PLAN §2).
    """


class FinalOutputNotCalled(FlightRecorderError):
    """The context exited cleanly but ``record_final_output`` was never called."""


class SchedulingError(FlightRecorderError):
    """``DagScheduler`` contract misuse — a programmer error, not a replay outcome.

    Raised for invalid construction input (duplicate event ids, a parent that
    is not a schedulable event in the trace) and invalid queries or
    completions (unknown ids, completing an event twice, completing an event
    whose parents are not all consumed). Deliberately *not* part of the
    :class:`ReplayDivergence` family: it means the scheduler was driven
    wrongly, not that replay compared something unequal (DESIGN-SESSION-4 §4).
    """


class ReplayDivergence(FlightRecorderError):
    """Replay saw something other than what the trace recorded.

    Carries expected-vs-actual detail (event type, name, argument hash,
    parents) plus where in the trace the mismatch happened (PLAN §3).
    """

    def __init__(
        self,
        reason: str,
        *,
        expected: Optional[dict] = None,
        actual: Optional[dict] = None,
        at_sequence_index: Optional[int] = None,
        at_event_id: Optional[str] = None,
    ):
        details = []
        if at_sequence_index is not None:
            details.append(f"at sequence index {at_sequence_index}")
        if at_event_id is not None:
            details.append(f"event {at_event_id}")
        if expected is not None:
            details.append(f"expected {expected!r}")
        if actual is not None:
            details.append(f"actual {actual!r}")
        message = reason if not details else f"{reason} ({'; '.join(details)})"
        super().__init__(message)
        self.reason = reason
        self.expected = expected
        self.actual = actual
        self.at_sequence_index = at_sequence_index
        self.at_event_id = at_event_id
        # "{event_type}_{seq}: {name}" labels for the expected event's parents,
        # attached by the replayer (which can see the whole trace) so pretty()
        # can say "Parent: llm_call_2" instead of a bare UUID.
        self.parent_labels: list[str] = []

    def pretty(self) -> str:
        """Multi-line, human-first rendering of this divergence.

        Format::

            ReplayDivergence at tool_call_3: search_flights
            Expected: {"from": "London", "limit": 5, "to": "Tokyo"}
            Actual:   {"from": "London", "limit": 10, "to": "Tokyo"}
            Parent:   llm_call_2
            Likely cause: Your agent changed the arguments it generates after llm_call_2.
        """
        source = self.expected if isinstance(self.expected, dict) else None
        request = self.actual if isinstance(self.actual, dict) else None
        anchor = source or request or {}

        event_type = anchor.get("event_type")
        where = event_type or type(self).__name__.replace("ReplayDivergence", "event")
        if event_type and self.at_sequence_index is not None:
            where = f"{event_type}_{self.at_sequence_index}"
        name = anchor.get("name")
        header = f"{type(self).__name__} at {where}"
        if name:
            header += f": {name}"

        lines = [header]
        if source is not None and "payload" in source:
            lines.append(f"Expected: {_compact(source['payload'])}")
        elif source is not None:
            lines.append(f"Expected: {_compact(source)}")
        if request is not None and "payload" in request:
            lines.append(f"Actual:   {_compact(request['payload'])}")
        elif request is not None:
            lines.append(f"Actual:   {_compact(request)}")

        parent = None
        if self.parent_labels:
            parent = ", ".join(self.parent_labels)
        elif isinstance(anchor.get("parent_event_ids"), list) and anchor["parent_event_ids"]:
            parent = ", ".join(anchor["parent_event_ids"])
        if parent:
            lines.append(f"Parent:   {parent}")

        cause = _LIKELY_CAUSES.get(self.reason)
        if cause is None and self.reason.startswith("semantic"):
            cause = (
                "The semantic matcher rejected (or could not judge) the new "
                "payload against the recorded one."
            )
        if cause is not None:
            lines.append(
                "Likely cause: " + cause.format(parent=parent or "the previous step")
            )
        return "\n".join(lines)

    def detail(self) -> dict[str, Any]:
        """Machine-readable divergence detail for reports and CLI output."""
        return {
            "reason": self.reason,
            "expected": self.expected,
            "actual": self.actual,
            "at_sequence_index": self.at_sequence_index,
            "at_event_id": self.at_event_id,
        }


class FinalOutputMismatch(ReplayDivergence):
    """The replayed final output differs from the recorded one.

    A specialised divergence so callers can catch it separately while
    ``except ReplayDivergence`` still covers every mismatch.
    """


class PrematureEventError(ReplayDivergence):
    """A matched event's response was withheld: its prerequisites are not
    all consumed (DESIGN-SESSION-4 §1, §5).

    Prerequisites are the event's recorded parents — except for
    ``final_output``, whose prerequisite under strict replay is every other
    recorded event. In a single-threaded synchronous replay, blocking until
    prerequisites complete would deadlock with certainty (the only thread
    that could complete them is the one that would be waiting), so the
    withhold is fail-fast and carries the remediation surface instead:

    - ``missing_parent_ids`` — what must be consumed first, in recorded
      parent order (for ``final_output``: all other pending events in
      sequence order);
    - ``ready_event_ids`` — what the requester may legally do right now
      (non-empty whenever anything is pending, by the scheduler's liveness
      guarantee).

    Subclasses :class:`ReplayDivergence` so ``except ReplayDivergence``
    still covers every replay mismatch (same precedent as
    :class:`FinalOutputMismatch`); scheduler-driven consumers can catch it
    specifically and reschedule.
    """

    def __init__(
        self,
        reason: str,
        *,
        missing_parent_ids: list,
        ready_event_ids: list,
        expected: Optional[dict] = None,
        actual: Optional[dict] = None,
        at_sequence_index: Optional[int] = None,
        at_event_id: Optional[str] = None,
    ):
        super().__init__(
            reason,
            expected=expected,
            actual=actual,
            at_sequence_index=at_sequence_index,
            at_event_id=at_event_id,
        )
        self.missing_parent_ids = list(missing_parent_ids)
        self.ready_event_ids = list(ready_event_ids)

    def detail(self) -> dict[str, Any]:
        detail = super().detail()
        detail["missing_parent_ids"] = list(self.missing_parent_ids)
        detail["ready_event_ids"] = list(self.ready_event_ids)
        return detail
