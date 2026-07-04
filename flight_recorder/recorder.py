"""Recorder context manager: records boundary events to a JSONL trace file (PLAN §2).

Usage::

    with Recorder(agent_id="demo", capture_to="trace.jsonl") as recorder:
        root_id = recorder.record_root_input({"query": "..."})
        response, llm_id = recorder.record_llm_call(
            "llm_plan", {"prompt": "..."}, lambda: fake_llm(...), [root_id])
        recorder.record_final_output({"answer": response["text"]}, [llm_id])

Lifecycle rules, each enforced at call time *before* anything is written so
bad traces never reach disk:

- entering writes the metadata event (sequence 0) and refuses an existing
  ``capture_to`` unless ``overwrite=True``;
- ``record_root_input`` exactly once, before any boundary call;
- ``record_final_output`` exactly once, last — nothing may be recorded after
  it, and a clean exit without it raises :class:`FinalOutputNotCalled`;
- exiting via an agent exception propagates that exception unchanged and
  skips the final-output assertion (the partial trace on disk stays valid
  line-by-line).

Boundary calls execute ``call()`` themselves. If ``call()`` raises an
``Exception`` the event is recorded with ``status="error"`` and the original
exception is always re-raised — there is no swallow option. Non-``Exception``
``BaseException``s (KeyboardInterrupt, SystemExit) propagate unrecorded.

The optional ``redactor(payload) -> redacted_payload`` runs on every payload
and response *before hashing and before storage* — raw values never touch
disk or a hash — but the raw ``call()`` response is still what the agent gets
back. The recorder-generated metadata payload is not redacted. Pass the same
redactor to the Replayer for hash parity.

Every event is flushed as soon as it is written, so a crash leaves at most
one incomplete final line.
"""

from __future__ import annotations

import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional, Union

from .errors import FinalOutputNotCalled, LifecycleError
from .events import (
    EVENT_TYPE_FINAL_OUTPUT,
    EVENT_TYPE_LLM_CALL,
    EVENT_TYPE_METADATA,
    EVENT_TYPE_ROOT_INPUT,
    EVENT_TYPE_TOOL_CALL,
    RECORDER_VERSION,
    SCHEMA_VERSION,
    STATUS_ERROR,
    STATUS_OK,
    TraceEvent,
)
from .hashing import argument_hash, context_hash
from .storage import TraceWriter


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _identity(value: Any) -> Any:
    return value


class Recorder:
    """Records one agent run as a causal DAG of boundary events."""

    def __init__(
        self,
        agent_id: str,
        capture_to: Union[str, Path],
        overwrite: bool = False,
        redactor: Optional[Callable[[Any], Any]] = None,
    ):
        if type(agent_id) is not str or not agent_id:
            raise ValueError("agent_id must be a non-empty string")
        if redactor is not None and not callable(redactor):
            raise TypeError("redactor must be a callable: payload -> redacted_payload")
        self._agent_id = agent_id
        self._capture_to = Path(capture_to)
        self._overwrite = bool(overwrite)
        self._redactor = redactor if redactor is not None else _identity
        self._writer: Optional[TraceWriter] = None
        self._run_id: Optional[str] = None
        self._entered = False
        self._closed = False
        self._next_sequence = 0
        self._root_event_id: Optional[str] = None
        self._final_event_id: Optional[str] = None
        # context_hash by event_id, for chaining children (PLAN §6). The
        # metadata event is deliberately absent: it has no context_hash, so
        # it can never be used as a parent.
        self._context_hashes: dict[str, str] = {}

    @property
    def agent_id(self) -> str:
        return self._agent_id

    @property
    def capture_to(self) -> Path:
        return self._capture_to

    @property
    def run_id(self) -> Optional[str]:
        """The run's UUID; None before the context is entered."""
        return self._run_id

    # --- context manager ------------------------------------------------------

    def __enter__(self) -> "Recorder":
        if self._entered:
            raise LifecycleError(
                "Recorder context is not reentrant; create a new Recorder per run"
            )
        self._writer = TraceWriter(self._capture_to, overwrite=self._overwrite)
        try:
            self._run_id = str(uuid.uuid4())
            now = _utc_now()
            metadata = TraceEvent(
                event_id=str(uuid.uuid4()),
                run_id=self._run_id,
                agent_id=self._agent_id,
                parent_event_ids=[],
                call_sequence_index=self._next_sequence,
                event_type=EVENT_TYPE_METADATA,
                name=None,
                timestamp=now,
                payload={
                    "schema_version": SCHEMA_VERSION,
                    "recorder_version": RECORDER_VERSION,
                    "trace_creation_time": now,
                    "run_id": self._run_id,
                    "agent_id": self._agent_id,
                },
                historical_response=None,
                status=STATUS_OK,
                error=None,
                argument_hash=None,
                context_hash=None,
                latency_ms=None,
            )
            self._write(metadata)
        except BaseException:
            self._writer.close()
            raise
        self._entered = True
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        self._closed = True
        try:
            if exc_type is None and self._final_event_id is None:
                raise FinalOutputNotCalled(
                    "Recorder context exited cleanly but record_final_output "
                    "was never called"
                )
        finally:
            self._writer.close()
        # An exception from agent code propagates unchanged; the final-output
        # assertion above only runs on the clean-exit path, so we never mask
        # the user's exception with our own.
        return False

    # --- lifecycle methods ------------------------------------------------------

    def record_root_input(self, payload: Any) -> str:
        """Record the run's input; exactly once, before any boundary call.

        Returns the root event's id for use in ``parent_event_ids``.
        """
        self._require_active("record_root_input")
        if self._root_event_id is not None:
            raise LifecycleError(
                "record_root_input must be called exactly once (already recorded)"
            )
        event = self._build_event(
            event_type=EVENT_TYPE_ROOT_INPUT,
            name=None,
            payload=self._redactor(payload),
            parent_event_ids=[],
            historical_response=None,
            status=STATUS_OK,
            error=None,
            latency_ms=None,
        )
        self._write(event)
        self._root_event_id = event.event_id
        return event.event_id

    def record_llm_call(
        self,
        name: str,
        payload: Any,
        call: Callable[[], Any],
        parent_event_ids: list[str],
    ) -> tuple[Any, str]:
        """Execute ``call()``, record it as an llm_call event, and return
        ``(response, event_id)``. If ``call()`` raises, the event is recorded
        with ``status="error"`` and the original exception is re-raised."""
        return self._record_boundary(EVENT_TYPE_LLM_CALL, name, payload, call, parent_event_ids)

    def record_tool_call(
        self,
        name: str,
        payload: Any,
        call: Callable[[], Any],
        parent_event_ids: list[str],
    ) -> tuple[Any, str]:
        """Same contract as :meth:`record_llm_call`, recorded as a tool_call."""
        return self._record_boundary(EVENT_TYPE_TOOL_CALL, name, payload, call, parent_event_ids)

    def record_final_output(self, value: Any, parent_event_ids: list[str]) -> str:
        """Record the run's final output; exactly once, last. Returns its event id."""
        self._require_active("record_final_output")
        if self._root_event_id is None:
            raise LifecycleError("record_final_output called before record_root_input")
        event = self._build_event(
            event_type=EVENT_TYPE_FINAL_OUTPUT,
            name=None,
            payload=self._redactor(value),
            parent_event_ids=self._resolve_parents(parent_event_ids),
            historical_response=None,
            status=STATUS_OK,
            error=None,
            latency_ms=None,
        )
        self._write(event)
        self._final_event_id = event.event_id
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
        parents = self._resolve_parents(parent_event_ids)
        redacted_payload = self._redactor(payload)
        # Hashing validates strict JSON; doing it before call() runs means an
        # unrecordable payload fails before any side effect happens.
        argument_hash(event_type, name, redacted_payload)

        started = time.perf_counter()
        try:
            response = call()
        except Exception as exc:
            event = self._build_event(
                event_type=event_type,
                name=name,
                payload=redacted_payload,
                parent_event_ids=parents,
                historical_response=None,
                status=STATUS_ERROR,
                error={
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "traceback": traceback.format_exc(),
                },
                latency_ms=_elapsed_ms(started),
            )
            self._write(event)
            raise  # always re-raise the original exception (PLAN §2)
        latency_ms = _elapsed_ms(started)

        event = self._build_event(
            event_type=event_type,
            name=name,
            payload=redacted_payload,
            parent_event_ids=parents,
            historical_response=self._redactor(response),
            status=STATUS_OK,
            error=None,
            latency_ms=latency_ms,
        )
        self._write(event)
        return response, event.event_id

    def _require_active(self, method: str) -> None:
        if not self._entered:
            raise LifecycleError(
                f"{method} called outside an active Recorder context; "
                "use 'with Recorder(...) as recorder'"
            )
        if self._closed:
            raise LifecycleError(f"{method} called after the Recorder context exited")
        if self._final_event_id is not None:
            raise LifecycleError(
                f"{method} called after record_final_output: no calls of any "
                "kind are allowed after the final output"
            )

    def _resolve_parents(self, parent_event_ids: Any) -> list[str]:
        if type(parent_event_ids) is not list:
            raise ValueError("parent_event_ids must be a list of event ids")
        parents = list(parent_event_ids)
        for parent_id in parents:
            if parent_id not in self._context_hashes:
                raise ValueError(
                    f"unknown parent_event_id {parent_id!r}: parents must be "
                    "event ids returned by this recorder's record_* methods"
                )
        return parents

    def _build_event(
        self,
        *,
        event_type: str,
        name: Optional[str],
        payload: Any,
        parent_event_ids: list[str],
        historical_response: Any,
        status: str,
        error: Optional[dict],
        latency_ms: Optional[int],
    ) -> TraceEvent:
        # payload and historical_response must already be redacted.
        parent_context_hashes = [self._context_hashes[p] for p in parent_event_ids]
        return TraceEvent(
            event_id=str(uuid.uuid4()),
            run_id=self._run_id,
            agent_id=self._agent_id,
            parent_event_ids=list(parent_event_ids),
            call_sequence_index=self._next_sequence,
            event_type=event_type,
            name=name,
            timestamp=_utc_now(),
            payload=payload,
            historical_response=historical_response,
            status=status,
            error=error,
            argument_hash=argument_hash(event_type, name, payload),
            context_hash=context_hash(
                parent_context_hashes,
                event_type,
                name,
                payload,
                historical_response,
                status,
                error,
            ),
            latency_ms=latency_ms,
        )

    def _write(self, event: TraceEvent) -> None:
        self._writer.append(event)  # validates, writes one line, flushes
        if event.context_hash is not None:
            self._context_hashes[event.event_id] = event.context_hash
        self._next_sequence += 1


def _elapsed_ms(started: float) -> int:
    return max(0, int((time.perf_counter() - started) * 1000))
