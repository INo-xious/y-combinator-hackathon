"""Replay engines: strict, non-executing replay from a trace.

Two engines share one lifecycle: :class:`Replayer` (sequence-based matching,
PLAN §3) and :class:`TopologicalReplayer` (DAG-scheduled matching over
:class:`DagScheduler`, DESIGN-SESSION-4). ``ReplayedError`` lives here too.

Usage::

    with Replayer(trace_file="trace.jsonl") as replayer:
        root_id = replayer.record_root_input({"query": "..."})
        response, llm_id = replayer.record_llm_call(
            "llm_plan", {"prompt": "..."}, poison_call, [root_id])
        replayer.record_final_output({"answer": response["text"]}, [llm_id])

Same public methods and lifecycle rules as :class:`~flight_recorder.recorder.Recorder`
(PLAN §3), so the same agent function runs unmodified against either
(``recorder: Recorder | Replayer``). ``call`` is accepted for signature
parity but is **never invoked** — the historical response (or error) is
replayed from the trace instead.

Matching is strict and sequence-based: every call computes a local
``argument_hash`` from ``{event_type, name, redacted_payload}`` and compares
it, along with ``event_type``, ``name``, and ``parent_event_ids`` (exact,
order-sensitive), against the next unconsumed non-metadata event. Any
mismatch raises :class:`~flight_recorder.errors.ReplayDivergence` (or its
subclass :class:`~flight_recorder.errors.FinalOutputMismatch` for a
final-output value mismatch), carrying expected-vs-actual detail and the
sequence index where it happened.

A matched event with ``status="error"`` re-raises the historical error: a
builtin exception type replays as itself; anything else replays as
:class:`ReplayedError` (Python can't safely reconstruct arbitrary custom
exception classes from a trace — agent code that catches the *original*
custom exception class will diverge on replay; this is a documented MVP
limitation, not a bug).
"""

from __future__ import annotations

import builtins
from pathlib import Path
from typing import Any, Callable, Optional, Union, Literal, NoReturn

from .crypto import Cipher
from .dag import validate_trace, verify_hashes
from .errors import (
    FinalOutputMismatch,
    FinalOutputNotCalled,
    FlightRecorderError,
    LifecycleError,
    PrematureEventError,
    ReplayDivergence,
    SchedulingError,
)
from .events import EVENT_TYPE_METADATA, TraceEvent
from .hashing import FLOAT_POLICIES, FLOAT_POLICY_ALLOW, argument_hash
from .report import ReplayReport
from .signing import resolve_signing_key, verify_signatures
from .storage import read_events


class ReplayedError(FlightRecorderError):
    """A historical non-builtin exception re-raised during replay.

    Python cannot safely reconstruct an arbitrary custom exception class
    from a trace, so any non-builtin exception recorded during the run
    replays as this wrapper instead of its original type. Agent code that
    specifically catches the original custom exception class will diverge
    on replay — acceptable and detectable for MVP (PLAN §3, Risks).
    """

    def __init__(self, original_type: str, message: str):
        super().__init__(f"{original_type}: {message}")
        self.original_type = original_type
        self.original_message = message


def _identity(value: Any) -> Any:
    return value


REPLAY_MODE_STRICT = "strict"
REPLAY_MODE_STRUCTURED = "structured"
REPLAY_MODE_SEMANTIC = "semantic"
REPLAY_MODES = (REPLAY_MODE_STRICT, REPLAY_MODE_STRUCTURED, REPLAY_MODE_SEMANTIC)


def _json_schema_shape(value: Any) -> tuple:
    """Return a deterministic JSON-schema-ish shape for tolerant replay.

    Structured replay intentionally ignores primitive values and compares the
    JSON shape: object keys, nested value types, and array item shapes.
    """

    value_type = type(value)
    if value_type is dict:
        return (
            "object",
            tuple((key, _json_schema_shape(value[key])) for key in sorted(value)),
        )
    if value_type is list:
        return ("array", tuple(sorted({_json_schema_shape(item) for item in value})))
    if value_type is str:
        return ("string",)
    if value_type is int:
        return ("integer",)
    if value_type is float:
        return ("number",)
    if value_type is bool:
        return ("boolean",)
    if value is None:
        return ("null",)
    return (value_type.__name__,)


def _request_summary(
    event_type: str,
    name: Optional[str],
    payload: Any,
    argument_hash_value: str,
    parents: list[str],
) -> dict:
    """The "actual" side of expected-vs-actual divergence detail (shared by
    the sequence and topological matchers — DESIGN-SESSION-4 DRY note)."""
    return {
        "event_type": event_type,
        "name": name,
        "payload": payload,
        "argument_hash": argument_hash_value,
        "parent_event_ids": parents,
    }


def _event_summary(event: TraceEvent) -> dict:
    """The "expected" side of expected-vs-actual divergence detail."""
    return {
        "event_type": event.event_type,
        "name": event.name,
        "payload": event.payload,
        "argument_hash": event.argument_hash,
        "parent_event_ids": event.parent_event_ids,
    }


class DagScheduler:
    """Readiness state machine over one validated trace's causal DAG.

    Pure bookkeeping: no I/O, no matching, no hashing. Specified over
    *validated flight-recorder trace event lists* (the shape ``dag.py``
    guarantees), not arbitrary DAGs — the liveness guarantee below leans on
    the validated invariant that every parent has a strictly lower
    ``call_sequence_index`` than its child.

    Per-event lifecycle (metadata is excluded before any state is assigned)::

           validated trace ──▶ ┌─────────────┐
           (metadata dropped)  │   PENDING   │  some parent not yet consumed
                               │  (blocked)  │
                               └──────┬──────┘
                                      │ last parent consumed
                                      ▼
                               ┌─────────────┐  root_input (parents=[]) starts
                               │    READY    │  here; ready is never empty
                               └──────┬──────┘  while anything is pending
                                      │ complete(event_id)   complete() on unknown /
                                      ▼                      duplicate / non-ready id
                               ┌─────────────┐               ──▶ SchedulingError
                               │  CONSUMED   │───▶ unlocks children whose other
                               └─────────────┘     parents are already consumed

    **Liveness (no intrinsic deadlock):** among pending events, the one with
    the lowest ``call_sequence_index`` has all parents at strictly lower
    indices, so none of them can be pending — it is always ready. A consumer
    that only requests ready events can therefore drain any validated trace.

    Readiness is recomputed from the consumed set on demand (a property of
    ``all parents consumed``) rather than tracked with in-degree counters:
    one piece of state, no desync risk, O(V·E) per full drain — irrelevant at
    MVP trace sizes (DESIGN-SESSION-4 D7).
    """

    def __init__(self, events: list[TraceEvent]):
        self._events: dict[str, TraceEvent] = {}
        for event in events:
            if event.event_type == EVENT_TYPE_METADATA:
                continue  # validation-only, never schedulable (PLAN §1)
            if event.event_id in self._events:
                raise SchedulingError(f"duplicate event_id {event.event_id}")
            self._events[event.event_id] = event
        for event in self._events.values():
            for parent_id in event.parent_event_ids:
                if parent_id not in self._events:
                    raise SchedulingError(
                        f"event {event.event_id} references parent {parent_id} "
                        "which is not a schedulable event in this trace"
                    )
        self._consumed: set[str] = set()
        self._pending_ids: set[str] = set(self._events)
        self._ordered_events = sorted(
            self._events.values(),
            key=lambda event: event.call_sequence_index,
        )

    @property
    def pending(self) -> list[TraceEvent]:
        """Unconsumed events, ascending ``call_sequence_index``."""
        return [e for e in self._ordered_events if e.event_id in self._pending_ids]

    @property
    def done(self) -> bool:
        return not self._pending_ids

    def _get(self, event_id: str) -> TraceEvent:
        try:
            return self._events[event_id]
        except KeyError:
            raise SchedulingError(
                f"unknown event_id {event_id!r} (not a schedulable event in this trace)"
            ) from None

    def is_ready(self, event_id: str) -> bool:
        """True when *event_id* is pending and every parent is consumed.

        Consumed events are not ready (readiness is a property of pending
        events only)."""
        event = self._get(event_id)
        if event.event_id not in self._pending_ids:
            return False
        return all(pid in self._consumed for pid in event.parent_event_ids)

    def ready_events(self) -> list[TraceEvent]:
        """The ready subset of :attr:`pending`, ascending sequence order."""
        return [
            e
            for e in self._ordered_events
            if e.event_id in self._pending_ids
            and all(pid in self._consumed for pid in e.parent_event_ids)
        ]

    def missing_parents(self, event_id: str) -> list[str]:
        """Unconsumed parents of *event_id*, in recorded parent order."""
        event = self._get(event_id)
        return [pid for pid in event.parent_event_ids if pid not in self._consumed]

    def complete(self, event_id: str) -> None:
        """Consume a ready event; anything else is a :class:`SchedulingError`."""
        event = self._get(event_id)
        if event.event_id in self._consumed:
            raise SchedulingError(f"event {event_id} was already completed")
        missing = self.missing_parents(event_id)
        if missing:
            raise SchedulingError(
                f"event {event_id} is not ready: parents not consumed: {missing}"
            )
        self._consumed.add(event_id)
        self._pending_ids.remove(event_id)


class Replayer:
    """Strictly replays one agent run from a trace, never executing calls.

    Subclass contract (load-bearing seam — :class:`TopologicalReplayer`):
    the lifecycle surface (``__enter__``/``__exit__``/``record_*`` and their
    guards) is shared; a matching engine varies only these internals:
    ``_match_next`` (candidate selection + divergence taxonomy),
    ``_validate_parents`` (parent-id precondition), and
    ``_unconsumed_event_ids`` (what "left over" means). Bookkeeping written
    by ``_match_next`` — ``_matched_event_ids``, ``_divergence`` via
    ``_fail_divergence``, ``_final_output_matched`` — must be maintained by
    any override; ``_reraise_historical_error`` is shared as-is.
    """

    def __init__(
        self,
        trace_file: Union[str, Path],
        redactor: Optional[Callable[[Any], Any]] = None,
        *,
        mode: str = REPLAY_MODE_STRICT,
        semantic_matcher: Optional[Callable[[Any, Any], bool]] = None,
        float_policy: str = FLOAT_POLICY_ALLOW,
        signing_key: Union[bytes, str, None] = None,
        require_signatures: bool = False,
        cipher: Optional[Cipher] = None,
    ):
        if redactor is not None and not callable(redactor):
            raise TypeError("redactor must be a callable: payload -> redacted_payload")
        if mode not in REPLAY_MODES:
            raise ValueError(f"mode must be one of {REPLAY_MODES}, got {mode!r}")
        if semantic_matcher is not None and not callable(semantic_matcher):
            raise TypeError("semantic_matcher must be callable when provided")
        if float_policy not in FLOAT_POLICIES:
            raise ValueError(f"float_policy must be one of {FLOAT_POLICIES}, got {float_policy!r}")
        self._trace_file = Path(trace_file)
        self._redactor = redactor if redactor is not None else _identity
        self._cipher = cipher
        self._float_policy = float_policy
        self._signing_key = resolve_signing_key(signing_key)
        self._require_signatures = bool(require_signatures)
        if self._require_signatures and self._signing_key is None:
            raise ValueError(
                "require_signatures=True needs a signing key: pass signing_key "
                "or set AGENT_RR_SIGNING_KEY"
            )
        self._mode = mode
        self._semantic_matcher = semantic_matcher
        self._events: Optional[list[TraceEvent]] = None
        self._entered = False
        self._closed = False
        self._next_index = 1  # index 0 is always metadata; replay starts after it
        self._root_event_id: Optional[str] = None
        self._final_output_called = False
        self._matched_event_ids: list[str] = []
        self._run_id: Optional[str] = None
        self._divergence: Optional[dict] = None
        self._final_output_matched: Optional[bool] = None

    @property
    def trace_file(self) -> Path:
        return self._trace_file

    @property
    def run_id(self) -> Optional[str]:
        """The replayed run's UUID (from the trace's metadata event); None before entry."""
        return self._run_id

    @property
    def report(self) -> ReplayReport:
        """A snapshot of replay progress so far; meaningful during and after the run."""
        return ReplayReport(
            run_id=self._run_id,
            matched_event_ids=list(self._matched_event_ids),
            unconsumed_event_ids=self._unconsumed_event_ids(),
            divergence=self._divergence,
            final_output_matched=self._final_output_matched,
        )

    # --- context manager ------------------------------------------------------

    def __enter__(self) -> "Replayer":
        if self._entered:
            raise LifecycleError(
                "Replayer context is not reentrant; create a new Replayer per run"
            )
        events = read_events(self._trace_file, cipher=self._cipher)
        validate_trace(events)
        verify_hashes(events)
        if self._signing_key is not None:
            verify_signatures(events, self._signing_key, require=self._require_signatures)
        self._events = events
        self._run_id = events[0].run_id
        self._entered = True
        return self

    def __exit__(self, exc_type, exc, tb) -> Literal[False]:
        self._closed = True
        if exc_type is None:
            if not self._final_output_called:
                unconsumed_ids = self._unconsumed_event_ids()
                if unconsumed_ids:
                    self._fail_divergence(
                        ReplayDivergence(
                            "unconsumed events at exit",
                            expected=None,
                            actual={"unconsumed_event_ids": unconsumed_ids},
                            at_sequence_index=self._next_index,
                        )
                    )
                raise FinalOutputNotCalled(
                    "Replayer context exited cleanly but record_final_output "
                    "was never called"
                )
        # An exception (agent's own, or one we raised at call time) propagates
        # unchanged; the clean-exit assertions above only run when there is
        # none, so we never mask the caller's exception with our own.
        return False

    # --- lifecycle methods ------------------------------------------------------

    def record_root_input(self, payload: Any) -> str:
        """Match the run's recorded input; exactly once, before any boundary call.

        Returns the historical root event's id for use in ``parent_event_ids``.
        """
        self._require_active("record_root_input")
        if self._root_event_id is not None:
            raise LifecycleError(
                "record_root_input must be called exactly once (already recorded)"
            )
        redacted = self._redactor(payload)
        event = self._match_next("root_input", None, redacted, [])
        self._root_event_id = event.event_id
        return event.event_id

    def record_llm_call(
        self,
        name: str,
        payload: Any,
        call: Callable[[], Any],
        parent_event_ids: list[str],
    ) -> tuple[Any, str]:
        """Match an ``llm_call`` and return ``(historical_response, event_id)``.

        ``call`` is never invoked. If the matched event recorded an error,
        the historical error is re-raised instead of returning."""
        return self._record_boundary("llm_call", name, payload, call, parent_event_ids)

    def record_tool_call(
        self,
        name: str,
        payload: Any,
        call: Callable[[], Any],
        parent_event_ids: list[str],
    ) -> tuple[Any, str]:
        """Same contract as :meth:`record_llm_call`, matched as a tool_call."""
        return self._record_boundary("tool_call", name, payload, call, parent_event_ids)

    def record_final_output(self, value: Any, parent_event_ids: list[str]) -> str:
        """Match the run's recorded final output; exactly once, last.

        Returns its event id. A structural mismatch (wrong shape/position)
        raises :class:`ReplayDivergence`; a same-shape value mismatch raises
        the more specific :class:`FinalOutputMismatch`."""
        self._require_active("record_final_output")
        if self._root_event_id is None:
            raise LifecycleError("record_final_output called before record_root_input")
        parents = self._validate_parents(parent_event_ids)
        redacted = self._redactor(value)
        event = self._match_next("final_output", None, redacted, parents, final=True)
        self._final_output_called = True
        return event.event_id

    # --- internals ------------------------------------------------------

    def _record_boundary(
        self,
        event_type: str,
        name: str,
        payload: Any,
        call: Callable[[], Any],
        parent_event_ids: list[str],
    ) -> tuple[Any, str]:
        method = f"record_{event_type}"
        self._require_active(method)
        if self._root_event_id is None:
            raise LifecycleError(f"{method} called before record_root_input")
        if type(name) is not str or not name:
            raise ValueError(f"name must be a non-empty string, got {name!r}")
        if not callable(call):
            raise TypeError("call must be a zero-argument callable")
        parents = self._validate_parents(parent_event_ids)
        redacted_payload = self._redactor(payload)
        event = self._match_next(event_type, name, redacted_payload, parents)
        if event.status == "ok":
            return event.historical_response, event.event_id
        self._reraise_historical_error(event)

    def _match_next(
        self,
        event_type: str,
        name: Optional[str],
        redacted_payload: Any,
        parents: list[str],
        *,
        final: bool = False,
    ) -> TraceEvent:
        assert self._events is not None
        # Hashing validates strict JSON before anything else, same as the
        # recorder: an unrecordable payload fails before any comparison.
        computed_hash = argument_hash(
            event_type, name, redacted_payload, float_policy=self._float_policy
        )

        if self._next_index >= len(self._events):
            self._fail_divergence(
                ReplayDivergence(
                    "trace exhausted",
                    expected=None,
                    actual=_request_summary(
                        event_type, name, redacted_payload, computed_hash, parents
                    ),
                    at_sequence_index=self._next_index,
                ),
                final=final,
            )

        candidate = self._events[self._next_index]
        reason: str | None = None
        if candidate.event_type != event_type:
            reason = "event_type mismatch"
        elif candidate.name != name:
            reason = "name mismatch"
        elif candidate.parent_event_ids != parents:
            reason = "parent_event_ids mismatch"
        else:
            reason = self._payload_mismatch_reason(
                candidate,
                computed_hash,
                redacted_payload,
                final=final,
            )

        if reason is not None:
            final_mismatch_reasons = (
                "final output mismatch",
                "structured final output mismatch",
                "semantic final output mismatch",
            )
            error_cls = (
                FinalOutputMismatch
                if reason in final_mismatch_reasons
                else ReplayDivergence
            )
            self._fail_divergence(
                error_cls(
                    reason,
                    expected=_event_summary(candidate),
                    actual=_request_summary(
                        event_type, name, redacted_payload, computed_hash, parents
                    ),
                    at_sequence_index=self._next_index,
                    at_event_id=candidate.event_id,
                ),
                final=final,
            )

        self._matched_event_ids.append(candidate.event_id)
        self._next_index += 1
        if final:
            self._final_output_matched = True
        return candidate

    def _payload_mismatch_reason(
        self,
        candidate: TraceEvent,
        computed_hash: str,
        redacted_payload: Any,
        *,
        final: bool,
    ) -> Optional[str]:
        if candidate.argument_hash == computed_hash:
            return None

        if self._mode == REPLAY_MODE_STRUCTURED:
            if _json_schema_shape(candidate.payload) == _json_schema_shape(redacted_payload):
                return None
            return "structured final output mismatch" if final else "structured payload mismatch"

        if self._mode == REPLAY_MODE_SEMANTIC:
            if self._semantic_matcher is None:
                return "semantic matcher unavailable"
            try:
                if self._semantic_matcher(candidate.payload, redacted_payload):
                    return None
            except Exception as exc:
                return f"semantic matcher error: {type(exc).__name__}: {exc}"
            return "semantic final output mismatch" if final else "semantic payload mismatch"

        return "final output mismatch" if final else "argument_hash mismatch"

    def _unconsumed_event_ids(self) -> list[str]:
        """Ids of not-yet-consumed events. The sequence engine consumes in
        file order, so this is the tail from the cursor; the topological
        engine overrides it with scheduler state."""
        if self._events is None:
            return []
        return [e.event_id for e in self._events[self._next_index :]]

    def _fail_divergence(self, err: ReplayDivergence, *, final: bool = False) -> None:
        """Record *err* in the report bookkeeping and raise it."""
        err.parent_labels = self._parent_labels_for(err)
        self._divergence = err.detail()
        if final:
            self._final_output_matched = False
        raise err

    def _parent_labels_for(self, err: ReplayDivergence) -> list[str]:
        """Human labels ("llm_call_2: llm_plan") for the diverging event's
        recorded parents, so ``ReplayDivergence.pretty()`` can point at the
        upstream cause instead of bare UUIDs."""
        if self._events is None:
            return []
        anchor = err.expected if isinstance(err.expected, dict) else None
        parent_ids = (anchor or {}).get("parent_event_ids")
        if not isinstance(parent_ids, list):
            return []
        by_id = {e.event_id: e for e in self._events}
        labels = []
        for parent_id in parent_ids:
            event = by_id.get(parent_id)
            if event is None:
                labels.append(parent_id)
            else:
                label = f"{event.event_type}_{event.call_sequence_index}"
                if event.name:
                    label += f": {event.name}"
                labels.append(label)
        return labels

    def _reraise_historical_error(self, event: TraceEvent) -> NoReturn:
        assert event.error is not None
        error_type = event.error["type"]
        message = event.error["message"]
        candidate = getattr(builtins, error_type, None)
        if isinstance(candidate, type) and issubclass(candidate, BaseException):
            raise candidate(message)
        raise ReplayedError(error_type, message)

    def _require_active(self, method: str) -> None:
        if not self._entered:
            raise LifecycleError(
                f"{method} called outside an active Replayer context; "
                "use 'with Replayer(...) as replayer'"
            )
        if self._closed:
            raise LifecycleError(f"{method} called after the Replayer context exited")
        if self._final_output_called:
            raise LifecycleError(
                f"{method} called after record_final_output: no calls of any "
                "kind are allowed after the final output"
            )

    def _validate_parents(self, parent_event_ids: Any) -> list[str]:
        if type(parent_event_ids) is not list:
            raise ValueError("parent_event_ids must be a list of event ids")
        parents = list(parent_event_ids)
        known = set(self._matched_event_ids)
        for parent_id in parents:
            if parent_id not in known:
                raise ValueError(
                    f"unknown parent_event_id {parent_id!r}: parents must be "
                    "event ids returned by this replayer's record_* methods"
                )
        return parents


class TopologicalReplayer(Replayer):
    """Replays one agent run in any valid topological order of the trace DAG.

    Same constructor, public methods, and lifecycle rules as
    :class:`Replayer`, but matching is set-based over the scheduler's
    *pending* events instead of cursor-based over the next sequence index:
    independent sibling branches may replay in any order that respects the
    recorded ``parent_event_ids`` edges (DESIGN-SESSION-4 §3).

    Signature parity is not full semantic parity: parent ids here are pure
    match data (design decision D5) — an unknown parent id surfaces as a
    ``parent_event_ids mismatch`` divergence, where :class:`Replayer` and
    ``Recorder`` raise ``ValueError`` at the API boundary.

    Matching pipeline for one request ``R = (type, name, payload→hash H,
    parents P)``, evaluated top to bottom, first exit wins::

         U = scheduler.pending
         │
         ├─ U empty ──────────────────────▶ ReplayDivergence("trace exhausted")
         ├─ K = {e ∈ U : type/name/H equal}
         │   └─ K empty
         │       ├─ exactly one e ∈ U with same (type,name), different hash
         │       │     ├─ final ─────────▶ FinalOutputMismatch
         │       │     └─ else ──────────▶ Divergence("argument_hash mismatch")
         │       └─ otherwise ───────────▶ Divergence("no matching unconsumed
         │                                  event", expected = ready set)
         ├─ K_p = {e ∈ K : parents == P}
         │   └─ K_p empty ───────────────▶ Divergence("parent_event_ids mismatch")
         ├─ c = lowest call_sequence_index in K_p
         ├─ WITHHOLD GATE (PrematureEventError — response withheld)
         │   ├─ final and U ≠ {c}
         │   └─ c not ready
         └─ consume c ──▶ status ok → (historical_response, event_id)
                          status error → re-raise historical error

    Exact identity beats nearest-ready guess: when (type, name, H) all equal
    a blocked event, its prematurity is reported even if a *ready* event
    shares (type, name) with a different hash — three identity components
    agreeing means the caller named that specific event.
    """

    def __init__(
        self,
        trace_file: Union[str, Path],
        redactor: Optional[Callable[[Any], Any]] = None,
        *,
        mode: str = REPLAY_MODE_STRICT,
        semantic_matcher: Optional[Callable[[Any, Any], bool]] = None,
        float_policy: str = FLOAT_POLICY_ALLOW,
        signing_key: Union[bytes, str, None] = None,
        require_signatures: bool = False,
        cipher: Optional[Cipher] = None,
    ):
        super().__init__(
            trace_file,
            redactor=redactor,
            mode=mode,
            semantic_matcher=semantic_matcher,
            float_policy=float_policy,
            signing_key=signing_key,
            require_signatures=require_signatures,
            cipher=cipher,
        )
        self._scheduler: Optional[DagScheduler] = None

    def __enter__(self) -> "TopologicalReplayer":
        super().__enter__()
        assert self._events is not None
        self._scheduler = DagScheduler(self._events)
        return self

    # --- engine variation points (see Replayer subclass contract) -----------------

    def _unconsumed_event_ids(self) -> list[str]:
        if self._scheduler is None:
            return []
        return [e.event_id for e in self._scheduler.pending]

    def _validate_parents(self, parent_event_ids: Any) -> list[str]:
        # Topological mode: parent ids are pure match data (D5). Malformed
        # entries can never equal the schema-validated UUID strings recorded
        # in the trace, so they surface as parent_event_ids mismatches.
        if type(parent_event_ids) is not list:
            raise ValueError("parent_event_ids must be a list of event ids")
        return list(parent_event_ids)

    def _match_next(
        self,
        event_type: str,
        name: Optional[str],
        redacted_payload: Any,
        parents: list[str],
        *,
        final: bool = False,
    ) -> TraceEvent:
        assert self._scheduler is not None
        # Hashing validates strict JSON before anything else (recorder parity).
        computed_hash = argument_hash(
            event_type, name, redacted_payload, float_policy=self._float_policy
        )
        actual = _request_summary(event_type, name, redacted_payload, computed_hash, parents)

        pending = self._scheduler.pending
        if not pending:
            self._fail_divergence(
                ReplayDivergence("trace exhausted", expected=None, actual=actual),
                final=final,
            )

        exact = [
            e
            for e in pending
            if e.event_type == event_type
            and e.name == name
            and self._payload_mismatch_reason(
                e, computed_hash, redacted_payload, final=final
            )
            is None
        ]
        if not exact:
            near = [
                e for e in pending if e.event_type == event_type and e.name == name
            ]
            if len(near) == 1:
                # Unambiguous target, wrong payload: keep the Session-3 reason
                # vocabulary (and FinalOutputMismatch contract) for this case.
                reason = self._payload_mismatch_reason(
                    near[0], computed_hash, redacted_payload, final=final
                )
                assert reason is not None
                error_cls = FinalOutputMismatch if final else ReplayDivergence
                self._fail_divergence(
                    error_cls(
                        reason,
                        expected=_event_summary(near[0]),
                        actual=actual,
                        at_sequence_index=near[0].call_sequence_index,
                        at_event_id=near[0].event_id,
                    ),
                    final=final,
                )
            # No single expected event exists in a set-based matcher: the
            # ready set is the expectation surface.
            ready_summary = [
                {"event_id": e.event_id, "event_type": e.event_type, "name": e.name}
                for e in self._scheduler.ready_events()
            ]
            self._fail_divergence(
                ReplayDivergence(
                    "no matching unconsumed event",
                    expected={"ready_events": ready_summary},
                    actual=actual,
                ),
                final=final,
            )

        with_parents = [e for e in exact if e.parent_event_ids == parents]
        if not with_parents:
            self._fail_divergence(
                ReplayDivergence(
                    "parent_event_ids mismatch",
                    expected=_event_summary(exact[0]),
                    actual=actual,
                    at_sequence_index=exact[0].call_sequence_index,
                    at_event_id=exact[0].event_id,
                ),
                final=final,
            )

        # Identical duplicates share one parent list, hence one readiness;
        # consume them in recorded order (lowest sequence — pending is sorted).
        candidate = with_parents[0]

        # WITHHOLD GATE: never block (a single-threaded wait can never be
        # satisfied — Theorem 2), never deliver; fail fast with remediation.
        if final:
            others = [e.event_id for e in pending if e.event_id != candidate.event_id]
            if others:
                self._fail_divergence(
                    PrematureEventError(
                        "response withheld: final_output requested while "
                        "events remain unconsumed",
                        missing_parent_ids=others,
                        ready_event_ids=[
                            e.event_id for e in self._scheduler.ready_events()
                        ],
                        expected=_event_summary(candidate),
                        actual=actual,
                        at_sequence_index=candidate.call_sequence_index,
                        at_event_id=candidate.event_id,
                    ),
                    final=True,
                )
        elif not self._scheduler.is_ready(candidate.event_id):
            self._fail_divergence(
                PrematureEventError(
                    "response withheld: parents not consumed",
                    missing_parent_ids=self._scheduler.missing_parents(
                        candidate.event_id
                    ),
                    ready_event_ids=[
                        e.event_id for e in self._scheduler.ready_events()
                    ],
                    expected=_event_summary(candidate),
                    actual=actual,
                    at_sequence_index=candidate.call_sequence_index,
                    at_event_id=candidate.event_id,
                ),
                final=final,
            )

        self._scheduler.complete(candidate.event_id)
        self._matched_event_ids.append(candidate.event_id)
        if final:
            self._final_output_matched = True
        return candidate
