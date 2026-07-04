"""Tests for JSONL storage: append, flush, partial-line recovery (PLAN §2, §8)."""

import dataclasses
import json
import warnings

import pytest

from conftest import make_trace
from flight_recorder.storage import TraceWriter, TruncatedTraceWarning, read_events


@pytest.fixture
def trace():
    return make_trace()


@pytest.fixture
def trace_path(tmp_path, trace):
    path = tmp_path / "trace.jsonl"
    with TraceWriter(path) as writer:
        for event in trace:
            writer.append(event)
    return path


# --- Writing -----------------------------------------------------------------


def test_append_writes_one_json_line_per_event(trace_path, trace):
    lines = trace_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == len(trace)
    for line, event in zip(lines, trace):
        assert json.loads(line)["event_id"] == event.event_id


def test_file_ends_with_newline(trace_path):
    assert trace_path.read_text(encoding="utf-8").endswith("\n")


def test_append_flushes_each_event_immediately(tmp_path, trace):
    path = tmp_path / "trace.jsonl"
    writer = TraceWriter(path)
    try:
        for count, event in enumerate(trace, start=1):
            writer.append(event)
            # Visible on disk without close(): flushed per event.
            assert len(path.read_text(encoding="utf-8").splitlines()) == count
    finally:
        writer.close()


def test_writer_refuses_existing_file(tmp_path):
    path = tmp_path / "trace.jsonl"
    path.write_text("existing\n")
    with pytest.raises(FileExistsError):
        TraceWriter(path)
    assert path.read_text() == "existing\n"


def test_writer_overwrite_truncates(tmp_path, trace):
    path = tmp_path / "trace.jsonl"
    path.write_text("junk that is not JSON\n")
    with TraceWriter(path, overwrite=True) as writer:
        writer.append(trace[0])
    assert read_events(path) == [trace[0]]


def test_append_rejects_invalid_event_and_writes_nothing(tmp_path, trace):
    path = tmp_path / "trace.jsonl"
    with TraceWriter(path) as writer:
        writer.append(trace[0])
        bad = dataclasses.replace(trace[1], agent_id="")
        with pytest.raises(ValueError, match="agent_id must be a non-empty string"):
            writer.append(bad)
    assert len(path.read_text(encoding="utf-8").splitlines()) == 1


# --- Reading -----------------------------------------------------------------


def test_round_trip_preserves_events(trace_path, trace):
    assert read_events(trace_path) == trace


def test_read_empty_file_returns_no_events(tmp_path):
    path = tmp_path / "empty.jsonl"
    path.touch()
    assert read_events(path) == []


def test_read_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_events(tmp_path / "missing.jsonl")


def test_read_without_trailing_newline_is_not_truncation(trace_path, trace):
    text = trace_path.read_text(encoding="utf-8")
    trace_path.write_text(text.rstrip("\n"), encoding="utf-8")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert read_events(trace_path) == trace


def test_truncated_final_line_warns_and_returns_prior_events(trace_path, trace):
    text = trace_path.read_text(encoding="utf-8")
    trace_path.write_text(text[:-20], encoding="utf-8")  # cut into the last line
    with pytest.warns(TruncatedTraceWarning, match="crash-interrupted write"):
        events = read_events(trace_path)
    assert events == trace[:-1]


def test_corrupt_middle_line_raises(trace_path):
    lines = trace_path.read_text(encoding="utf-8").splitlines()
    lines[2] = '{"event_id": '
    trace_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="line 3 is not valid JSON"):
        read_events(trace_path)


def test_blank_middle_line_raises(trace_path):
    lines = trace_path.read_text(encoding="utf-8").splitlines()
    lines.insert(2, "")
    trace_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="line 3 is not valid JSON"):
        read_events(trace_path)


def test_invalid_event_line_raises_with_line_number(trace_path):
    lines = trace_path.read_text(encoding="utf-8").splitlines()
    data = json.loads(lines[1])
    del data["status"]
    lines[1] = json.dumps(data)
    trace_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="line 2: invalid event: missing fields: status"):
        read_events(trace_path)


def test_invalid_final_event_line_is_corruption_not_truncation(trace_path):
    # A final line that parses as JSON but is not a valid event is corruption:
    # truncation produces unparseable JSON, never a parseable-but-wrong event.
    lines = trace_path.read_text(encoding="utf-8").splitlines()
    lines[-1] = '{"not": "an event"}'
    trace_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="line 5"):
        read_events(trace_path)
