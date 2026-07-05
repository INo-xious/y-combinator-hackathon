"""LangChain/LangGraph integration using Runnable composition.

The intended integration is deliberately small:

    llm = wrap_llm(llm)
    lookup = wrap_tool(lookup)
    result = run_agent_rr(rr, payload, graph)

The wrappers intercept ``.invoke()`` through LangChain's Runnable surface.
They do not mutate or monkey-patch the original model/tool instance.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from flight_recorder.capture import (
    CapturedResponse,
    get_active_rr,
    get_current_parent_ids,
    set_current_parent_ids,
    capture_context,
)

from ._serialization import from_jsonable, to_jsonable


class _RunnableAdapter:
    """Dependency-free fallback for tests and demos without langchain_core."""

    def __init__(self, func: Callable[..., Any], name: str):
        self._func = func
        self.name = name

    def invoke(self, input: Any, config: Optional[dict] = None, **kwargs: Any) -> Any:
        return self._func(input, config=config, **kwargs)

    def __call__(self, input: Any, **kwargs: Any) -> Any:
        return self.invoke(input, **kwargs)


def wrap_llm(
    llm: Any,
    *,
    name: Optional[str] = None,
    include_config: bool = False,
    serializer: Callable[[Any], Any] = to_jsonable,
    deserializer: Callable[[Any], Any] = from_jsonable,
) -> Any:
    """Return a Runnable that records/replays ``llm.invoke(...)`` as an LLM call."""

    return _wrap_runnable(
        llm,
        event_type="llm_call",
        name=name,
        include_config=include_config,
        serializer=serializer,
        deserializer=deserializer,
    )


def wrap_tool(
    tool: Any,
    *,
    name: Optional[str] = None,
    include_config: bool = False,
    serializer: Callable[[Any], Any] = to_jsonable,
    deserializer: Callable[[Any], Any] = from_jsonable,
) -> Any:
    """Return a Runnable that records/replays ``tool.invoke(...)`` as a tool call."""

    return _wrap_runnable(
        tool,
        event_type="tool_call",
        name=name,
        include_config=include_config,
        serializer=serializer,
        deserializer=deserializer,
    )


def run_agent_rr(rr: Any, payload: Any, graph: Any) -> Any:
    """Run a LangGraph/Runnable/callable under an active Recorder/Replayer.

    This records the root input before graph execution, exposes ``rr`` to
    wrapped models/tools through contextvars, and records the final output on
    success. Context state is always reset, even when the graph raises.
    """

    root_id = rr.record_root_input(to_jsonable(payload))
    with capture_context(rr, [root_id]):
        result = _invoke_graph(graph, payload)
        rr.record_final_output(to_jsonable(result), get_current_parent_ids())
        return result


def _wrap_runnable(
    runnable: Any,
    *,
    event_type: str,
    name: Optional[str],
    include_config: bool,
    serializer: Callable[[Any], Any],
    deserializer: Callable[[Any], Any],
) -> Any:
    boundary_name = name or _infer_name(runnable)

    def invoke(input: Any, config: Optional[dict] = None, **kwargs: Any) -> Any:
        rr = get_active_rr()
        if rr is None:
            return _invoke_target(runnable, input, config=config, **kwargs)

        payload = {
            "input": serializer(input),
            "kwargs": serializer(kwargs),
        }
        if include_config:
            payload["config"] = serializer(config)

        parents = get_current_parent_ids()

        def call() -> CapturedResponse:
            raw = _invoke_target(runnable, input, config=config, **kwargs)
            return CapturedResponse(raw=raw, stored=serializer(raw))

        if event_type == "llm_call":
            response, event_id = rr.record_llm_call(boundary_name, payload, call, parents)
        elif event_type == "tool_call":
            response, event_id = rr.record_tool_call(boundary_name, payload, call, parents)
        else:
            raise ValueError(f"unsupported event_type {event_type!r}")

        set_current_parent_ids([event_id])
        return deserializer(response)

    return _make_runnable(invoke, name=f"agent_rr_{boundary_name}")


def _invoke_target(
    target: Any,
    input: Any,
    *,
    config: Optional[dict] = None,
    **kwargs: Any,
) -> Any:
    if hasattr(target, "invoke") and callable(target.invoke):
        return target.invoke(input, config=config, **kwargs)
    if callable(target):
        return target(input, **kwargs)
    raise TypeError(f"wrapped object {target!r} is not callable and has no .invoke()")


def _invoke_graph(graph: Any, payload: Any) -> Any:
    if hasattr(graph, "invoke") and callable(graph.invoke):
        return graph.invoke(payload)
    if callable(graph):
        return graph(payload)
    raise TypeError(f"graph {graph!r} is not callable and has no .invoke()")


def _make_runnable(func: Callable[..., Any], *, name: str) -> Any:
    try:
        from langchain_core.runnables import RunnableLambda
    except Exception:
        return _RunnableAdapter(func, name=name)

    try:
        return RunnableLambda(func, name=name)
    except TypeError:
        return RunnableLambda(func)


def _infer_name(obj: Any) -> str:
    for attr in ("name", "__name__"):
        value = getattr(obj, attr, None)
        if isinstance(value, str) and value:
            return value
    return type(obj).__name__
