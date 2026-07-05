"""Small helpers for recording hand-rolled agent loops.

The core Recorder/Replayer API is still the source of truth. This module only
adds loop-shaped naming and parent bookkeeping for ReAct-style agents where
each iteration makes one or more boundary calls before deciding whether to
continue.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


class LoopRun:
    """Parent-tracking helper for one recorded or replayed loop run."""

    def __init__(self, rr: Any, root_event_id: str):
        self._rr = rr
        self._current_parent_ids = [root_event_id]
        self._next_step_index = 1

    @classmethod
    def start(cls, rr: Any, root_payload: Any) -> "LoopRun":
        """Record or replay the root input and initialize loop parents."""

        return cls(rr, rr.record_root_input(root_payload))

    @property
    def current_parent_ids(self) -> list[str]:
        """Return a copy of the parent ids used by default for the next call."""

        return list(self._current_parent_ids)

    def step(self, label: str | None = None) -> "LoopStep":
        """Return the next 1-based loop step.

        If *label* is omitted, the boundary prefix is ``step_1``, ``step_2``,
        and so on.
        """

        index = self._next_step_index
        self._next_step_index += 1
        return LoopStep(self, label or f"step_{index}", index)

    def advance(self, parent_event_ids: list[str]) -> None:
        """Set the default parents for the next loop boundary or final output."""

        if type(parent_event_ids) is not list:
            raise ValueError("parent_event_ids must be a list of event ids")
        self._current_parent_ids = list(parent_event_ids)

    def final(self, value: Any, parent_event_ids: list[str] | None = None) -> str:
        """Record or replay the final output from explicit or current parents."""

        parents = self.current_parent_ids if parent_event_ids is None else parent_event_ids
        event_id = self._rr.record_final_output(value, parents)
        self.advance([event_id])
        return event_id


@dataclass(frozen=True)
class LoopStep:
    """One loop iteration with namespaced LLM/tool boundary helpers."""

    loop: LoopRun
    label: str
    index: int

    def llm(
        self,
        name: str,
        payload: Any,
        call: Callable[[], Any],
        parent_event_ids: list[str] | None = None,
    ) -> tuple[Any, str]:
        """Record or replay an LLM call named ``{step_label}.{name}``."""

        parents = self.loop.current_parent_ids if parent_event_ids is None else parent_event_ids
        response, event_id = self.loop._rr.record_llm_call(
            self._boundary_name(name), payload, call, parents
        )
        self.loop.advance([event_id])
        return response, event_id

    def tool(
        self,
        name: str,
        payload: Any,
        call: Callable[[], Any],
        parent_event_ids: list[str] | None = None,
    ) -> tuple[Any, str]:
        """Record or replay a tool call named ``{step_label}.{name}``."""

        parents = self.loop.current_parent_ids if parent_event_ids is None else parent_event_ids
        response, event_id = self.loop._rr.record_tool_call(
            self._boundary_name(name), payload, call, parents
        )
        self.loop.advance([event_id])
        return response, event_id

    def _boundary_name(self, name: str) -> str:
        if type(name) is not str or not name:
            raise ValueError(f"name must be a non-empty string, got {name!r}")
        return f"{self.label}.{name}"
