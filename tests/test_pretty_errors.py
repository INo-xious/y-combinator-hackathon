"""Tests for ReplayDivergence.pretty(): the human-first divergence format."""

from __future__ import annotations

import pytest

from flight_recorder.errors import ReplayDivergence
from flight_recorder.recorder import Recorder
from flight_recorder.replayer import Replayer


def _poison():
    raise AssertionError("call() must not run during replay")


@pytest.fixture()
def trace_path(tmp_path):
    path = tmp_path / "trace.jsonl"
    with Recorder(agent_id="demo-agent", capture_to=path) as recorder:
        root_id = recorder.record_root_input({"query": "book a flight"})
        plan, llm_id = recorder.record_llm_call(
            "llm_plan",
            {"prompt": "plan", "temperature": 0},
            lambda: {"plan": ["search_flights"]},
            [root_id],
        )
        flights, tool_id = recorder.record_tool_call(
            "search_flights",
            {"from": "London", "to": "Tokyo", "limit": 5},
            lambda: {"flights": [1, 2]},
            [llm_id],
        )
        recorder.record_final_output({"answer": "2 flights"}, [tool_id])
    return path


def _replay_until_divergence(trace_path, tool_payload):
    with Replayer(trace_file=trace_path) as replayer:
        root_id = replayer.record_root_input({"query": "book a flight"})
        plan, llm_id = replayer.record_llm_call(
            "llm_plan", {"prompt": "plan", "temperature": 0}, _poison, [root_id]
        )
        replayer.record_tool_call("search_flights", tool_payload, _poison, [llm_id])


def test_pretty_names_event_payloads_parent_and_cause(trace_path):
    with pytest.raises(ReplayDivergence) as excinfo:
        _replay_until_divergence(
            trace_path, {"from": "London", "to": "Tokyo", "limit": 10}
        )

    pretty = excinfo.value.pretty()
    lines = pretty.splitlines()
    assert lines[0] == "ReplayDivergence at tool_call_3: search_flights"
    assert lines[1] == 'Expected: {"from": "London", "limit": 5, "to": "Tokyo"}'
    assert lines[2] == 'Actual:   {"from": "London", "limit": 10, "to": "Tokyo"}'
    assert lines[3] == "Parent:   llm_call_2: llm_plan"
    assert lines[4] == (
        "Likely cause: Your agent changed the arguments it generates "
        "after llm_call_2: llm_plan."
    )


def test_pretty_reason_string_still_matchable(trace_path):
    """The compact reason keeps working for except-and-match callers."""
    with pytest.raises(ReplayDivergence, match="argument_hash mismatch"):
        _replay_until_divergence(
            trace_path, {"from": "London", "to": "Tokyo", "limit": 10}
        )


def test_pretty_without_detail_degrades_to_header():
    err = ReplayDivergence("trace exhausted")
    pretty = err.pretty()
    assert pretty.startswith("ReplayDivergence")
    assert "trace exhausted" in str(err)
    assert "Likely cause:" in pretty
