"""OpenAI Python SDK integration.

Wrap an official SDK client once:

    client = wrap_openai(OpenAI())

Calls to ``client.responses.create(...)``, ``client.chat.completions.create(...)``
and ``client.embeddings.create(...)`` are recorded/replayed when an Agent-RR
capture context is active. Outside that context, calls pass through unchanged.
"""

from __future__ import annotations

from typing import Any, Callable

from flight_recorder.capture import CapturedResponse, get_active_rr, get_current_parent_ids
from flight_recorder.capture import set_current_parent_ids

from ._serialization import from_jsonable, to_jsonable

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
        return f"<AgentRROpenAIProxy target={self._target!r}>"


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
        if kwargs.get("stream") is True:
            raise NotImplementedError(
                "Agent-RR OpenAI wrapper does not capture streaming responses yet"
            )

        payload = {"args": serializer(args), "kwargs": serializer(kwargs)}
        parents = get_current_parent_ids()

        def call() -> CapturedResponse:
            raw = create(*args, **kwargs)
            return CapturedResponse(raw=raw, stored=serializer(raw))

        response, event_id = rr.record_llm_call(name, payload, call, parents)
        set_current_parent_ids([event_id])
        return deserializer(response)

    return wrapped
