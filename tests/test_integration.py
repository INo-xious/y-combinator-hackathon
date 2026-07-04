"""End-to-end record/replay integration tests, divergence matrix, crash recovery."""

import uuid

import pytest

from flight_recorder.errors import (
    FinalOutputMismatch,
    FinalOutputNotCalled,
    LifecycleError,
    ReplayDivergence,
)
from flight_recorder.recorder import Recorder
from flight_recorder.replayer import Replayer, ReplayedError
from flight_recorder.storage import read_events


def poison_call():
    raise AssertionError("call() must not have been executed during replay")


class _SimulatedCrash(Exception):
    """Raised inside a Recorder context to simulate an agent crash: the
    exception exit skips the final-output assertion (PLAN §2) and leaves a
    valid partial trace on disk."""


def run_demo_agent(recorder, *, query="Look up customer 123 and summarize their last 5 orders."):
    """The PLAN §4 demo shape (7 events), against either a Recorder or Replayer."""
    root_id = recorder.record_root_input({"query": query})
    plan, llm1_id = recorder.record_llm_call(
        "llm_plan", {"prompt": "plan", "temperature": 0},
        lambda: {"plan": ["lookup_customer", "fetch_orders"]}, [root_id],
    )
    customer, tool1_id = recorder.record_tool_call(
        "lookup_customer", {"customer_id": 123}, lambda: {"name": "Ada"}, [llm1_id]
    )
    orders, tool2_id = recorder.record_tool_call(
        "fetch_orders", {"customer_id": 123, "limit": 5},
        lambda: {"orders": [1, 2, 3]}, [llm1_id],
    )
    answer, llm2_id = recorder.record_llm_call(
        "llm_summary", {"prompt": "summarize"},
        lambda: {"answer": "3 recent orders"}, [llm1_id, tool1_id, tool2_id],
    )
    final_id = recorder.record_final_output({"answer": "3 recent orders"}, [llm2_id])
    return {
        "root": root_id, "llm1": llm1_id, "tool1": tool1_id,
        "tool2": tool2_id, "llm2": llm2_id, "final": final_id,
    }


@pytest.fixture
def trace_path(tmp_path):
    return tmp_path / "trace.jsonl"


def record_demo(trace_path, **recorder_kwargs):
    with Recorder(agent_id="demo-agent", capture_to=trace_path, **recorder_kwargs) as rec:
        ids = run_demo_agent(rec)
    return ids


# --- Happy path ------------------------------------------------------------------


def test_replay_same_agent_matches_everything(trace_path):
    record_demo(trace_path)

    with Replayer(trace_file=trace_path) as replayer:
        ids = run_demo_agent(replayer)
        # record_final_output already ran inside run_demo_agent, so the
        # report reflects the comparison immediately (report.py contract:
        # None only until record_final_output runs).
        assert replayer.report.final_output_matched is True

    report = replayer.report
    assert report.clean
    assert len(report.matched_event_ids) == 6  # every non-metadata event
    assert report.unconsumed_event_ids == []
    assert report.divergence is None
    assert report.final_output_matched is True
    assert report.run_id == replayer.run_id
    assert ids["final"] == report.matched_event_ids[-1]


def test_replay_never_executes_call(trace_path):
    record_demo(trace_path)
    with Replayer(trace_file=trace_path) as replayer:
        root_id = replayer.record_root_input(
            {"query": "Look up customer 123 and summarize their last 5 orders."}
        )
        response, llm1_id = replayer.record_llm_call(
            "llm_plan", {"prompt": "plan", "temperature": 0}, poison_call, [root_id]
        )
        assert response == {"plan": ["lookup_customer", "fetch_orders"]}
        customer, tool1_id = replayer.record_tool_call(
            "lookup_customer", {"customer_id": 123}, poison_call, [llm1_id]
        )
        orders, tool2_id = replayer.record_tool_call(
            "fetch_orders", {"customer_id": 123, "limit": 5}, poison_call, [llm1_id]
        )
        answer, llm2_id = replayer.record_llm_call(
            "llm_summary", {"prompt": "summarize"}, poison_call,
            [llm1_id, tool1_id, tool2_id],
        )
        replayer.record_final_output({"answer": "3 recent orders"}, [llm2_id])


def test_replay_returns_historical_responses_not_fresh_ones(trace_path):
    record_demo(trace_path)
    with Replayer(trace_file=trace_path) as replayer:
        root_id = replayer.record_root_input(
            {"query": "Look up customer 123 and summarize their last 5 orders."}
        )
        response, llm1_id = replayer.record_llm_call(
            "llm_plan", {"prompt": "plan", "temperature": 0},
            lambda: {"plan": ["something else entirely"]}, [root_id],
        )
        # The historical response is returned, not whatever the lambda would produce.
        assert response == {"plan": ["lookup_customer", "fetch_orders"]}
        customer, tool1_id = replayer.record_tool_call(
            "lookup_customer", {"customer_id": 123}, poison_call, [llm1_id]
        )
        orders, tool2_id = replayer.record_tool_call(
            "fetch_orders", {"customer_id": 123, "limit": 5}, poison_call, [llm1_id]
        )
        answer, llm2_id = replayer.record_llm_call(
            "llm_summary", {"prompt": "summarize"}, poison_call,
            [llm1_id, tool1_id, tool2_id],
        )
        replayer.record_final_output({"answer": "3 recent orders"}, [llm2_id])


def test_replayer_run_id_matches_recorded_run(trace_path):
    with Recorder(agent_id="demo-agent", capture_to=trace_path) as rec:
        run_demo_agent(rec)
        recorded_run_id = rec.run_id
    with Replayer(trace_file=trace_path) as replayer:
        assert replayer.run_id == recorded_run_id
        run_demo_agent(replayer)


def test_duplicate_identical_calls_distinguished_by_sequence(trace_path):
    """A retried call has the same argument_hash both times; replay must
    reproduce error-then-success in sequence order, not conflate them
    (PLAN §8: status mismatch / duplicate identical calls by sequence)."""

    def fail_first():
        raise ValueError("first try")

    with Recorder(agent_id="demo-agent", capture_to=trace_path) as rec:
        root_id = rec.record_root_input({"q": 1})
        try:
            rec.record_tool_call("flaky", {"p": 1}, fail_first, [root_id])
        except ValueError:
            failed_id = read_events(trace_path)[-1].event_id
        _, retry_id = rec.record_tool_call("flaky", {"p": 1}, lambda: {"ok": True}, [failed_id])
        rec.record_final_output({"a": 1}, [retry_id])

    with Replayer(trace_file=trace_path) as replayer:
        root_id = replayer.record_root_input({"q": 1})
        with pytest.raises(ValueError, match="first try"):
            replayer.record_tool_call("flaky", {"p": 1}, poison_call, [root_id])
        failed_id = replayer.report.matched_event_ids[-1]
        response, retry_id = replayer.record_tool_call("flaky", {"p": 1}, poison_call, [failed_id])
        assert response == {"ok": True}
        replayer.record_final_output({"a": 1}, [retry_id])
    assert replayer.report.clean


# --- Divergence matrix ------------------------------------------------------------


def test_argument_mismatch_diverges(trace_path):
    record_demo(trace_path)
    with pytest.raises(ReplayDivergence, match="argument_hash mismatch"):
        with Replayer(trace_file=trace_path) as replayer:
            root_id = replayer.record_root_input(
                {"query": "Look up customer 123 and summarize their last 5 orders."}
            )
            # payload changed: name is the same, but the arguments differ.
            replayer.record_llm_call(
                "llm_plan", {"prompt": "a totally different plan", "temperature": 0},
                poison_call, [root_id],
            )


def test_name_mismatch_diverges(trace_path):
    record_demo(trace_path)
    with pytest.raises(ReplayDivergence, match="name mismatch"):
        with Replayer(trace_file=trace_path) as replayer:
            root_id = replayer.record_root_input(
                {"query": "Look up customer 123 and summarize their last 5 orders."}
            )
            replayer.record_llm_call(
                "llm_plan_renamed", {"prompt": "plan", "temperature": 0}, poison_call, [root_id]
            )


def test_parent_content_mismatch_diverges(trace_path):
    record_demo(trace_path)
    with pytest.raises(ReplayDivergence, match="parent_event_ids mismatch"):
        with Replayer(trace_file=trace_path) as replayer:
            root_id = replayer.record_root_input(
                {"query": "Look up customer 123 and summarize their last 5 orders."}
            )
            _, llm1_id = replayer.record_llm_call(
                "llm_plan", {"prompt": "plan", "temperature": 0}, poison_call, [root_id]
            )
            # lookup_customer's real parent is llm1, not root: a valid,
            # known event id, but the wrong one for this position.
            replayer.record_tool_call(
                "lookup_customer", {"customer_id": 123}, poison_call, [root_id]
            )


def test_parent_order_mismatch_diverges(trace_path):
    record_demo(trace_path)
    with pytest.raises(ReplayDivergence, match="parent_event_ids mismatch"):
        with Replayer(trace_file=trace_path) as replayer:
            root_id = replayer.record_root_input(
                {"query": "Look up customer 123 and summarize their last 5 orders."}
            )
            _, llm1_id = replayer.record_llm_call(
                "llm_plan", {"prompt": "plan", "temperature": 0}, poison_call, [root_id]
            )
            _, tool1_id = replayer.record_tool_call(
                "lookup_customer", {"customer_id": 123}, poison_call, [llm1_id]
            )
            _, tool2_id = replayer.record_tool_call(
                "fetch_orders", {"customer_id": 123, "limit": 5}, poison_call, [llm1_id]
            )
            # Real parent order is [llm1, tool1, tool2]; swap tool1/tool2.
            replayer.record_llm_call(
                "llm_summary", {"prompt": "summarize"}, poison_call,
                [llm1_id, tool2_id, tool1_id],
            )


def test_extra_call_exhausts_trace(trace_path):
    with pytest.raises(_SimulatedCrash):
        with Recorder(agent_id="demo-agent", capture_to=trace_path) as rec:
            root_id = rec.record_root_input({"q": 1})
            rec.record_llm_call("llm", {"p": 1}, lambda: {"r": 1}, [root_id])
            # Crash before final_output: a clean Recorder exit without it
            # would (correctly) raise FinalOutputNotCalled, so the short
            # trace must be produced via the exception exit path.
            raise _SimulatedCrash()

    with pytest.raises(ReplayDivergence, match="trace exhausted"):
        with Replayer(trace_file=trace_path) as replayer:
            root_id = replayer.record_root_input({"q": 1})
            _, llm_id = replayer.record_llm_call("llm", {"p": 1}, poison_call, [root_id])
            # Trace is fully consumed; one more call has nothing left to match.
            replayer.record_llm_call("extra", {"p": 2}, poison_call, [llm_id])


def test_missing_call_leaves_unconsumed_events_at_exit(trace_path):
    record_demo(trace_path)
    with pytest.raises(ReplayDivergence, match="unconsumed events at exit"):
        with Replayer(trace_file=trace_path) as replayer:
            root_id = replayer.record_root_input(
                {"query": "Look up customer 123 and summarize their last 5 orders."}
            )
            replayer.record_llm_call(
                "llm_plan", {"prompt": "plan", "temperature": 0}, poison_call, [root_id]
            )
            # Agent exits early: never calls the remaining tool/llm/final events.


def test_final_output_value_mismatch_raises_final_output_mismatch(trace_path):
    record_demo(trace_path)
    with pytest.raises(FinalOutputMismatch):
        with Replayer(trace_file=trace_path) as replayer:
            root_id = replayer.record_root_input(
                {"query": "Look up customer 123 and summarize their last 5 orders."}
            )
            _, llm1_id = replayer.record_llm_call(
                "llm_plan", {"prompt": "plan", "temperature": 0}, poison_call, [root_id]
            )
            _, tool1_id = replayer.record_tool_call(
                "lookup_customer", {"customer_id": 123}, poison_call, [llm1_id]
            )
            _, tool2_id = replayer.record_tool_call(
                "fetch_orders", {"customer_id": 123, "limit": 5}, poison_call, [llm1_id]
            )
            _, llm2_id = replayer.record_llm_call(
                "llm_summary", {"prompt": "summarize"}, poison_call,
                [llm1_id, tool1_id, tool2_id],
            )
            replayer.record_final_output({"answer": "a totally different answer"}, [llm2_id])
    assert replayer.report.final_output_matched is False


def test_final_output_mismatch_is_a_replay_divergence(trace_path):
    # FinalOutputMismatch must still be catchable via the parent class.
    record_demo(trace_path)
    with pytest.raises(ReplayDivergence):
        with Replayer(trace_file=trace_path) as replayer:
            root_id = replayer.record_root_input(
                {"query": "Look up customer 123 and summarize their last 5 orders."}
            )
            _, llm1_id = replayer.record_llm_call(
                "llm_plan", {"prompt": "plan", "temperature": 0}, poison_call, [root_id]
            )
            _, tool1_id = replayer.record_tool_call(
                "lookup_customer", {"customer_id": 123}, poison_call, [llm1_id]
            )
            _, tool2_id = replayer.record_tool_call(
                "fetch_orders", {"customer_id": 123, "limit": 5}, poison_call, [llm1_id]
            )
            _, llm2_id = replayer.record_llm_call(
                "llm_summary", {"prompt": "summarize"}, poison_call,
                [llm1_id, tool1_id, tool2_id],
            )
            replayer.record_final_output({"answer": "wrong"}, [llm2_id])


def test_custom_exception_replays_as_replayed_error(trace_path):
    class MyCustomError(RuntimeError):
        pass

    def raise_custom():
        raise MyCustomError("custom boom")

    with Recorder(agent_id="demo-agent", capture_to=trace_path) as rec:
        root_id = rec.record_root_input({"q": 1})
        try:
            rec.record_tool_call("flaky", {"p": 1}, raise_custom, [root_id])
        except MyCustomError:
            failed_id = read_events(trace_path)[-1].event_id
        _, llm_id = rec.record_llm_call("recover", {"p": 2}, lambda: {"r": 1}, [failed_id])
        rec.record_final_output({"a": 1}, [llm_id])

    with Replayer(trace_file=trace_path) as replayer:
        root_id = replayer.record_root_input({"q": 1})
        with pytest.raises(ReplayedError) as exc_info:
            replayer.record_tool_call("flaky", {"p": 1}, poison_call, [root_id])
        assert exc_info.value.original_type == "MyCustomError"
        assert exc_info.value.original_message == "custom boom"
        failed_id = replayer.report.matched_event_ids[-1]
        _, llm_id = replayer.record_llm_call("recover", {"p": 2}, poison_call, [failed_id])
        replayer.record_final_output({"a": 1}, [llm_id])


def test_builtin_exception_replays_as_itself_at_same_sequence(trace_path):
    def blow_up():
        raise KeyError("orders")

    with Recorder(agent_id="demo-agent", capture_to=trace_path) as rec:
        root_id = rec.record_root_input({"q": 1})
        try:
            rec.record_tool_call("fetch_orders", {"customer_id": 123}, blow_up, [root_id])
        except KeyError:
            failed_id = read_events(trace_path)[-1].event_id
        _, llm_id = rec.record_llm_call("recover", {"p": 2}, lambda: {"r": 1}, [failed_id])
        rec.record_final_output({"a": 1}, [llm_id])

    with Replayer(trace_file=trace_path) as replayer:
        root_id = replayer.record_root_input({"q": 1})
        with pytest.raises(KeyError, match="orders"):
            replayer.record_tool_call("fetch_orders", {"customer_id": 123}, poison_call, [root_id])
        failed_id = replayer.report.matched_event_ids[-1]
        _, llm_id = replayer.record_llm_call("recover", {"p": 2}, poison_call, [failed_id])
        replayer.record_final_output({"a": 1}, [llm_id])


# --- Redaction & parity ------------------------------------------------------------


def scrub_secrets(payload):
    if type(payload) is dict:
        return {k: "[REDACTED]" if k == "secret" else scrub_secrets(v) for k, v in payload.items()}
    return payload


def test_record_and_replay_with_same_redactor_passes(trace_path):
    with Recorder(agent_id="demo-agent", capture_to=trace_path, redactor=scrub_secrets) as rec:
        root_id = rec.record_root_input({"secret": "hunter2", "q": 1})
        _, llm_id = rec.record_llm_call(
            "llm", {"secret": "api-key", "p": 1}, lambda: {"secret": "resp-key", "r": 1}, [root_id]
        )
        rec.record_final_output({"secret": "out-key", "a": 1}, [llm_id])

    with Replayer(trace_file=trace_path, redactor=scrub_secrets) as replayer:
        root_id = replayer.record_root_input({"secret": "hunter2", "q": 1})
        response, llm_id = replayer.record_llm_call(
            "llm", {"secret": "api-key", "p": 1}, poison_call, [root_id]
        )
        assert response == {"secret": "[REDACTED]", "r": 1}
        replayer.record_final_output({"secret": "out-key", "a": 1}, [llm_id])
    assert replayer.report.clean


def test_replay_without_redactor_diverges_on_redacted_hashes(trace_path):
    with Recorder(agent_id="demo-agent", capture_to=trace_path, redactor=scrub_secrets) as rec:
        root_id = rec.record_root_input({"secret": "hunter2", "q": 1})
        _, llm_id = rec.record_llm_call(
            "llm", {"secret": "api-key", "p": 1}, lambda: {"secret": "resp-key", "r": 1}, [root_id]
        )
        rec.record_final_output({"secret": "out-key", "a": 1}, [llm_id])

    with pytest.raises(ReplayDivergence, match="argument_hash mismatch"):
        with Replayer(trace_file=trace_path) as replayer:  # no redactor this time
            root_id = replayer.record_root_input({"secret": "hunter2", "q": 1})
            replayer.record_llm_call(
                "llm", {"secret": "api-key", "p": 1}, poison_call, [root_id]
            )


def test_redacted_values_never_appear_on_disk(trace_path):
    with Recorder(agent_id="demo-agent", capture_to=trace_path, redactor=scrub_secrets) as rec:
        root_id = rec.record_root_input({"secret": "hunter2", "q": 1})
        _, llm_id = rec.record_llm_call(
            "llm", {"secret": "api-key", "p": 1}, lambda: {"secret": "resp-key", "r": 1}, [root_id]
        )
        rec.record_final_output({"secret": "out-key", "a": 1}, [llm_id])

    text = trace_path.read_text(encoding="utf-8")
    for raw in ("hunter2", "api-key", "resp-key", "out-key"):
        assert raw not in text


def test_replayer_redactor_output_must_be_strict_json(trace_path):
    with Recorder(agent_id="demo-agent", capture_to=trace_path) as rec:
        root_id = rec.record_root_input({"q": 1})
        _, llm_id = rec.record_llm_call("llm", {"p": 1}, lambda: {"r": 1}, [root_id])
        rec.record_final_output({"a": 1}, [llm_id])

    with pytest.raises(ValueError, match="bytes are not allowed"):
        with Replayer(trace_file=trace_path, redactor=lambda payload: b"oops") as replayer:
            replayer.record_root_input({"q": 1})


# --- Lifecycle -----------------------------------------------------------------


def test_boundary_call_before_root_input(trace_path):
    record_demo(trace_path)
    with pytest.raises(LifecycleError, match="record_llm_call called before record_root_input"):
        with Replayer(trace_file=trace_path) as replayer:
            replayer.record_llm_call("llm_plan", {"prompt": "plan", "temperature": 0}, poison_call, [])


def test_duplicate_root_input(trace_path):
    record_demo(trace_path)
    with pytest.raises(LifecycleError, match="record_root_input must be called exactly once"):
        with Replayer(trace_file=trace_path) as replayer:
            replayer.record_root_input(
                {"query": "Look up customer 123 and summarize their last 5 orders."}
            )
            replayer.record_root_input(
                {"query": "Look up customer 123 and summarize their last 5 orders."}
            )


def test_duplicate_final_output(trace_path):
    with Recorder(agent_id="demo-agent", capture_to=trace_path) as rec:
        root_id = rec.record_root_input({"q": 1})
        rec.record_final_output({"a": 1}, [root_id])

    with pytest.raises(LifecycleError, match="after record_final_output"):
        with Replayer(trace_file=trace_path) as replayer:
            root_id = replayer.record_root_input({"q": 1})
            replayer.record_final_output({"a": 1}, [root_id])
            replayer.record_final_output({"a": 1}, [root_id])


def test_call_after_final_output_rejected(trace_path):
    with Recorder(agent_id="demo-agent", capture_to=trace_path) as rec:
        root_id = rec.record_root_input({"q": 1})
        _, llm_id = rec.record_llm_call("llm", {"p": 1}, lambda: {"r": 1}, [root_id])
        rec.record_final_output({"a": 1}, [llm_id])

    with pytest.raises(LifecycleError, match="after record_final_output"):
        with Replayer(trace_file=trace_path) as replayer:
            root_id = replayer.record_root_input({"q": 1})
            _, llm_id = replayer.record_llm_call("llm", {"p": 1}, poison_call, [root_id])
            replayer.record_final_output({"a": 1}, [llm_id])
            replayer.record_llm_call("late", {"p": 2}, poison_call, [llm_id])


def test_exception_exit_propagates_unchanged(trace_path):
    record_demo(trace_path)

    class AgentBug(RuntimeError):
        pass

    with pytest.raises(AgentBug, match="agent logic exploded"):
        with Replayer(trace_file=trace_path) as replayer:
            root_id = replayer.record_root_input(
                {"query": "Look up customer 123 and summarize their last 5 orders."}
            )
            replayer.record_llm_call(
                "llm_plan", {"prompt": "plan", "temperature": 0}, poison_call, [root_id]
            )
            raise AgentBug("agent logic exploded")  # final-output assertion must be skipped


def test_calls_outside_context_rejected(trace_path):
    record_demo(trace_path)
    replayer = Replayer(trace_file=trace_path)
    with pytest.raises(LifecycleError, match="outside an active Replayer context"):
        replayer.record_root_input({"q": 1})


def test_calls_after_exit_rejected(trace_path):
    record_demo(trace_path)
    replayer = Replayer(trace_file=trace_path)
    with replayer:
        run_demo_agent(replayer)
    with pytest.raises(LifecycleError, match="after the Replayer context exited"):
        replayer.record_root_input({"q": 1})


def test_context_is_not_reentrant(trace_path):
    record_demo(trace_path)
    with Replayer(trace_file=trace_path) as replayer:
        with pytest.raises(LifecycleError, match="not reentrant"):
            replayer.__enter__()
        run_demo_agent(replayer)


def test_unknown_parent_rejected(trace_path):
    record_demo(trace_path)
    with pytest.raises(ValueError, match="unknown parent_event_id"):
        with Replayer(trace_file=trace_path) as replayer:
            replayer.record_root_input(
                {"query": "Look up customer 123 and summarize their last 5 orders."}
            )
            replayer.record_llm_call(
                "llm_plan", {"prompt": "plan", "temperature": 0}, poison_call, [str(uuid.uuid4())]
            )


def test_metadata_event_id_is_not_a_valid_parent(trace_path):
    with Recorder(agent_id="demo-agent", capture_to=trace_path) as rec:
        root_id = rec.record_root_input({"q": 1})
        rec.record_final_output({"a": 1}, [root_id])
    metadata_id = read_events(trace_path)[0].event_id

    with pytest.raises(ValueError, match="unknown parent_event_id"):
        with Replayer(trace_file=trace_path) as replayer:
            replayer.record_root_input({"q": 1})
            replayer.record_final_output({"a": 1}, [metadata_id])


def test_parent_ids_must_be_a_list(trace_path):
    record_demo(trace_path)
    with pytest.raises(ValueError, match="parent_event_ids must be a list"):
        with Replayer(trace_file=trace_path) as replayer:
            root_id = replayer.record_root_input(
                {"query": "Look up customer 123 and summarize their last 5 orders."}
            )
            replayer.record_llm_call(
                "llm_plan", {"prompt": "plan", "temperature": 0}, poison_call, root_id
            )


def test_call_must_be_callable(trace_path):
    record_demo(trace_path)
    with pytest.raises(TypeError, match="zero-argument callable"):
        with Replayer(trace_file=trace_path) as replayer:
            root_id = replayer.record_root_input(
                {"query": "Look up customer 123 and summarize their last 5 orders."}
            )
            replayer.record_llm_call(
                "llm_plan", {"prompt": "plan", "temperature": 0}, {"not": "callable"}, [root_id]
            )


def test_redactor_must_be_callable(trace_path):
    with pytest.raises(TypeError, match="redactor must be a callable"):
        Replayer(trace_file=trace_path, redactor="upper")


# --- Crash recovery --------------------------------------------------------------


def test_replay_of_trace_missing_final_output_fails_cleanly(trace_path):
    with pytest.raises(_SimulatedCrash):
        with Recorder(agent_id="demo-agent", capture_to=trace_path) as rec:
            root_id = rec.record_root_input({"q": 1})
            rec.record_llm_call("llm", {"p": 1}, lambda: {"r": 1}, [root_id])
            # Simulate a crash: no final_output ever recorded; the exception
            # exit (not a clean one) is what leaves this partial trace.
            raise _SimulatedCrash()

    with pytest.raises(FinalOutputNotCalled):
        with Replayer(trace_file=trace_path) as replayer:
            root_id = replayer.record_root_input({"q": 1})
            replayer.record_llm_call("llm", {"p": 1}, poison_call, [root_id])
            # The agent has nothing more to do per its own logic and exits
            # clean, but the recorded run never got a final_output either.


def test_replay_of_trace_with_truncated_final_line(trace_path):
    with Recorder(agent_id="demo-agent", capture_to=trace_path) as rec:
        root_id = rec.record_root_input({"q": 1})
        _, llm_id = rec.record_llm_call("llm", {"p": 1}, lambda: {"r": 1}, [root_id])
        rec.record_final_output({"a": 1}, [llm_id])

    # Corrupt the file: truncate mid-way through the final line.
    text = trace_path.read_text(encoding="utf-8")
    trace_path.write_text(text[: len(text) - 5], encoding="utf-8")

    with pytest.warns(UserWarning, match="incomplete"):
        with pytest.raises(FinalOutputNotCalled):
            with Replayer(trace_file=trace_path) as replayer:
                root_id = replayer.record_root_input({"q": 1})
                replayer.record_llm_call("llm", {"p": 1}, poison_call, [root_id])
                # final_output's line was dropped by the truncation; nothing
                # left to match, and record_final_output is never called.


def test_replay_of_trace_with_corrupt_middle_line_raises(trace_path):
    with Recorder(agent_id="demo-agent", capture_to=trace_path) as rec:
        root_id = rec.record_root_input({"q": 1})
        _, llm_id = rec.record_llm_call("llm", {"p": 1}, lambda: {"r": 1}, [root_id])
        rec.record_final_output({"a": 1}, [llm_id])

    lines = trace_path.read_text(encoding="utf-8").splitlines()
    lines[1] = "not valid json at all"
    trace_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="corrupt trace"):
        with Replayer(trace_file=trace_path):
            pass
