"""Generic HTTP (requests) wrapper tests (P0 roadmap: Native Integrations).

Fake session/response objects mimic the ``requests`` surface — the real
library is never required.
"""

import base64
import json

import pytest

from flight_recorder.capture import capture_context, get_current_parent_ids
from flight_recorder.errors import ReplayDivergence
from flight_recorder.integrations.requests import (
    HTTP_RESPONSE_MARKER,
    REDACTED,
    HTTPStatusError,
    ReplayedHTTPResponse,
    wrap_requests,
)
from flight_recorder.recorder import Recorder
from flight_recorder.replayer import Replayer
from flight_recorder.storage import read_events

# raise_for_status raises the real requests.HTTPError when the library is
# installed, and the local HTTPStatusError otherwise.
try:
    from requests.exceptions import HTTPError as ExpectedHTTPError
except ImportError:
    ExpectedHTTPError = HTTPStatusError


class _FakeResponse:
    def __init__(self, *, status_code=200, body=None, text=None, content=None,
                 headers=None, url="https://api.example.com/x", reason="OK"):
        self.status_code = status_code
        self.reason = reason
        self.url = url
        self.headers = headers or {"Content-Type": "application/json"}
        self.encoding = "utf-8"
        self._body = body
        self._text = text
        self._content = content

    def json(self):
        if self._body is None:
            raise ValueError("no JSON body")
        return self._body

    @property
    def text(self):
        if self._text is not None:
            return self._text
        if self._body is not None:
            return json.dumps(self._body)
        raise ValueError("no text body")

    @property
    def content(self):
        if self._content is not None:
            return self._content
        return self.text.encode("utf-8")


class _FakeSession:
    def __init__(self, response=None, *, poison=False):
        self.poison = poison
        self.headers = {"Authorization": "Bearer secret-token", "User-Agent": "test"}
        self.response = response or _FakeResponse(body={"orders": [1, 2, 3]})
        self.calls = []

    def request(self, method, url, **kwargs):
        if self.poison:
            raise AssertionError("network must not be touched during replay")
        self.calls.append((method, url, kwargs))
        return self.response


def _run_agent(http, rr, *, url="https://api.example.com/orders"):
    root = rr.record_root_input({"q": "orders"})
    with capture_context(rr, [root]):
        response = http.get(url, params={"limit": 5}, timeout=10)
        data = response.json()
        rr.record_final_output({"count": len(data["orders"])}, get_current_parent_ids())
    return response


def test_record_then_replay_serves_recorded_response(tmp_path):
    trace = tmp_path / "trace.jsonl"

    session = _FakeSession()
    with Recorder("http", trace) as rr:
        live = _run_agent(wrap_requests(session), rr)
    assert live is session.response  # record path returns the live response
    assert session.calls == [
        ("GET", "https://api.example.com/orders", {"params": {"limit": 5}, "timeout": 10})
    ]

    with Replayer(trace) as rr:
        replayed = _run_agent(wrap_requests(_FakeSession(poison=True)), rr)
    assert isinstance(replayed, ReplayedHTTPResponse)
    assert replayed.status_code == 200
    assert replayed.ok
    assert replayed.json() == {"orders": [1, 2, 3]}
    assert "orders" in replayed.text
    assert replayed.content == replayed.text.encode("utf-8")


def test_recorded_event_shape_and_header_redaction(tmp_path):
    trace = tmp_path / "trace.jsonl"
    session = _FakeSession(
        _FakeResponse(body={"ok": True}, headers={"Set-Cookie": "sid=abc", "X-Rate": "9"})
    )
    with Recorder("http", trace) as rr:
        root = rr.record_root_input({"q": "x"})
        http = wrap_requests(session)
        with capture_context(rr, [root]):
            http.post(
                "https://api.example.com/create",
                json={"name": "Ada"},
                headers={"X-Api-Key": "call-secret"},
            )
            rr.record_final_output({"ok": True}, get_current_parent_ids())

    (event,) = [e for e in read_events(trace) if e.event_type == "tool_call"]
    assert event.name == "requests.request"
    assert event.payload["method"] == "POST"
    assert event.payload["url"] == "https://api.example.com/create"
    assert event.payload["json"] == {"name": "Ada"}
    # Session-level and call-level secrets are both redacted before hashing.
    assert event.payload["headers"]["Authorization"] == REDACTED
    assert event.payload["headers"]["X-Api-Key"] == REDACTED
    assert event.payload["headers"]["User-Agent"] == "test"
    assert event.latency_ms is not None

    stored = event.historical_response
    assert stored[HTTP_RESPONSE_MARKER] is True
    assert stored["status_code"] == 200
    assert stored["headers"]["Set-Cookie"] == REDACTED
    assert stored["headers"]["X-Rate"] == "9"
    assert stored["body"] == {"kind": "json", "value": {"ok": True}}


def test_replayed_500_raises_for_status(tmp_path):
    trace = tmp_path / "trace.jsonl"
    session = _FakeSession(
        _FakeResponse(status_code=500, reason="Internal Server Error", body={"error": "boom"})
    )
    with Recorder("http", trace) as rr:
        root = rr.record_root_input({"q": "x"})
        with capture_context(rr, [root]):
            wrap_requests(session).get("https://api.example.com/broken")
            rr.record_final_output({"ok": False}, get_current_parent_ids())

    with Replayer(trace) as rr:
        root = rr.record_root_input({"q": "x"})
        with capture_context(rr, [root]):
            response = wrap_requests(_FakeSession(poison=True)).get(
                "https://api.example.com/broken"
            )
            assert not response.ok
            with pytest.raises(ExpectedHTTPError, match="500 Server Error"):
                response.raise_for_status()
            rr.record_final_output({"ok": False}, get_current_parent_ids())


def test_divergence_on_changed_url(tmp_path):
    trace = tmp_path / "trace.jsonl"
    with Recorder("http", trace) as rr:
        _run_agent(wrap_requests(_FakeSession()), rr)

    with pytest.raises(ReplayDivergence):
        with Replayer(trace) as rr:
            _run_agent(
                wrap_requests(_FakeSession(poison=True)),
                rr,
                url="https://api.example.com/DIFFERENT",
            )


def test_binary_body_falls_back_to_base64(tmp_path):
    trace = tmp_path / "trace.jsonl"
    payload_bytes = bytes(range(8))

    class _BinaryResponse(_FakeResponse):
        def json(self):
            raise ValueError("not json")

        @property
        def text(self):
            raise ValueError("not text")

    session = _FakeSession(_BinaryResponse(content=payload_bytes, headers={}))
    with Recorder("http", trace) as rr:
        root = rr.record_root_input({"q": "bin"})
        with capture_context(rr, [root]):
            wrap_requests(session).post("https://api.example.com/blob", data=b"\x00\x01")
            rr.record_final_output({"ok": True}, get_current_parent_ids())

    (event,) = [e for e in read_events(trace) if e.event_type == "tool_call"]
    # Request bytes are stored as base64, never hashed raw.
    assert event.payload["data"] == {
        "kind": "base64",
        "value": base64.b64encode(b"\x00\x01").decode("ascii"),
    }
    assert event.historical_response["body"]["kind"] == "base64"

    with Replayer(trace) as rr:
        root = rr.record_root_input({"q": "bin"})
        with capture_context(rr, [root]):
            response = wrap_requests(_FakeSession(poison=True)).post(
                "https://api.example.com/blob", data=b"\x00\x01"
            )
            assert response.content == payload_bytes
            rr.record_final_output({"ok": True}, get_current_parent_ids())


def test_stream_download_refused(tmp_path):
    trace = tmp_path / "trace.jsonl"
    with Recorder("http", trace) as rr:
        root = rr.record_root_input({"q": "x"})
        with capture_context(rr, [root]):
            with pytest.raises(NotImplementedError, match="streamed downloads"):
                wrap_requests(_FakeSession()).get("https://x.example", stream=True)
            rr.record_final_output({"ok": True}, [root])


def test_passthrough_outside_capture_context():
    session = _FakeSession()
    http = wrap_requests(session)
    response = http.get("https://api.example.com/orders")
    assert response is session.response
    assert http.headers is session.headers  # non-verb attributes delegate
