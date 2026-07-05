"""OpenAI Python SDK integration.

Wrap an official SDK client once:

    client = wrap_openai(OpenAI())

Calls to ``client.responses.create(...)``, ``client.chat.completions.create(...)``
and ``client.embeddings.create(...)`` are recorded/replayed when an Agent-M²
capture context is active. Outside that context, calls pass through unchanged.

``stream=True`` calls are supported: chunks are buffered and aggregated
deterministically during record, and replay yields a synthetic chunk stream
rebuilt from the aggregate (see ``_streaming.py`` for the contract).
"""

from __future__ import annotations

from typing import Any, Callable

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

_OPENAI_CREATE_ENDPOINTS = {
    ("responses", "create"): "openai.responses.create",
    ("chat", "completions", "create"): "openai.chat.completions.create",
    ("embeddings", "create"): "openai.embeddings.create",
}


def wrap_openai(
    client: Any,
    *,
    serializer: Callable[[Any], Any] = to_jsonable,
    deserializer: Callable[[Any], Any] = from_jsonable,
) -> Any:
    """Return a proxy around an OpenAI SDK client."""

    return _OpenAIProxy(client, (), serializer, deserializer)


wrap_client = wrap_openai


class _OpenAIProxy:
    def __init__(
        self,
        target: Any,
        path: tuple[str, ...],
        serializer: Callable[[Any], Any],
        deserializer: Callable[[Any], Any],
    ):
        object.__setattr__(self, "_target", target)
        object.__setattr__(self, "_path", path)
        object.__setattr__(self, "_serializer", serializer)
        object.__setattr__(self, "_deserializer", deserializer)

    def __getattr__(self, name: str) -> Any:
        target_attr = getattr(self._target, name)
        path = self._path + (name,)
        endpoint = _OPENAI_CREATE_ENDPOINTS.get(path)
        if endpoint and callable(target_attr):
            return _capture_create(
                target_attr,
                endpoint,
                self._serializer,
                self._deserializer,
            )
        # Only wrap in a proxy if this path is a prefix of a captured endpoint
        if any(ep_path[:len(path)] == path for ep_path in _OPENAI_CREATE_ENDPOINTS):
            return _OpenAIProxy(target_attr, path, self._serializer, self._deserializer)
        return target_attr

    def __setattr__(self, name: str, value: Any) -> None:
        setattr(self._target, name, value)

    def __repr__(self) -> str:
        return f"<AgentM2OpenAIProxy target={self._target!r}>"


def _capture_create(
    create: Callable[..., Any],
    name: str,
    serializer: Callable[[Any], Any],
    deserializer: Callable[[Any], Any],
) -> Callable[..., Any]:
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        rr = get_active_rr()
        if rr is None:
            return create(*args, **kwargs)
        streaming = kwargs.get("stream") is True

        payload = {"args": serializer(args), "kwargs": serializer(kwargs)}
        parents = get_current_parent_ids()

        if streaming:
            def call() -> CapturedResponse:
                # Buffer-then-yield: the stream is fully consumed here so the
                # recorder writes one event; only the deterministic aggregate
                # is stored (chunk boundaries are network noise).
                raw_chunks = list(create(*args, **kwargs))
                stored = stream_response(
                    STREAM_KIND_OPENAI,
                    aggregate_openai_chunks(serializer(chunk) for chunk in raw_chunks),
                    len(raw_chunks),
                )
                return CapturedResponse(raw=ReplayableStream(raw_chunks), stored=stored)
        else:
            def call() -> CapturedResponse:
                raw = create(*args, **kwargs)
                return CapturedResponse(raw=raw, stored=serializer(raw))

        response, event_id = rr.record_llm_call(name, payload, call, parents)
        set_current_parent_ids([event_id])
        if isinstance(response, ReplayableStream):
            return response  # record path: the buffered original chunks
        if is_stream_response(response):
            # Replay path: rebuild an equivalent chunk stream from the aggregate.
            return ReplayableStream(synthesize_openai_chunks(response["aggregated"]))
        return deserializer(response)

    return wrapped
