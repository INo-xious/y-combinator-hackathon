"""TopologicalReplayer engine tests: topological matching, the withhold gate,
divergence taxonomy, and lifecycle parity (DESIGN-SESSION-4 §3, §5).

The "local mock agent" in withhold tests deliberately reads event ids from
the parsed trace (out-of-band knowledge, simulating a scheduler-driven
consumer) — through the honest API an agent cannot name an unconsumed
parent, which is exactly why the withhold gate exists (design premise 4).
"""

import json
import uuid

import pytest

from conftest import make_event, make_metadata
from flight_recorder.errors import (
    FinalOutputMismatch,
    FinalOutputNotCalled,
    LifecycleError,
    PrematureEventError,
    ReplayDivergence,
)
from flight_recorder.recorder import Recorder
from flight_recorder.replayer import Replayer, TopologicalReplayer
from flight_recorder.storage import TraceWriter


def poison_call():
    raise AssertionError("call() must not have been executed during replay")


def write_trace(path, events):
    with TraceWriter(path) as writer:
        for event in events:
            writer.append(event)
    return path


def fanout_events():
    """metadata -> root -> llm -> {alpha, beta} -> final; alpha ⊥ beta."""
    meta = make_metadata()
    root = make_event(meta, 1, "root_input", payload={"q": 1})
    llm = make_event(meta, 2, "llm_call", name="plan", payload={"p": 0},
                     parents=[root], historical_response={"r": 0})
    alpha = make_event(meta, 3, "tool_call", name="alpha", payload={"a": 1},
                       parents=[llm], historical_response={"ra": 1})
    beta = make_event(meta, 4, "tool_call", name="beta", payload={"b": 2},
                      parents=[llm], historical_response={"rb": 2})
    final = make_event(meta, 5, "final_output", payload={"answer": "done"},
                       parents=[alpha, beta])
    return [meta, root, llm, alpha, beta, final]


@pytest.fixture
def fanout(tmp_path):
    events = fanout_events()
    return write_trace(tmp_path / "trace.jsonl", events), events


def run_fanout_agent(replayer, *, beta_first=False):
    """The honest agent for the fanout trace; ids flow only from returns."""
    root_id = replayer.record_root_input({"q": 1})
    plan, llm_id = replayer.record_llm_call("plan", {"p": 0}, poison_call, [root_id])
    if beta_first:
        rb, beta_id = replayer.record_tool_call("beta", {"b": 2}, poison_call, [llm_id])
        ra, alpha_id = replayer.record_tool_call("alpha", {"a": 1}, poison_call, [llm_id])
    else:
        ra, alpha_id = replayer.record_tool_call("alpha", {"a": 1}, poison_call, [llm_id])
        rb, beta_id = replayer.record_tool_call("beta", {"b": 2}, poison_call, [llm_id])
    # Recorded final parents are [alpha, beta] regardless of call order.
    final_id = replayer.record_final_output({"answer": "done"}, [alpha_id, beta_id])
    return {"plan": plan, "ra": ra, "rb": rb, "final": final_id}


# --- happy path: recorded order is one valid topological order --------------------


def test_in_order_replay_matches_everything(fanout):
    path, events = fanout
    with TopologicalReplayer(trace_file=path) as replayer:
        out = run_fanout_agent(replayer)
        assert out["plan"] == {"r": 0}
        assert out["ra"] == {"ra": 1}
        assert out["rb"] == {"rb": 2}

    report = replayer.report
    assert report.clean
    assert report.matched_event_ids == [e.event_id for e in events[1:]]
    assert report.unconsumed_event_ids == []
    assert report.final_output_matched is True
    assert report.run_id == events[0].run_id


# --- the new capability: any valid topological order replays clean ----------------


def test_reordered_independent_siblings_replay_clean(fanout):
    path, events = fanout
    meta, root, llm, alpha, beta, final = events
    with TopologicalReplayer(trace_file=path) as replayer:
        out = run_fanout_agent(replayer, beta_first=True)
        # Historical responses land with the right call despite reordering.
        assert out["ra"] == {"ra": 1}
        assert out["rb"] == {"rb": 2}

    report = replayer.report
    assert report.clean
    # matched order is consumption order — a topological linear extension,
    # not the recorded sequence.
    assert report.matched_event_ids == [
        root.event_id, llm.event_id, beta.event_id, alpha.event_id, final.event_id
    ]


def test_sequence_mode_rejects_the_same_reordering(fanout):
    path, _ = fanout
    with pytest.raises(ReplayDivergence):
        with Replayer(trace_file=path) as replayer:
            run_fanout_agent(replayer, beta_first=True)


# --- lifecycle parity (inherited seam) ---------------------------------------------


def test_boundary_call_before_root_input_raises(fanout):
    path, _ = fanout
    with TopologicalReplayer(trace_file=path) as replayer:
        with pytest.raises(LifecycleError, match="before record_root_input"):
            replayer.record_llm_call("plan", {"p": 0}, poison_call, [])
        run_fanout_agent(replayer)  # leave the context clean


# --- the withhold gate (headline requirement) --------------------------------------
# These mock agents read event ids from the parsed trace — out-of-band
# knowledge a scheduler-driven consumer would have (design premise 4).


def diamond_events():
    """metadata -> root -> {a, b} -> c -> final; c needs both a and b."""
    meta = make_metadata()
    root = make_event(meta, 1, "root_input", payload={"q": 1})
    a = make_event(meta, 2, "tool_call", name="a", payload={"p": 1},
                   parents=[root], historical_response={"r": 1})
    b = make_event(meta, 3, "tool_call", name="b", payload={"p": 2},
                   parents=[root], historical_response={"r": 2})
    c = make_event(meta, 4, "llm_call", name="c", payload={"p": 3},
                   parents=[a, b], historical_response={"r": 3})
    final = make_event(meta, 5, "final_output", payload={"answer": 3}, parents=[c])
    return [meta, root, a, b, c, final]


def test_child_completed_too_early_is_withheld(tmp_path):
    events = diamond_events()
    meta, root, a, b, c, final = events
    path = write_trace(tmp_path / "t.jsonl", events)

    with pytest.raises(PrematureEventError) as excinfo:
        with TopologicalReplayer(trace_file=path) as replayer:
            replayer.record_root_input({"q": 1})
            replayer.record_tool_call("a", {"p": 1}, poison_call, [root.event_id])
            # Too early: c's recorded parents are correct, but b is unconsumed.
            replayer.record_llm_call(
                "c", {"p": 3}, poison_call, [a.event_id, b.event_id]
            )

    err = excinfo.value
    assert isinstance(err, ReplayDivergence)  # catchable with the Session-3 net
    assert "withheld" in err.reason
    assert err.missing_parent_ids == [b.event_id]
    assert err.ready_event_ids == [b.event_id]  # what the agent may legally do now
    assert err.at_event_id == c.event_id
    assert err.at_sequence_index == c.call_sequence_index
    detail = err.detail()
    assert detail["missing_parent_ids"] == [b.event_id]
    assert detail["ready_event_ids"] == [b.event_id]
    # The report captured the withhold as this run's divergence.
    assert replayer.report.divergence["reason"] == "response withheld: parents not consumed"
    # b was never consumed: the response really was withheld, not delivered.
    assert b.event_id in replayer.report.unconsumed_event_ids


def test_withhold_is_about_immediate_parents_only(tmp_path):
    """Grandparent consumed, parent pending: missing lists the parent only."""
    meta = make_metadata()
    root = make_event(meta, 1, "root_input", payload={"q": 1})
    a = make_event(meta, 2, "tool_call", name="a", payload={"p": 1},
                   parents=[root], historical_response={"r": 1})
    b = make_event(meta, 3, "tool_call", name="b", payload={"p": 2},
                   parents=[a], historical_response={"r": 2})
    final = make_event(meta, 4, "final_output", payload={"answer": 2}, parents=[b])
    path = write_trace(tmp_path / "t.jsonl", [meta, root, a, b, final])

    with pytest.raises(PrematureEventError) as excinfo:
        with TopologicalReplayer(trace_file=path) as replayer:
            replayer.record_root_input({"q": 1})  # grandparent consumed
            replayer.record_tool_call("b", {"p": 2}, poison_call, [a.event_id])

    assert excinfo.value.missing_parent_ids == [a.event_id]


def test_premature_final_output_is_withheld(fanout):
    path, events = fanout
    meta, root, llm, alpha, beta, final = events

    with pytest.raises(PrematureEventError) as excinfo:
        with TopologicalReplayer(trace_file=path) as replayer:
            root_id = replayer.record_root_input({"q": 1})
            _, llm_id = replayer.record_llm_call("plan", {"p": 0}, poison_call, [root_id])
            _, alpha_id = replayer.record_tool_call("alpha", {"a": 1}, poison_call, [llm_id])
            # Skips beta, then claims to be done (beta's id peeked from the trace).
            replayer.record_final_output({"answer": "done"}, [alpha_id, beta.event_id])

    err = excinfo.value
    assert err.reason == (
        "response withheld: final_output requested while events remain unconsumed"
    )
    # final's prerequisite under strict replay is every other recorded event.
    assert err.missing_parent_ids == [beta.event_id]
    assert replayer.report.final_output_matched is False


def test_premature_error_event_is_withheld_not_reraised(tmp_path):
    """A premature request for a status=error event withholds; ready re-raises."""
    meta = make_metadata()
    root = make_event(meta, 1, "root_input", payload={"q": 1})
    a = make_event(meta, 2, "tool_call", name="a", payload={"p": 1},
                   parents=[root], historical_response={"r": 1})
    boom = make_event(meta, 3, "tool_call", name="boom", payload={"p": 2},
                      parents=[a], status="error",
                      error={"type": "KeyError", "message": "'orders'"})
    final = make_event(meta, 4, "final_output", payload={"answer": 1}, parents=[boom])
    path = write_trace(tmp_path / "t.jsonl", [meta, root, a, boom, final])

    with TopologicalReplayer(trace_file=path) as replayer:
        replayer.record_root_input({"q": 1})
        with pytest.raises(PrematureEventError):  # not KeyError: withheld
            replayer.record_tool_call("boom", {"p": 2}, poison_call, [a.event_id])
        _, a_id = replayer.record_tool_call("a", {"p": 1}, poison_call, [root.event_id])
        with pytest.raises(KeyError):  # ready now: historical error re-raised
            replayer.record_tool_call("boom", {"p": 2}, poison_call, [a_id])
        replayer.record_final_output({"answer": 1}, [boom.event_id])


def test_exact_identity_beats_ready_near_miss(tmp_path):
    """(type, name, hash) naming a blocked event wins over a ready same-name
    event with a different payload — prematurity, not argument_hash mismatch."""
    meta = make_metadata()
    root = make_event(meta, 1, "root_input", payload={"q": 1})
    x = make_event(meta, 2, "tool_call", name="f", payload={"p": 1},
                   parents=[root], historical_response={"r": 1})
    y = make_event(meta, 3, "tool_call", name="f", payload={"p": 2},
                   parents=[x], historical_response={"r": 2})
    final = make_event(meta, 4, "final_output", payload={"answer": 2}, parents=[y])
    path = write_trace(tmp_path / "t.jsonl", [meta, root, x, y, final])

    with pytest.raises(PrematureEventError) as excinfo:
        with TopologicalReplayer(trace_file=path) as replayer:
            replayer.record_root_input({"q": 1})
            # Exactly identifies blocked y (payload {"p": 2}), while ready x
            # shares only (type, name).
            replayer.record_tool_call("f", {"p": 2}, poison_call, [x.event_id])

    assert excinfo.value.at_event_id == y.event_id
    assert excinfo.value.missing_parent_ids == [x.event_id]


# --- divergence taxonomy ------------------------------------------------------------


def test_trace_exhausted(tmp_path):
    meta = make_metadata()
    root = make_event(meta, 1, "root_input", payload={"q": 1})
    a = make_event(meta, 2, "tool_call", name="a", payload={"p": 1},
                   parents=[root], historical_response={"r": 1})
    path = write_trace(tmp_path / "t.jsonl", [meta, root, a])  # valid prefix

    with pytest.raises(ReplayDivergence, match="trace exhausted"):
        with TopologicalReplayer(trace_file=path) as replayer:
            root_id = replayer.record_root_input({"q": 1})
            _, a_id = replayer.record_tool_call("a", {"p": 1}, poison_call, [root_id])
            replayer.record_tool_call("extra", {"p": 9}, poison_call, [a_id])


def test_no_matching_unconsumed_event_reports_ready_set(fanout):
    path, events = fanout
    with pytest.raises(ReplayDivergence, match="no matching unconsumed event") as excinfo:
        with TopologicalReplayer(trace_file=path) as replayer:
            root_id = replayer.record_root_input({"q": 1})
            replayer.record_tool_call("gamma", {"g": 1}, poison_call, [root_id])
    ready = excinfo.value.expected["ready_events"]
    assert [e["name"] for e in ready] == ["plan"]  # the one legal next move


def test_argument_hash_mismatch_on_unambiguous_target(fanout):
    path, events = fanout
    llm = events[2]
    with pytest.raises(ReplayDivergence, match="argument_hash mismatch") as excinfo:
        with TopologicalReplayer(trace_file=path) as replayer:
            root_id = replayer.record_root_input({"q": 1})
            replayer.record_llm_call("plan", {"p": "changed"}, poison_call, [root_id])
    assert excinfo.value.at_event_id == llm.event_id


def test_root_input_payload_change_is_argument_hash_mismatch(fanout):
    path, _ = fanout
    with pytest.raises(ReplayDivergence, match="argument_hash mismatch"):
        with TopologicalReplayer(trace_file=path) as replayer:
            replayer.record_root_input({"q": "different question"})


def test_parent_list_content_mismatch(fanout):
    path, _ = fanout
    with pytest.raises(ReplayDivergence, match="parent_event_ids mismatch"):
        with TopologicalReplayer(trace_file=path) as replayer:
            root_id = replayer.record_root_input({"q": 1})
            _, llm_id = replayer.record_llm_call("plan", {"p": 0}, poison_call, [root_id])
            # Recorded parents of alpha are [llm], not [root].
            replayer.record_tool_call("alpha", {"a": 1}, poison_call, [root_id])


def test_parent_list_order_mismatch(tmp_path):
    events = diamond_events()
    meta, root, a, b, c, final = events
    path = write_trace(tmp_path / "t.jsonl", events)
    with pytest.raises(ReplayDivergence, match="parent_event_ids mismatch"):
        with TopologicalReplayer(trace_file=path) as replayer:
            root_id = replayer.record_root_input({"q": 1})
            _, a_id = replayer.record_tool_call("a", {"p": 1}, poison_call, [root_id])
            _, b_id = replayer.record_tool_call("b", {"p": 2}, poison_call, [root_id])
            # Recorded order is [a, b]; order is significant (PLAN §1).
            replayer.record_llm_call("c", {"p": 3}, poison_call, [b_id, a_id])


def test_final_output_value_mismatch(fanout):
    path, _ = fanout
    with pytest.raises(FinalOutputMismatch) as excinfo:
        with TopologicalReplayer(trace_file=path) as replayer:
            root_id = replayer.record_root_input({"q": 1})
            _, llm_id = replayer.record_llm_call("plan", {"p": 0}, poison_call, [root_id])
            _, alpha_id = replayer.record_tool_call("alpha", {"a": 1}, poison_call, [llm_id])
            _, beta_id = replayer.record_tool_call("beta", {"b": 2}, poison_call, [llm_id])
            replayer.record_final_output({"answer": "WRONG"}, [alpha_id, beta_id])
    assert isinstance(excinfo.value, ReplayDivergence)
    assert replayer.report.final_output_matched is False


# --- D5: the documented parent-precondition fork ------------------------------------


def test_unknown_parent_id_is_divergence_in_topological_mode(fanout):
    path, _ = fanout
    fake = str(uuid.uuid4())
    # Topological mode: pure match data -> divergence, never ValueError.
    with pytest.raises(ReplayDivergence, match="parent_event_ids mismatch"):
        with TopologicalReplayer(trace_file=path) as replayer:
            replayer.record_root_input({"q": 1})
            replayer.record_llm_call("plan", {"p": 0}, poison_call, [fake])
    # Sequence mode keeps the API-misuse contract: ValueError at the boundary.
    with pytest.raises(ValueError, match="unknown parent_event_id"):
        with Replayer(trace_file=path) as replayer:
            replayer.record_root_input({"q": 1})
            replayer.record_llm_call("plan", {"p": 0}, poison_call, [fake])


# --- duplicates ---------------------------------------------------------------------


def test_identical_duplicates_consume_in_recorded_order(tmp_path):
    meta = make_metadata()
    root = make_event(meta, 1, "root_input", payload={"q": 1})
    t1 = make_event(meta, 2, "tool_call", name="t", payload={"p": 1},
                    parents=[root], historical_response={"r": "first"})
    t2 = make_event(meta, 3, "tool_call", name="t", payload={"p": 1},
                    parents=[root], historical_response={"r": "second"})
    final = make_event(meta, 4, "final_output", payload={"answer": 1},
                       parents=[t1, t2])
    path = write_trace(tmp_path / "t.jsonl", [meta, root, t1, t2, final])

    with TopologicalReplayer(trace_file=path) as replayer:
        root_id = replayer.record_root_input({"q": 1})
        first, first_id = replayer.record_tool_call("t", {"p": 1}, poison_call, [root_id])
        second, second_id = replayer.record_tool_call("t", {"p": 1}, poison_call, [root_id])
        assert (first, first_id) == ({"r": "first"}, t1.event_id)
        assert (second, second_id) == ({"r": "second"}, t2.event_id)
        replayer.record_final_output({"answer": 1}, [first_id, second_id])
    assert replayer.report.clean


# --- redactor parity ----------------------------------------------------------------


def redact_secret(payload):
    if isinstance(payload, dict) and "secret" in payload:
        return {**payload, "secret": "[REDACTED]"}
    return payload


def record_with_secret(path):
    with Recorder(agent_id="demo-agent", capture_to=path, redactor=redact_secret) as rec:
        root_id = rec.record_root_input({"q": 1, "secret": "hunter2"})
        _, llm_id = rec.record_llm_call("plan", {"p": 0}, lambda: {"r": 0}, [root_id])
        rec.record_final_output({"answer": "done"}, [llm_id])
    return path


def test_redactor_parity_in_topological_mode(tmp_path):
    path = record_with_secret(tmp_path / "t.jsonl")

    with TopologicalReplayer(trace_file=path, redactor=redact_secret) as replayer:
        root_id = replayer.record_root_input({"q": 1, "secret": "hunter2"})
        _, llm_id = replayer.record_llm_call("plan", {"p": 0}, poison_call, [root_id])
        replayer.record_final_output({"answer": "done"}, [llm_id])
    assert replayer.report.clean

    # Same trace, no redactor: hashes were computed post-redaction, so the
    # raw payload no longer matches.
    with pytest.raises(ReplayDivergence, match="argument_hash mismatch"):
        with TopologicalReplayer(trace_file=path) as replayer:
            replayer.record_root_input({"q": 1, "secret": "hunter2"})


# --- exit rules and lifecycle --------------------------------------------------------


def test_clean_exit_with_unconsumed_events_diverges(fanout):
    path, events = fanout
    with pytest.raises(ReplayDivergence, match="unconsumed events at exit"):
        with TopologicalReplayer(trace_file=path) as replayer:
            root_id = replayer.record_root_input({"q": 1})
            replayer.record_llm_call("plan", {"p": 0}, poison_call, [root_id])
            # exits cleanly with alpha, beta, final never consumed


def test_clean_exit_without_final_on_fully_consumed_prefix(tmp_path):
    meta = make_metadata()
    root = make_event(meta, 1, "root_input", payload={"q": 1})
    a = make_event(meta, 2, "tool_call", name="a", payload={"p": 1},
                   parents=[root], historical_response={"r": 1})
    path = write_trace(tmp_path / "t.jsonl", [meta, root, a])

    with pytest.raises(FinalOutputNotCalled):
        with TopologicalReplayer(trace_file=path) as replayer:
            root_id = replayer.record_root_input({"q": 1})
            replayer.record_tool_call("a", {"p": 1}, poison_call, [root_id])


def test_call_after_final_output_raises(fanout):
    path, _ = fanout
    with TopologicalReplayer(trace_file=path) as replayer:
        run_fanout_agent(replayer)
        with pytest.raises(LifecycleError, match="after record_final_output"):
            replayer.record_tool_call("alpha", {"a": 1}, poison_call, [])


def test_calls_outside_context_raise(fanout):
    path, _ = fanout
    replayer = TopologicalReplayer(trace_file=path)
    with pytest.raises(LifecycleError, match="outside an active"):
        replayer.record_root_input({"q": 1})


def test_context_is_not_reentrant(fanout):
    path, _ = fanout
    with TopologicalReplayer(trace_file=path) as replayer:
        with pytest.raises(LifecycleError, match="not reentrant"):
            with replayer:
                pass
        run_fanout_agent(replayer)


def test_agent_exception_propagates_unchanged(fanout):
    path, _ = fanout

    class AgentBug(RuntimeError):
        pass

    with pytest.raises(AgentBug):
        with TopologicalReplayer(trace_file=path) as replayer:
            replayer.record_root_input({"q": 1})
            raise AgentBug("the agent's own crash, never masked")
    assert len(replayer.report.unconsumed_event_ids) == 4


def test_corrupted_trace_rejected_on_enter(fanout, tmp_path):
    path, _ = fanout
    lines = path.read_text(encoding="utf-8").splitlines()
    tampered = json.loads(lines[2])
    tampered["argument_hash"] = "0" * 64
    lines[2] = json.dumps(tampered, ensure_ascii=False)
    bad = tmp_path / "tampered.jsonl"
    bad.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="argument_hash mismatch"):
        TopologicalReplayer(trace_file=bad).__enter__()


# --- package exports -----------------------------------------------------------------


def test_new_names_are_exported_from_the_package():
    import flight_recorder

    assert flight_recorder.TopologicalReplayer is TopologicalReplayer
    assert flight_recorder.PrematureEventError is PrematureEventError
    from flight_recorder import DagScheduler, SchedulingError  # noqa: F401

    for name in ("DagScheduler", "PrematureEventError", "SchedulingError",
                 "TopologicalReplayer", "iter_events"):
        assert name in flight_recorder.__all__
