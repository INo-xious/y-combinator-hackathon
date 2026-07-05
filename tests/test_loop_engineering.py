"""LoopRun helper tests for hand-rolled agent loops."""

import pytest

from flight_recorder import LoopRun, LoopStep
from flight_recorder.errors import ReplayDivergence
from flight_recorder.recorder import Recorder
from flight_recorder.replayer import Replayer, TopologicalReplayer
from flight_recorder.storage import read_events


def _call_returning(name, value, *, poison=False):
    def call():
        if poison:
            raise AssertionError(f"{name} should not execute during replay")
        return value

    return call


def run_two_step_react(rr, *, priority="standard", poison=False):
    loop = LoopRun.start(
        rr,
        {"ticket_id": "t_123", "message": "Need help with my account."},
    )
    first = loop.step()
    thought, _thought_id = first.llm(
        "think",
        {"iteration": 1, "goal": "choose lookup action"},
        _call_returning(
            "first thought",
            {"action": "lookup_account", "account_id": "acct_123"},
            poison=poison,
        ),
    )
    account, _account_id = first.tool(
        thought["action"],
        {"account_id": thought["account_id"]},
        _call_returning(
            "account lookup",
            {"account_id": "acct_123", "tier": "enterprise"},
            poison=poison,
        ),
    )

    second = loop.step()
    decision, _decision_id = second.llm(
        "decide",
        {"iteration": 2, "tier": account["tier"], "priority": priority},
        _call_returning(
            "second decision",
            {"answer": f"{priority} support path for {account['tier']}"},
            poison=poison,
        ),
    )
    loop.final({"answer": decision["answer"]})
    return decision


def test_two_step_react_loop_records_replays_and_tracks_parents(tmp_path):
    trace = tmp_path / "loop.jsonl"

    with Recorder("loop-agent", trace) as rr:
        assert run_two_step_react(rr) == {
            "answer": "standard support path for enterprise"
        }

    events = read_events(trace)
    root, first_thought, first_tool, second_decision, final = events[1:]
    assert first_thought.name == "step_1.think"
    assert first_tool.name == "step_1.lookup_account"
    assert second_decision.name == "step_2.decide"
    assert first_thought.parent_event_ids == [root.event_id]
    assert first_tool.parent_event_ids == [first_thought.event_id]
    assert second_decision.parent_event_ids == [first_tool.event_id]
    assert final.parent_event_ids == [second_decision.event_id]

    with Replayer(trace) as rr:
        assert run_two_step_react(rr, poison=True) == {
            "answer": "standard support path for enterprise"
        }
    assert rr.report.clean


def test_loop_iteration_payload_drift_reports_loop_boundary_name(tmp_path):
    trace = tmp_path / "loop.jsonl"
    with Recorder("loop-agent", trace) as rr:
        run_two_step_react(rr, priority="standard")

    with pytest.raises(ReplayDivergence) as excinfo:
        with Replayer(trace) as rr:
            run_two_step_react(rr, priority="urgent", poison=True)

    assert excinfo.value.reason == "argument_hash mismatch"
    assert excinfo.value.expected["name"] == "step_2.decide"
    assert excinfo.value.actual["payload"]["priority"] == "urgent"


def run_fanout_loop(rr, *, beta_first=False, poison=False):
    loop = LoopRun.start(rr, {"query": "run independent checks"})
    inspect = loop.step("inspect")
    plan, plan_id = inspect.llm(
        "plan",
        {"checks": ["alpha", "beta"]},
        _call_returning("plan", {"checks": ["alpha", "beta"]}, poison=poison),
    )

    if beta_first:
        beta, beta_id = inspect.tool(
            "beta",
            {"check": plan["checks"][1]},
            _call_returning("beta", {"beta_ok": True}, poison=poison),
            [plan_id],
        )
        alpha, alpha_id = inspect.tool(
            "alpha",
            {"check": plan["checks"][0]},
            _call_returning("alpha", {"alpha_ok": True}, poison=poison),
            [plan_id],
        )
    else:
        alpha, alpha_id = inspect.tool(
            "alpha",
            {"check": plan["checks"][0]},
            _call_returning("alpha", {"alpha_ok": True}, poison=poison),
            [plan_id],
        )
        beta, beta_id = inspect.tool(
            "beta",
            {"check": plan["checks"][1]},
            _call_returning("beta", {"beta_ok": True}, poison=poison),
            [plan_id],
        )

    join = loop.step("join")
    summary, _summary_id = join.llm(
        "summarize",
        {"alpha_ok": alpha["alpha_ok"], "beta_ok": beta["beta_ok"]},
        _call_returning("summary", {"summary": "both checks passed"}, poison=poison),
        [alpha_id, beta_id],
    )
    loop.final({"summary": summary["summary"]})
    return summary


def test_fanout_loop_reordered_tools_replay_under_topological_replayer(tmp_path):
    trace = tmp_path / "fanout.jsonl"
    with Recorder("loop-agent", trace) as rr:
        run_fanout_loop(rr, beta_first=False)

    with TopologicalReplayer(trace) as rr:
        assert run_fanout_loop(rr, beta_first=True, poison=True) == {
            "summary": "both checks passed"
        }
    assert rr.report.clean


def run_explicit_final_parent_loop(rr, *, poison=False):
    loop = LoopRun.start(rr, {"query": "final parent override"})
    root_parents = loop.current_parent_ids
    step = loop.step()
    step.tool(
        "side_effect",
        {"id": 1},
        _call_returning("side effect", {"ok": True}, poison=poison),
    )
    return loop.final({"done": True}, root_parents)


def test_final_uses_current_parents_by_default_and_accepts_override(tmp_path):
    default_trace = tmp_path / "default.jsonl"
    with Recorder("loop-agent", default_trace) as rr:
        run_two_step_react(rr)
    events = read_events(default_trace)
    assert events[-1].parent_event_ids == [events[-2].event_id]

    override_trace = tmp_path / "override.jsonl"
    with Recorder("loop-agent", override_trace) as rr:
        run_explicit_final_parent_loop(rr)
    events = read_events(override_trace)
    root, side_effect, final = events[1:]
    assert side_effect.name == "step_1.side_effect"
    assert final.parent_event_ids == [root.event_id]

    with Replayer(override_trace) as rr:
        run_explicit_final_parent_loop(rr, poison=True)
    assert rr.report.clean


def test_loop_helpers_are_exported_from_package():
    assert LoopRun.start
    assert LoopStep.__name__ == "LoopStep"
