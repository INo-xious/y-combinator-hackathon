"""LiteLLM integration: one wrapper for every provider LiteLLM routes to.

LiteLLM exposes module-level functions (``litellm.completion(...)``) rather
than a client object, so this wrapper wraps callables, not attribute paths:

    import litellm
    from flight_recorder.integrations.litellm import wrap_litellm

    llm = wrap_litellm(litellm)      # or wrap_litellm() to import it lazily
    response = llm.completion(model="gpt-4o-mini", messages=[...])

Calls are recorded/replayed when an Agent-M² capture context is active and
pass through unchanged outside one. LiteLLM normalizes responses (and
streaming chunks) to the OpenAI format, so streaming reuses the OpenAI
chunk aggregation.

TODO: async ``acompletion`` and ``litellm.Router`` support.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from flight_recorder.capture import CapturedResponse, get_active_rr, get_current_parent_ids
from flight_recorder.capture import set_current_parent_ids

from ._serialization import from_jsonable, to_jsonable
from ._streaming import (
    STREAM_KIND_OPENAI,
    ReplayableStream,
    aggregate_openai_chunks,
    is_stream_response,
    stream_response,
    synthesize_openai_chunks,
)


def wrap_completion(
    completion: Optional[Callable[..., Any]] = None,
    *,
    name: str = "litellm.completion",
    serializer: Callable[[Any], Any] = to_jsonable,
    deserializer: Callable[[Any], Any] = from_jsonable,
) -> Callable[..., Any]:
    """Wrap ``litellm.completion`` (or a compatible callable) for record/replay."""
    if completion is None:
        import litellm  # deferred so the module imports without the dependency

        completion = litellm.completion
    return _capture_function(completion, name, serializer, deserializer)


def wrap_litellm(
    module: Any = None,
    *,
    serializer: Callable[[Any], Any] = to_jsonable,
    deserializer: Callable[[Any], Any] = from_jsonable,
) -> "_LiteLLMProxy":
    """Return a proxy over the ``litellm`` module with wrapped entry points."""
    if module is None:
        import litellm

        module = litellm
    return _LiteLLMProxy(module, serializer, deserializer)


wrap_client = wrap_litellm

_LITELLM_ENDPOINTS = {
    "completion": "litellm.completion",
    "embedding": "litellm.embedding",
}


class _LiteLLMProxy:
    def __init__(
        self,
        target: Any,
        serializer: Callable[[Any], Any],
        deserializer: Callable[[Any], Any],
    ):
        object.__setattr__(self, "_target", target)
        object.__setattr__(self, "_serializer", serializer)
        object.__setattr__(self, "_deserializer", deserializer)

    def __getattr__(self, name: str) -> Any:
        target_attr = getattr(self._target, name)
        endpoint = _LITELLM_ENDPOINTS.get(name)
        if endpoint and callable(target_attr):
            return _capture_function(
                target_attr, endpoint, self._serializer, self._deserializer
            )
        return target_attr

    def __setattr__(self, name: str, value: Any) -> None:
        setattr(self._target, name, value)

    def __repr__(self) -> str:
        return f"<AgentM2LiteLLMProxy target={self._target!r}>"


def _capture_function(
    func: Callable[..., Any],
    name: str,
    serializer: Callable[[Any], Any],
    deserializer: Callable[[Any], Any],
) -> Callable[..., Any]:
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        rr = get_active_rr()
        if rr is None:
            return func(*args, **kwargs)
        streaming = kwargs.get("stream") is True

        payload = {"args": serializer(args), "kwargs": serializer(kwargs)}
        parents = get_current_parent_ids()

        if streaming:
            def call() -> CapturedResponse:
                # LiteLLM chunks are OpenAI-format; same buffer-and-aggregate
                # contract as the OpenAI wrapper (_streaming.py).
                raw_chunks = list(func(*args, **kwargs))
                stored = stream_response(
                    STREAM_KIND_OPENAI,
                    aggregate_openai_chunks(serializer(chunk) for chunk in raw_chunks),
                    len(raw_chunks),
                )
                return CapturedResponse(raw=ReplayableStream(raw_chunks), stored=stored)
        else:
            def call() -> CapturedResponse:
                raw = func(*args, **kwargs)
                return CapturedResponse(raw=raw, stored=serializer(raw))

        response, event_id = rr.record_llm_call(name, payload, call, parents)
        set_current_parent_ids([event_id])
        if isinstance(response, ReplayableStream):
            return response
        if is_stream_response(response):
            return ReplayableStream(synthesize_openai_chunks(response["aggregated"]))
        return deserializer(response)

    return wrapped
