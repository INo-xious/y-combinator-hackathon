"""Generic HTTP integration: record/replay ``requests`` sessions.

Wrap a session once:

    import requests
    from flight_recorder.integrations.requests import wrap_requests

    http = wrap_requests(requests.Session())
    response = http.get("https://api.example.com/orders", timeout=10)

Inside an Agent-RR capture context, every request is recorded as a
``tool_call`` event — method, URL, params, headers (sensitive ones redacted
by default), body, response status/headers/body, and latency. During replay
the recorded response is served as a :class:`ReplayedHTTPResponse` and the
network is never touched (the Replayer never executes ``call``). Outside a
capture context, calls pass through unchanged.

Header hygiene: session-level and call-level headers are merged *before*
redaction, so a session-wide ``Authorization`` header never reaches a hash
or the trace file. Add your own names via ``redacted_headers=``.

TODO: ``stream=True`` downloads and ``iter_content`` on replayed responses.
"""

from __future__ import annotations

import base64
import json as _json
from typing import Any, Callable, Iterable, Mapping, Optional

from flight_recorder.capture import CapturedResponse, get_active_rr, get_current_parent_ids
from flight_recorder.capture import set_current_parent_ids
from flight_recorder.errors import FlightRecorderError

from ._serialization import to_jsonable

HTTP_RESPONSE_MARKER = "__agent_rr_http_response__"
REDACTED = "[REDACTED]"

DEFAULT_REDACTED_HEADERS = frozenset(
    {
        "authorization",
        "proxy-authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
        "api-key",
    }
)

_VERB_METHODS = ("get", "post", "put", "patch", "delete", "head", "options")
# Caller kwargs worth recording; the rest (cert, verify, hooks, ...) are
# transport configuration that never changes the logical exchange.
_RECORDED_KWARGS = ("params", "headers", "json", "data", "timeout")


class HTTPStatusError(FlightRecorderError):
    """4xx/5xx raised by a replayed response when ``requests`` is unavailable."""

    def __init__(self, message: str, response: "ReplayedHTTPResponse"):
        super().__init__(message)
        self.response = response


def wrap_requests(
    session: Any,
    *,
    redacted_headers: Iterable[str] = DEFAULT_REDACTED_HEADERS,
    serializer: Callable[[Any], Any] = to_jsonable,
) -> "_RequestsSessionProxy":
    """Return a proxy around a ``requests.Session``-like object."""
    return _RequestsSessionProxy(session, frozenset(h.lower() for h in redacted_headers), serializer)


wrap_client = wrap_requests


class _RequestsSessionProxy:
    def __init__(
        self,
        target: Any,
        redacted_headers: frozenset[str],
        serializer: Callable[[Any], Any],
    ):
        object.__setattr__(self, "_target", target)
        object.__setattr__(self, "_redacted_headers", redacted_headers)
        object.__setattr__(self, "_serializer", serializer)

    def __getattr__(self, name: str) -> Any:
        if name == "request":
            return self._capture_request
        if name in _VERB_METHODS:
            def verb(url: str, **kwargs: Any) -> Any:
                return self._capture_request(name.upper(), url, **kwargs)

            return verb
        return getattr(self._target, name)

    def __setattr__(self, name: str, value: Any) -> None:
        setattr(self._target, name, value)

    def __enter__(self) -> "_RequestsSessionProxy":
        self._target.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):
        return self._target.__exit__(exc_type, exc, tb)

    def __repr__(self) -> str:
        return f"<AgentRRRequestsProxy target={self._target!r}>"

    def _capture_request(self, method: str, url: str, **kwargs: Any) -> Any:
        rr = get_active_rr()
        if rr is None:
            return self._target.request(method, url, **kwargs)
        if kwargs.get("stream") is True:
            raise NotImplementedError(
                "Agent-RR requests wrapper does not capture streamed downloads yet"
            )

        payload = self._build_payload(method, url, kwargs)
        parents = get_current_parent_ids()

        def call() -> CapturedResponse:
            raw = self._target.request(method, url, **kwargs)
            return CapturedResponse(raw=raw, stored=self._store_response(raw))

        response, event_id = rr.record_tool_call("requests.request", payload, call, parents)
        set_current_parent_ids([event_id])
        if type(response) is dict and response.get(HTTP_RESPONSE_MARKER) is True:
            # Replay path: serve the recorded exchange, never the network.
            return ReplayedHTTPResponse(response)
        return response  # record path: the live requests.Response

    def _build_payload(self, method: str, url: str, kwargs: Mapping[str, Any]) -> dict:
        payload: dict[str, Any] = {"method": method.upper(), "url": url}
        merged_headers = dict(getattr(self._target, "headers", None) or {})
        merged_headers.update(kwargs.get("headers") or {})
        if merged_headers:
            payload["headers"] = self._redact(merged_headers)
        for key in _RECORDED_KWARGS:
            if key == "headers" or key not in kwargs:
                continue
            payload[key] = _body_to_jsonable(kwargs[key], self._serializer)
        return payload

    def _store_response(self, response: Any) -> dict:
        stored: dict[str, Any] = {
            HTTP_RESPONSE_MARKER: True,
            "status_code": response.status_code,
            "reason": getattr(response, "reason", None),
            "url": getattr(response, "url", None),
            "headers": self._redact(dict(getattr(response, "headers", None) or {})),
            "encoding": getattr(response, "encoding", None),
            "body": _store_body(response),
        }
        return stored

    def _redact(self, headers: dict) -> dict:
        return {
            str(key): (REDACTED if str(key).lower() in self._redacted_headers else str(value))
            for key, value in headers.items()
        }


def _body_to_jsonable(value: Any, serializer: Callable[[Any], Any]) -> Any:
    if type(value) in (bytes, bytearray):
        return {"kind": "base64", "value": base64.b64encode(bytes(value)).decode("ascii")}
    return serializer(value)


def _store_body(response: Any) -> dict:
    """Body as strict JSON: parsed JSON, else text, else base64 — bytes never
    reach a hash."""
    try:
        return {"kind": "json", "value": response.json()}
    except Exception:
        pass
    try:
        text = response.text
        if type(text) is str:
            return {"kind": "text", "value": text}
    except Exception:
        pass
    content = getattr(response, "content", b"") or b""
    return {"kind": "base64", "value": base64.b64encode(bytes(content)).decode("ascii")}


class ReplayedHTTPResponse:
    """A recorded HTTP exchange served during replay.

    Covers the commonly used surface of ``requests.Response``:
    ``status_code``, ``ok``, ``reason``, ``url``, ``headers``, ``encoding``,
    ``text``, ``content``, ``json()`` and ``raise_for_status()``.
    """

    def __init__(self, stored: Mapping[str, Any]):
        self.status_code: int = stored["status_code"]
        self.reason: Optional[str] = stored.get("reason")
        self.url: Optional[str] = stored.get("url")
        self.headers: dict = dict(stored.get("headers") or {})
        self.encoding: Optional[str] = stored.get("encoding")
        self._body: dict = dict(stored.get("body") or {"kind": "text", "value": ""})

    @property
    def ok(self) -> bool:
        return self.status_code < 400

    @property
    def text(self) -> str:
        kind, value = self._body["kind"], self._body["value"]
        if kind == "json":
            return _json.dumps(value, ensure_ascii=False)
        if kind == "text":
            return value
        return self.content.decode(self.encoding or "utf-8", errors="replace")

    @property
    def content(self) -> bytes:
        kind, value = self._body["kind"], self._body["value"]
        if kind == "base64":
            return base64.b64decode(value)
        return self.text.encode(self.encoding or "utf-8")

    def json(self, **kwargs: Any) -> Any:
        if self._body["kind"] == "json":
            return self._body["value"]
        return _json.loads(self.text, **kwargs)

    def raise_for_status(self) -> None:
        if self.status_code < 400:
            return
        side = "Client" if self.status_code < 500 else "Server"
        message = f"{self.status_code} {side} Error: {self.reason} for url: {self.url}"
        try:
            from requests.exceptions import HTTPError  # type: ignore[import-not-found]
        except Exception:
            raise HTTPStatusError(message, self)
        raise HTTPError(message, response=self)

    def __repr__(self) -> str:
        return f"<ReplayedHTTPResponse [{self.status_code}]>"
