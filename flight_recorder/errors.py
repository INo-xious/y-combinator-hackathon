"""Error types shared by the recorder and replayer (PLAN §2, §3).

``ReplayedError`` (the wrapper for historical non-builtin exceptions) lives in
``replayer.py`` per the repository layout; everything else is here.
"""

from __future__ import annotations

from typing import Any, Optional


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
