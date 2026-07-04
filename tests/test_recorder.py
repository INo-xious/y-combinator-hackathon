"""Tests for the Recorder: lifecycle enforcement, flushing, error recording (PLAN §2)."""

import json
import uuid

import pytest

from flight_recorder.dag import validate_trace, verify_hashes
from flight_recorder.errors import FinalOutputNotCalled, LifecycleError
from flight_recorder.events import RECORDER_VERSION, SCHEMA_VERSION
from flight_recorder.hashing import argument_hash, context_hash
from flight_recorder.recorder import Recorder
from flight_recorder.storage import read_events


def poison_call():
    raise AssertionError("call() must not have been executed")


def record_demo_flow(path, **recorder_kwargs):
    """Record the PLAN §4 demo shape (7 events); return (recorder, ids dict)."""
    with Recorder(agent_id="demo-agent", capture_to=path, **recorder_kwargs) as rec:
        root_id = rec.record_root_input(
            {"query": "Look up customer 123 and summarize their last 5 orders."}
        )
        plan, llm1_id = rec.record_llm_call(
            "llm_plan", {"prompt": "plan", "temperature": 0},
            lambda: {"plan": ["lookup_customer", "fetch_orders"]}, [root_id],
        )
        customer, tool1_id = rec.record_tool_call(
            "lookup_customer", {"customer_id": 123}, lambda: {"name": "Ada"}, [llm1_id]
        )
        orders, tool2_id = rec.record_tool_call(
            "fetch_orders", {"customer_id": 123, "limit": 5},
            lambda: {"orders": [1, 2, 3]}, [llm1_id],
        )
        answer, llm2_id = rec.record_llm_call(
            "llm_summary", {"prompt": "summarize"},
            lambda: {"answer": "3 recent orders"}, [llm1_id, tool1_id, tool2_id],
        )
        final_id = rec.record_final_output({"answer": "3 recent orders"}, [llm2_id])
    ids = {
        "root": root_id, "llm1": llm1_id, "tool1": tool1_id,
        "tool2": tool2_id, "llm2": llm2_id, "final": final_id,
    }
    return rec, ids


@pytest.fixture
def trace_path(tmp_path):
    return tmp_path / "trace.jsonl"


# --- Happy path ------------------------------------------------------------------


def test_demo_flow_writes_complete_valid_trace(trace_path):
    record_demo_flow(trace_path)
    events = read_events(trace_path)
    assert len(events) == 7
    validate_trace(events, require_complete=True)
    verify_hashes(events)


def test_event_types_and_sequence_order(trace_path):
    record_demo_flow(trace_path)
    events = read_events(trace_path)
    assert [e.event_type for e in events] == [
        "metadata", "root_input", "llm_call", "tool_call",
        "tool_call", "llm_call", "final_output",
    ]
    assert [e.call_sequence_index for e in events] == list(range(7))


def test_metadata_event_written_on_enter(trace_path):
    with Recorder(agent_id="demo-agent", capture_to=trace_path) as rec:
        [metadata] = read_events(trace_path)  # already on disk before any record_* call
        assert metadata.event_type == "metadata"
        assert metadata.call_sequence_index == 0
        assert metadata.parent_event_ids == []
        assert metadata.status == "ok"
        assert metadata.argument_hash is None and metadata.context_hash is None
        assert metadata.payload == {
            "schema_version": SCHEMA_VERSION,
            "recorder_version": RECORDER_VERSION,
            "trace_creation_time": metadata.timestamp,
            "run_id": rec.run_id,
            "agent_id": "demo-agent",
        }
        root_id = rec.record_root_input({"q": 1})
        rec.record_final_output({"a": 1}, [root_id])


def test_run_id_shared_across_all_events(trace_path):
    rec, _ = record_demo_flow(trace_path)
    events = read_events(trace_path)
    assert {e.run_id for e in events} == {rec.run_id}
    uuid.UUID(rec.run_id)


def test_returned_event_ids_match_trace(trace_path):
    _, ids = record_demo_flow(trace_path)
    events = read_events(trace_path)
    assert [e.event_id for e in events[1:]] == [
        ids["root"], ids["llm1"], ids["tool1"], ids["tool2"], ids["llm2"], ids["final"]
    ]


def test_boundary_call_returns_raw_response(trace_path):
    marker = {"answer": ["identity", "preserved"]}
    with Recorder(agent_id="demo-agent", capture_to=trace_path) as rec:
        root_id = rec.record_root_input({"q": 1})
        response, event_id = rec.record_llm_call("llm", {"p": 1}, lambda: marker, [root_id])
        assert response is marker  # the agent gets the call's actual return value
        uuid.UUID(event_id)
        rec.record_final_output({"a": 1}, [event_id])


def test_parent_ids_recorded_in_caller_order(trace_path):
    _, ids = record_demo_flow(trace_path)
    events = read_events(trace_path)
    assert events[5].parent_event_ids == [ids["llm1"], ids["tool1"], ids["tool2"]]


def test_events_flushed_incrementally(trace_path):
    def lines_on_disk():
        return len(trace_path.read_text(encoding="utf-8").splitlines())

    with Recorder(agent_id="demo-agent", capture_to=trace_path) as rec:
        assert lines_on_disk() == 1
        root_id = rec.record_root_input({"q": 1})
        assert lines_on_disk() == 2
        _, llm_id = rec.record_llm_call("llm", {"p": 1}, lambda: {"r": 1}, [root_id])
        assert lines_on_disk() == 3
        rec.record_final_output({"a": 1}, [llm_id])
        assert lines_on_disk() == 4


def test_latency_recorded_on_boundary_events_only(trace_path):
    record_demo_flow(trace_path)
    events = read_events(trace_path)
    for event in events:
        if event.event_type in ("llm_call", "tool_call"):
            assert type(event.latency_ms) is int and event.latency_ms >= 0
        else:
            assert event.latency_ms is None


# --- File lifecycle ------------------------------------------------------------------


def test_existing_file_refused_without_overwrite(trace_path):
    trace_path.write_text("precious\n")
    with pytest.raises(FileExistsError):
        with Recorder(agent_id="demo-agent", capture_to=trace_path):
            pass
    assert trace_path.read_text() == "precious\n"


def test_overwrite_true_truncates_and_starts_fresh(trace_path):
    trace_path.write_text("old junk, not JSON\n")
    record_demo_flow(trace_path, overwrite=True)
    events = read_events(trace_path)
    assert len(events) == 7
    validate_trace(events, require_complete=True)


def test_capture_to_accepts_str_path(tmp_path):
    record_demo_flow(str(tmp_path / "trace.jsonl"))


# --- Lifecycle enforcement ---------------------------------------------------------


def test_boundary_call_before_root_input(trace_path):
    with pytest.raises(LifecycleError, match="record_llm_call called before record_root_input"):
        with Recorder(agent_id="demo-agent", capture_to=trace_path) as rec:
            rec.record_llm_call("llm", {"p": 1}, poison_call, [])


def test_tool_call_before_root_input(trace_path):
    with pytest.raises(LifecycleError, match="record_tool_call called before record_root_input"):
        with Recorder(agent_id="demo-agent", capture_to=trace_path) as rec:
            rec.record_tool_call("tool", {"p": 1}, poison_call, [])


def test_final_output_before_root_input(trace_path):
    with pytest.raises(LifecycleError, match="record_final_output called before record_root_input"):
        with Recorder(agent_id="demo-agent", capture_to=trace_path) as rec:
            rec.record_final_output({"a": 1}, [])


def test_duplicate_root_input(trace_path):
    with pytest.raises(LifecycleError, match="record_root_input must be called exactly once"):
        with Recorder(agent_id="demo-agent", capture_to=trace_path) as rec:
            rec.record_root_input({"q": 1})
            rec.record_root_input({"q": 2})


@pytest.mark.parametrize(
    "late_call",
    [
        pytest.param(lambda rec, ids: rec.record_root_input({"q": 2}), id="root-after-final"),
        pytest.param(
            lambda rec, ids: rec.record_llm_call("llm", {"p": 1}, poison_call, [ids["root"]]),
            id="llm-after-final",
        ),
        pytest.param(
            lambda rec, ids: rec.record_tool_call("tool", {"p": 1}, poison_call, [ids["root"]]),
            id="tool-after-final",
        ),
        pytest.param(
            lambda rec, ids: rec.record_final_output({"a": 2}, [ids["root"]]),
            id="duplicate-final",
        ),
    ],
)
def test_no_calls_of_any_kind_after_final_output(trace_path, late_call):
    with pytest.raises(LifecycleError, match="after record_final_output"):
        with Recorder(agent_id="demo-agent", capture_to=trace_path) as rec:
            ids = {"root": rec.record_root_input({"q": 1})}
            rec.record_final_output({"a": 1}, [ids["root"]])
            late_call(rec, ids)


def test_calls_outside_context_rejected(trace_path):
    rec = Recorder(agent_id="demo-agent", capture_to=trace_path)
    with pytest.raises(LifecycleError, match="outside an active Recorder context"):
        rec.record_root_input({"q": 1})


def test_calls_after_exit_rejected(trace_path):
    rec, ids = record_demo_flow(trace_path)
    with pytest.raises(LifecycleError, match="after the Recorder context exited"):
        rec.record_root_input({"q": 1})


def test_context_is_not_reentrant(trace_path):
    with Recorder(agent_id="demo-agent", capture_to=trace_path) as rec:
        with pytest.raises(LifecycleError, match="not reentrant"):
            rec.__enter__()
        root_id = rec.record_root_input({"q": 1})
        rec.record_final_output({"a": 1}, [root_id])


def test_clean_exit_without_final_output(trace_path):
    with pytest.raises(FinalOutputNotCalled):
        with Recorder(agent_id="demo-agent", capture_to=trace_path) as rec:
            rec.record_root_input({"q": 1})
    # The partial trace written before the failed assertion is intact.
    validate_trace(read_events(trace_path))


def test_exception_exit_propagates_unchanged(trace_path):
    class AgentBug(RuntimeError):
        pass

    with pytest.raises(AgentBug, match="agent logic exploded"):
        with Recorder(agent_id="demo-agent", capture_to=trace_path) as rec:
            root_id = rec.record_root_input({"q": 1})
            rec.record_llm_call("llm", {"p": 1}, lambda: {"r": 1}, [root_id])
            raise AgentBug("agent logic exploded")  # final-output assertion must be skipped

    events = read_events(trace_path)
    assert len(events) == 3
    validate_trace(events)  # partial trace is structurally valid line-by-line
    verify_hashes(events)


# --- Boundary call failure recording -----------------------------------------------


def test_failed_call_recorded_then_reraised(trace_path):
    with pytest.raises(KeyError, match="orders"):
        with Recorder(agent_id="demo-agent", capture_to=trace_path) as rec:
            root_id = rec.record_root_input({"q": 1})

            def blow_up():
                raise KeyError("orders")

            rec.record_tool_call("fetch_orders", {"customer_id": 123}, blow_up, [root_id])

    events = read_events(trace_path)
    failed = events[2]
    assert failed.event_type == "tool_call"
    assert failed.status == "error"
    assert failed.historical_response is None
    assert failed.error["type"] == "KeyError"
    assert failed.error["message"] == "'orders'"
    assert "KeyError" in failed.error["traceback"]
    assert type(failed.latency_ms) is int
    verify_hashes(events)


def test_agent_can_catch_error_and_continue(trace_path):
    with Recorder(agent_id="demo-agent", capture_to=trace_path) as rec:
        root_id = rec.record_root_input({"q": 1})

        def blow_up():
            raise ValueError("transient")

        try:
            rec.record_tool_call("flaky", {"p": 1}, blow_up, [root_id])
        except ValueError:
            failed_id = read_events(trace_path)[-1].event_id
        # The failed event has a context_hash, so it works as a parent.
        _, llm_id = rec.record_llm_call("recover", {"p": 2}, lambda: {"r": 1}, [failed_id])
        rec.record_final_output({"a": 1}, [llm_id])

    events = read_events(trace_path)
    assert [e.call_sequence_index for e in events] == list(range(5))
    validate_trace(events, require_complete=True)
    verify_hashes(events)


# --- Argument validation happens before call() executes ------------------------------


def test_invalid_payload_fails_before_call_and_writes_nothing(trace_path):
    with Recorder(agent_id="demo-agent", capture_to=trace_path) as rec:
        root_id = rec.record_root_input({"q": 1})
        with pytest.raises(ValueError, match="bytes are not allowed"):
            rec.record_llm_call("llm", {"blob": b"raw"}, poison_call, [root_id])
        assert len(read_events(trace_path)) == 2  # nothing written
        # Sequence numbering is unaffected by the rejected call.
        _, llm_id = rec.record_llm_call("llm", {"p": 1}, lambda: {"r": 1}, [root_id])
        rec.record_final_output({"a": 1}, [llm_id])
    events = read_events(trace_path)
    assert [e.call_sequence_index for e in events] == list(range(4))


def test_unknown_parent_fails_before_call_and_writes_nothing(trace_path):
    with pytest.raises(ValueError, match="unknown parent_event_id"):
        with Recorder(agent_id="demo-agent", capture_to=trace_path) as rec:
            rec.record_root_input({"q": 1})
            rec.record_llm_call("llm", {"p": 1}, poison_call, [str(uuid.uuid4())])
    assert len(read_events(trace_path)) == 2


def test_metadata_event_id_is_not_a_valid_parent(trace_path):
    with pytest.raises(ValueError, match="unknown parent_event_id"):
        with Recorder(agent_id="demo-agent", capture_to=trace_path) as rec:
            metadata_id = read_events(trace_path)[0].event_id
            rec.record_root_input({"q": 1})
            rec.record_llm_call("llm", {"p": 1}, poison_call, [metadata_id])


def test_parent_ids_must_be_a_list(trace_path):
    with pytest.raises(ValueError, match="parent_event_ids must be a list"):
        with Recorder(agent_id="demo-agent", capture_to=trace_path) as rec:
            root_id = rec.record_root_input({"q": 1})
            rec.record_llm_call("llm", {"p": 1}, poison_call, root_id)


def test_name_must_be_a_non_empty_string(trace_path):
    with pytest.raises(ValueError, match="name must be a non-empty string"):
        with Recorder(agent_id="demo-agent", capture_to=trace_path) as rec:
            root_id = rec.record_root_input({"q": 1})
            rec.record_llm_call("", {"p": 1}, poison_call, [root_id])


def test_call_must_be_callable(trace_path):
    with pytest.raises(TypeError, match="zero-argument callable"):
        with Recorder(agent_id="demo-agent", capture_to=trace_path) as rec:
            root_id = rec.record_root_input({"q": 1})
            rec.record_llm_call("llm", {"p": 1}, {"not": "callable"}, [root_id])


def test_invalid_root_payload_writes_nothing(trace_path):
    with pytest.raises(ValueError, match="non-string dict key"):
        with Recorder(agent_id="demo-agent", capture_to=trace_path) as rec:
            rec.record_root_input({1: "x"})
    assert len(read_events(trace_path)) == 1  # metadata only


# --- Constructor validation ------------------------------------------------------


def test_agent_id_must_be_non_empty_string(trace_path):
    with pytest.raises(ValueError, match="agent_id must be a non-empty string"):
        Recorder(agent_id="", capture_to=trace_path)


def test_redactor_must_be_callable(trace_path):
    with pytest.raises(TypeError, match="redactor must be a callable"):
        Recorder(agent_id="demo-agent", capture_to=trace_path, redactor="upper")


# --- Redaction --------------------------------------------------------------------


def scrub_secrets(payload):
    if type(payload) is dict:
        return {k: "[REDACTED]" if k == "secret" else scrub_secrets(v) for k, v in payload.items()}
    return payload


def test_redactor_applied_before_storage_and_hashing(trace_path):
    raw_response = {"secret": "resp-token-xyz", "data": 2}
    with Recorder(agent_id="demo-agent", capture_to=trace_path, redactor=scrub_secrets) as rec:
        root_id = rec.record_root_input({"secret": "hunter2", "q": 1})
        response, llm_id = rec.record_llm_call(
            "llm", {"secret": "api-key-abc", "p": 1}, lambda: raw_response, [root_id]
        )
        assert response is raw_response  # agent still sees the raw response
        rec.record_final_output({"secret": "out-token", "a": 1}, [llm_id])

    text = trace_path.read_text(encoding="utf-8")
    for raw in ("hunter2", "api-key-abc", "resp-token-xyz", "out-token"):
        assert raw not in text  # raw values never touch disk

    events = read_events(trace_path)
    root, llm, final = events[1], events[2], events[3]
    assert root.payload == {"secret": "[REDACTED]", "q": 1}
    assert llm.payload == {"secret": "[REDACTED]", "p": 1}
    assert llm.historical_response == {"secret": "[REDACTED]", "data": 2}
    assert final.payload == {"secret": "[REDACTED]", "a": 1}
    # Hashes were computed over redacted values: stored hashes verify as-is.
    assert llm.argument_hash == argument_hash("llm_call", "llm", llm.payload)
    verify_hashes(events)


def test_redactor_applied_to_failed_boundary_payload(trace_path):
    with pytest.raises(RuntimeError, match="tool failed"):
        with Recorder(agent_id="demo-agent", capture_to=trace_path, redactor=scrub_secrets) as rec:
            root_id = rec.record_root_input({"q": 1})

            def fail_without_secret_in_message():
                raise RuntimeError("tool failed")

            rec.record_tool_call(
                "lookup",
                {"secret": "request-token-123", "customer_id": 123},
                fail_without_secret_in_message,
                [root_id],
            )

    text = trace_path.read_text(encoding="utf-8")
    assert "request-token-123" not in text

    failed = read_events(trace_path)[2]
    assert failed.status == "error"
    assert failed.historical_response is None
    assert failed.payload == {"secret": "[REDACTED]", "customer_id": 123}
    assert failed.argument_hash == argument_hash("tool_call", "lookup", failed.payload)
    verify_hashes(read_events(trace_path))


def test_redactor_not_applied_to_metadata_payload(trace_path):
    calls = []

    def counting_redactor(payload):
        calls.append(payload)
        return payload

    with Recorder(agent_id="demo-agent", capture_to=trace_path, redactor=counting_redactor) as rec:
        root_id = rec.record_root_input({"q": 1})
        _, llm_id = rec.record_llm_call("llm", {"p": 1}, lambda: {"r": 1}, [root_id])
        rec.record_final_output({"a": 1}, [llm_id])

    # root payload + llm payload + llm response + final value; never metadata.
    assert calls == [{"q": 1}, {"p": 1}, {"r": 1}, {"a": 1}]


def test_redactor_producing_invalid_json_fails_before_call(trace_path):
    with pytest.raises(ValueError, match="bytes are not allowed"):
        with Recorder(agent_id="demo-agent", capture_to=trace_path, redactor=lambda p: b"oops") as rec:
            rec.record_root_input({"q": 1})
    assert len(read_events(trace_path)) == 1  # metadata only


# --- Hash chaining ------------------------------------------------------------------


def test_context_hashes_chain_parents_in_order(trace_path):
    _, ids = record_demo_flow(trace_path)
    events = {e.event_id: e for e in read_events(trace_path)}
    llm2 = events[ids["llm2"]]
    expected = context_hash(
        [events[ids[k]].context_hash for k in ("llm1", "tool1", "tool2")],
        "llm_call",
        "llm_summary",
        llm2.payload,
        llm2.historical_response,
        "ok",
        None,
    )
    assert llm2.context_hash == expected
