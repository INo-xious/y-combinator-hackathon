"""Context-local capture state for framework integrations.

The explicit ``Recorder`` / ``Replayer`` API remains the source of truth.
This module is the small bridge that lets framework wrappers find the active
flight recorder without threading it through every LangGraph node:

    with Recorder(...) as rr:
        result = run_agent_rr(rr, payload, graph)

Wrappers read ``active_rr`` and ``current_parent_ids`` at invocation time.
``contextvars`` keep state local to the current execution context, which is the
right default for LangGraph's task-style execution and future async support.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator, Optional
from contextvars import ContextVar, Token


active_rr: ContextVar[Any | None] = ContextVar("agent_rr_active_rr", default=None)
current_parent_ids: ContextVar[list[str]] = ContextVar(
    "agent_rr_current_parent_ids", default=[]
)


@dataclass(frozen=True)
class CapturedResponse:
    """Return wrapper used by integrations during live recording.

    ``raw`` is returned to the user's framework so their graph keeps seeing
    native SDK/LangChain objects. ``stored`` is strict-JSON data written into
    the trace and returned during replay.
    """

    raw: Any
    stored: Any


def get_active_rr() -> Any | None:
    """Return the recorder/replayer currently active in this context."""

    return active_rr.get()


def get_current_parent_ids() -> list[str]:
    """Return a copy of the current causal parent list."""

    return list(current_parent_ids.get())


def set_current_parent_ids(parent_ids: list[str]) -> Token[list[str]]:
    """Set the current causal parent list and return the reset token."""

    return current_parent_ids.set(list(parent_ids))


def set_active_rr(rr: Any | None) -> Token[Any | None]:
    """Set the active recorder/replayer and return the reset token."""

    return active_rr.set(rr)


def reset_active_rr(token: Token[Any | None]) -> None:
    active_rr.reset(token)


def reset_current_parent_ids(token: Token[list[str]]) -> None:
    current_parent_ids.reset(token)


@contextmanager
def parent_scope(parent_ids: list[str]) -> Iterator[None]:
    """Temporarily set parents for manual fork/join flows.

    Most linear LangGraph agents do not need this. It is the explicit escape
    hatch for sibling branches, joins, and hand-rolled parallel tool loops.
    """

    token = set_current_parent_ids(parent_ids)
    try:
        yield
    finally:
        reset_current_parent_ids(token)


@contextmanager
def capture_context(rr: Any, parent_ids: Optional[list[str]] = None) -> Iterator[None]:
    """Temporarily bind ``rr`` and optional parents to this execution context."""

    rr_token = set_active_rr(rr)
    parent_token = set_current_parent_ids(parent_ids or [])
    try:
        yield
    finally:
        reset_current_parent_ids(parent_token)
        reset_active_rr(rr_token)
