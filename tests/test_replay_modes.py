"""Strict, structured, and semantic replay mode tests."""

import pytest

from flight_recorder.errors import ReplayDivergence
from flight_recorder.recorder import Recorder
from flight_recorder.replayer import Replayer


def _record_simple(trace):
    with Recorder("modes", trace) as rr:
        root = rr.record_root_input({"query": "support"})
        response, llm = rr.record_llm_call(
            "planner",
            {"prompt": "find customer", "temperature": 0},
            lambda: {"customer_id": "cust_123"},
            [root],
        )
        rr.record_final_output({"customer_id": response["customer_id"]}, [llm])


def test_strict_mode_remains_default(tmp_path):
    trace = tmp_path / "trace.jsonl"
    _record_simple(trace)

    with pytest.raises(ReplayDivergence, match="argument_hash mismatch"):
        with Replayer(trace) as rr:
            root = rr.record_root_input({"query": "support"})
            rr.record_llm_call(
                "planner",
                {"prompt": "find account", "temperature": 0},
                lambda: {"should": "not run"},
                [root],
            )


def test_structured_mode_accepts_same_json_shape(tmp_path):
    trace = tmp_path / "trace.jsonl"
    _record_simple(trace)

    with Replayer(trace, mode="structured") as rr:
        root = rr.record_root_input({"query": "support"})
        response, llm = rr.record_llm_call(
            "planner",
            {"prompt": "find account", "temperature": 1},
            lambda: {"should": "not run"},
            [root],
        )
        assert response == {"customer_id": "cust_123"}
        rr.record_final_output({"customer_id": "changed-but-same-shape"}, [llm])


def test_structured_mode_rejects_different_json_shape(tmp_path):
    trace = tmp_path / "trace.jsonl"
    _record_simple(trace)

    with pytest.raises(ReplayDivergence, match="structured payload mismatch"):
        with Replayer(trace, mode="structured") as rr:
            root = rr.record_root_input({"query": "support"})
            rr.record_llm_call(
                "planner",
                {"prompt": {"nested": "find account"}, "temperature": 1},
                lambda: {"should": "not run"},
                [root],
            )


def test_semantic_mode_uses_callback_hook(tmp_path):
    trace = tmp_path / "trace.jsonl"
    _record_simple(trace)

    with Replayer(trace, mode="semantic", semantic_matcher=lambda expected, actual: True) as rr:
        root = rr.record_root_input({"query": "support"})
        response, llm = rr.record_llm_call(
            "planner",
            {"prompt": "same intent in different words", "temperature": 1},
            lambda: {"should": "not run"},
            [root],
        )
        assert response == {"customer_id": "cust_123"}
        rr.record_final_output({"customer_id": "semantically ok"}, [llm])


def test_semantic_mode_without_callback_is_explicit_future_hook(tmp_path):
    trace = tmp_path / "trace.jsonl"
    _record_simple(trace)

    with pytest.raises(ReplayDivergence, match="semantic matcher unavailable"):
        with Replayer(trace, mode="semantic") as rr:
            root = rr.record_root_input({"query": "support"})
            rr.record_llm_call(
                "planner",
                {"prompt": "same intent in different words", "temperature": 1},
                lambda: {"should": "not run"},
                [root],
            )
