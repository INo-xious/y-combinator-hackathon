"""Tests for the agent-rr CLI: record, replay, validate."""

from __future__ import annotations

import json
import uuid

from flight_recorder.cli import main
from flight_recorder.recorder import Recorder
from flight_recorder.storage import read_events


DEMO_QUERY = "Look up customer 123 and summarize their last 5 orders."


def _json_stdout(capsys) -> dict:
    captured = capsys.readouterr()
    lines = captured.out.splitlines()
    assert len(lines) == 1
    return json.loads(lines[0])


def _record_cli_trace(trace_path, capsys) -> dict:
    rc = main(["record", str(trace_path)])
    assert rc == 0
    return _json_stdout(capsys)


def _record_different_query_trace(trace_path) -> None:
    with Recorder(agent_id="demo-agent", capture_to=trace_path) as recorder:
        root_id = recorder.record_root_input({"query": "Summarize customer 999."})
        plan, llm1_id = recorder.record_llm_call(
            "llm_plan",
            {"prompt": "plan", "temperature": 0},
            lambda: {"plan": ["lookup_customer", "fetch_orders"]},
            [root_id],
        )
        customer, tool1_id = recorder.record_tool_call(
            "lookup_customer",
            {"customer_id": 123},
            lambda: {"name": "Ada"},
            [llm1_id],
        )
        orders, tool2_id = recorder.record_tool_call(
            "fetch_orders",
            {"customer_id": 123, "limit": 5},
            lambda: {"orders": [1, 2, 3]},
            [llm1_id],
        )
        answer, llm2_id = recorder.record_llm_call(
            "llm_summary",
            {"prompt": "summarize"},
            lambda: {"answer": "3 recent orders"},
            [llm1_id, tool1_id, tool2_id],
        )
        recorder.record_final_output({"answer": "3 recent orders"}, [llm2_id])


def test_record_writes_demo_trace_and_success_json(tmp_path, capsys):
    trace_path = tmp_path / "trace.jsonl"

    payload = _record_cli_trace(trace_path, capsys)

    assert payload["status"] == "success"
    assert payload["trace_file"] == str(trace_path)
    assert payload["events_count"] == 7
    uuid.UUID(payload["run_id"])
    events = read_events(trace_path)
    assert len(events) == 7
    assert events[0].event_type == "metadata"
    assert events[-1].event_type == "final_output"


def test_record_refuses_existing_trace_without_overwrite(tmp_path, capsys):
    trace_path = tmp_path / "trace.jsonl"
    trace_path.write_text("keep me", encoding="utf-8")

    rc = main(["record", str(trace_path)])
    payload = _json_stdout(capsys)

    assert rc == 1
    assert payload == {
        "error_type": "FileExistsError",
        "reason": "file exists",
        "status": "error",
        "trace_file": str(trace_path),
    }
    assert trace_path.read_text(encoding="utf-8") == "keep me"


def test_record_overwrite_replaces_existing_trace(tmp_path, capsys):
    trace_path = tmp_path / "trace.jsonl"
    trace_path.write_text("old", encoding="utf-8")

    rc = main(["record", "--overwrite", str(trace_path)])
    payload = _json_stdout(capsys)

    assert rc == 0
    assert payload["status"] == "success"
    assert payload["events_count"] == 7
    assert len(read_events(trace_path)) == 7


def test_replay_matches_recorded_demo_trace(tmp_path, capsys):
    trace_path = tmp_path / "trace.jsonl"
    record_payload = _record_cli_trace(trace_path, capsys)

    rc = main(["replay", str(trace_path)])
    payload = _json_stdout(capsys)

    assert rc == 0
    assert payload == {
        "final_output_matched": True,
        "matched_events": 6,
        "run_id": record_payload["run_id"],
        "status": "success",
        "trace_file": str(trace_path),
    }


def test_replay_divergence_outputs_machine_readable_detail(tmp_path, capsys):
    trace_path = tmp_path / "different-query.jsonl"
    _record_different_query_trace(trace_path)

    rc = main(["replay", str(trace_path)])
    payload = _json_stdout(capsys)

    assert rc == 1
    assert payload["status"] == "divergence"
    assert payload["reason"] == "argument_hash mismatch"
    assert payload["trace_file"] == str(trace_path)
    assert payload["at_sequence_index"] == 1
    uuid.UUID(payload["at_event_id"])
    assert payload["expected"]["payload"] == {"query": "Summarize customer 999."}
    assert payload["actual"]["payload"] == {"query": DEMO_QUERY}


def test_replay_missing_file_returns_json_error(tmp_path, capsys):
    trace_path = tmp_path / "missing.jsonl"

    rc = main(["replay", str(trace_path)])
    payload = _json_stdout(capsys)

    assert rc == 1
    assert payload["status"] == "error"
    assert payload["error_type"] == "FileNotFoundError"
    assert payload["trace_file"] == str(trace_path)


def test_validate_valid_trace_verifies_hashes(tmp_path, capsys):
    trace_path = tmp_path / "trace.jsonl"
    _record_cli_trace(trace_path, capsys)

    rc = main(["validate", str(trace_path)])
    payload = _json_stdout(capsys)

    assert rc == 0
    assert payload == {
        "events": 7,
        "hashes_verified": True,
        "status": "valid",
        "trace_file": str(trace_path),
    }


def test_validate_corrupted_hash_returns_invalid_json(tmp_path, capsys):
    trace_path = tmp_path / "trace.jsonl"
    _record_cli_trace(trace_path, capsys)
    lines = trace_path.read_text(encoding="utf-8").splitlines()
    root_event = json.loads(lines[1])
    root_event["payload"] = {"query": "tampered"}
    lines[1] = json.dumps(root_event)
    trace_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    rc = main(["validate", str(trace_path)])
    payload = _json_stdout(capsys)

    assert rc == 1
    assert payload["status"] == "invalid"
    assert payload["trace_file"] == str(trace_path)
    assert any("argument_hash mismatch" in error for error in payload["errors"])


def test_no_args_returns_argparse_usage_code(capsys):
    rc = main([])

    captured = capsys.readouterr()
    assert rc == 2
    assert captured.out == ""
    assert "usage: agent-rr" in captured.err
