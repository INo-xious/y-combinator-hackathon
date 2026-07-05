"""Anthropic Python SDK integration.

Wrap an official SDK client once:

    client = wrap_anthropic(Anthropic())

Calls to ``client.messages.create(...)`` are recorded/replayed when an
Agent-RR capture context is active. Outside that context, calls pass through.

``messages.create(stream=True)`` is supported: message events are buffered
and aggregated deterministically during record, and replay yields a synthetic
event stream rebuilt from the aggregate (see ``_streaming.py``). The
``messages.stream(...)`` context-manager helper is not captured yet.
"""

from __future__ import annotations

from typing import Any, Callable

from flight_recorder.capture import CapturedResponse, get_active_rr, get_current_parent_ids
from flight_recorder.capture import set_current_parent_ids

from ._serialization import from_jsonable, to_jsonable
from ._streaming import (
    STREAM_KIND_ANTHROPIC,
    ReplayableStream,
    aggregate_anthropic_events,
    is_stream_response,
    stream_response,
    synthesize_anthropic_events,
)

_ANTHROPIC_CREATE_ENDPOINTS = {
    ("messages", "create"): "anthropic.messages.create",
}
# TODO: capture the messages.stream(...) context-manager helper; until then
# it fails loudly inside a capture context instead of silently going live.
_ANTHROPIC_UNSUPPORTED_ENDPOINTS = {
    ("messages", "stream"): "anthropic.messages.stream",
}


def wrap_anthropic(
    client: Any,
    *,
    serializer: Callable[[Any], Any] = to_jsonable,
    deserializer: Callable[[Any], Any] = from_jsonable,
) -> Any:
    """Return a proxy around an Anthropic SDK client."""

    return _AnthropicProxy(client, (), serializer, deserializer)


wrap_client = wrap_anthropic


class _AnthropicProxy:
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
        endpoint = _ANTHROPIC_CREATE_ENDPOINTS.get(path)
        if endpoint and callable(target_attr):
            return _capture_create(
                target_attr,
                endpoint,
                self._serializer,
                self._deserializer,
            )
        unsupported = _ANTHROPIC_UNSUPPORTED_ENDPOINTS.get(path)
        if unsupported and callable(target_attr):
            return _refuse_in_capture_context(target_attr, unsupported)
        # Only wrap in a proxy if this path is a prefix of a captured endpoint
        if any(ep_path[:len(path)] == path for ep_path in _ANTHROPIC_CREATE_ENDPOINTS):
            return _AnthropicProxy(target_attr, path, self._serializer, self._deserializer)
        return target_attr

    def __setattr__(self, name: str, value: Any) -> None:
        setattr(self._target, name, value)

    def __repr__(self) -> str:
        return f"<AgentRRAnthropicProxy target={self._target!r}>"


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
                # Buffer-then-yield: the event stream is fully consumed here so
                # the recorder writes one event; only the deterministic
                # aggregate is stored (chunk boundaries are network noise).
                raw_events = list(create(*args, **kwargs))
                stored = stream_response(
                    STREAM_KIND_ANTHROPIC,
                    aggregate_anthropic_events(serializer(event) for event in raw_events),
                    len(raw_events),
                )
                return CapturedResponse(raw=ReplayableStream(raw_events), stored=stored)
        else:
            def call() -> CapturedResponse:
                raw = create(*args, **kwargs)
                return CapturedResponse(raw=raw, stored=serializer(raw))

        response, event_id = rr.record_llm_call(name, payload, call, parents)
        set_current_parent_ids([event_id])
        if isinstance(response, ReplayableStream):
            return response  # record path: the buffered original events
        if is_stream_response(response):
            # Replay path: rebuild an equivalent event stream from the aggregate.
            return ReplayableStream(synthesize_anthropic_events(response["aggregated"]))
        return deserializer(response)

    return wrapped


def _refuse_in_capture_context(target: Callable[..., Any], endpoint: str) -> Callable[..., Any]:
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        if get_active_rr() is None:
            return target(*args, **kwargs)
        raise NotImplementedError(
            f"Agent-RR does not capture {endpoint} yet; "
            "use messages.create(stream=True) instead"
        )

    return wrapped
