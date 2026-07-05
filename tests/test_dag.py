"""Tests for trace-level DAG invariant validation and hash verification (PLAN §1, §6)."""

import dataclasses
import uuid

import pytest

from conftest import make_event, make_metadata, make_trace
from flight_recorder.dag import validate_trace, verify_hashes
from flight_recorder.hashing import context_hash


@pytest.fixture
def trace():
    return make_trace()


def _replace(trace, position, **overrides):
    mutated = list(trace)
    mutated[position] = dataclasses.replace(trace[position], **overrides)
    return mutated


# --- Structural validation -----------------------------------------------------


def test_valid_trace_passes(trace):
    validate_trace(trace)
    validate_trace(trace, require_complete=True)


@pytest.mark.parametrize("length", [1, 2, 3, 4, 5])
def test_every_prefix_is_structurally_valid(trace, length):
    # Crash-truncated traces validate line-by-line (PLAN §2, §8).
    validate_trace(trace[:length])


def test_empty_trace_rejected():
    with pytest.raises(ValueError, match="empty trace"):
        validate_trace([])


def test_missing_metadata_rejected(trace):
    with pytest.raises(ValueError, match="invalid trace"):
        validate_trace(trace[1:])


def test_per_event_validation_runs(trace):
    bad = _replace(trace, 2, agent_id="")
    with pytest.raises(ValueError, match="event at position 2: invalid event"):
        validate_trace(bad)


def test_sequence_gap_rejected(trace):
    with pytest.raises(ValueError, match="monotonic from 0 with no gaps"):
        validate_trace([trace[0], trace[1], trace[3], trace[4]])


def test_duplicate_sequence_index_rejected(trace):
    bad = _replace(trace, 3, call_sequence_index=2)
    with pytest.raises(ValueError, match="monotonic from 0 with no gaps"):
        validate_trace(bad)


def test_duplicate_event_id_rejected(trace):
    bad = _replace(trace, 4, event_id=trace[1].event_id)
    with pytest.raises(ValueError, match="duplicate event_id"):
        validate_trace(bad)


def test_mixed_run_ids_rejected(trace):
    bad = _replace(trace, 2, run_id=str(uuid.uuid4()))
    with pytest.raises(ValueError, match="mixed run_ids"):
        validate_trace(bad)


def test_mixed_agent_ids_rejected(trace):
    bad = _replace(trace, 2, agent_id="other-agent")
    with pytest.raises(ValueError, match="mixed agent_ids"):
        validate_trace(bad)


# --- Parent / DAG invariant ------------------------------------------------------


def test_unknown_parent_rejected(trace):
    bad = _replace(trace, 2, parent_event_ids=[str(uuid.uuid4())])
    with pytest.raises(ValueError, match="unknown parent"):
        validate_trace(bad)


def test_forward_parent_reference_rejected(trace):
    bad = _replace(trace, 2, parent_event_ids=[trace[4].event_id])
    with pytest.raises(ValueError, match="strictly lower call_sequence_index"):
        validate_trace(bad)


def test_self_parent_rejected(trace):
    bad = _replace(trace, 2, parent_event_ids=[trace[2].event_id])
    with pytest.raises(ValueError, match="strictly lower call_sequence_index"):
        validate_trace(bad)


def test_metadata_as_parent_rejected(trace):
    bad = _replace(trace, 2, parent_event_ids=[trace[0].event_id])
    with pytest.raises(ValueError, match="metadata event as a parent"):
        validate_trace(bad)


# --- Lifecycle structure -----------------------------------------------------------


def test_boundary_call_before_root_input_rejected():
    meta = make_metadata()
    llm = make_event(meta, 1, "llm_call", name="llm_plan", payload={"p": 1}, historical_response={"r": 1})
    with pytest.raises(ValueError, match="second event must be root_input"):
        validate_trace([meta, llm])


def test_multiple_root_inputs_rejected():
    meta = make_metadata()
    root = make_event(meta, 1, "root_input", payload={"q": 1})
    root2 = make_event(meta, 2, "root_input", payload={"q": 2})
    with pytest.raises(ValueError, match="multiple root_input events"):
        validate_trace([meta, root, root2])


def test_final_output_not_last_rejected():
    meta = make_metadata()
    root = make_event(meta, 1, "root_input", payload={"q": 1})
    final = make_event(meta, 2, "final_output", payload={"a": 1}, parents=[root])
    llm = make_event(meta, 3, "llm_call", name="llm_plan", payload={"p": 1}, parents=[root], historical_response={"r": 1})
    with pytest.raises(ValueError, match="final_output must be the last event"):
        validate_trace([meta, root, final, llm])


def test_multiple_final_outputs_rejected():
    meta = make_metadata()
    root = make_event(meta, 1, "root_input", payload={"q": 1})
    final1 = make_event(meta, 2, "final_output", payload={"a": 1}, parents=[root])
    final2 = make_event(meta, 3, "final_output", payload={"a": 2}, parents=[root])
    with pytest.raises(ValueError, match="multiple final_output events"):
        validate_trace([meta, root, final1, final2])


@pytest.mark.parametrize(
    ("length", "match"),
    [
        pytest.param(1, "no root_input event", id="metadata-only"),
        pytest.param(4, "no final_output event", id="no-final"),
    ],
)
def test_require_complete_demands_root_and_final(trace, length, match):
    with pytest.raises(ValueError, match=match):
        validate_trace(trace[:length], require_complete=True)


# --- Hash verification --------------------------------------------------------------


def test_valid_trace_hashes_verify(trace):
    verify_hashes(trace)


def test_tampered_argument_hash_detected(trace):
    bad = _replace(trace, 2, argument_hash="0" * 64)
    with pytest.raises(ValueError, match="argument_hash mismatch"):
        verify_hashes(bad)


def test_tampered_payload_detected(trace):
    bad = _replace(trace, 1, payload={"query": "tampered"})
    with pytest.raises(ValueError, match="argument_hash mismatch"):
        verify_hashes(bad)


def test_tampered_response_detected_via_context_hash(trace):
    # argument_hash covers the request only; the response is caught by context_hash.
    bad = _replace(trace, 2, historical_response={"plan": []})
    with pytest.raises(ValueError, match="context_hash mismatch"):
        verify_hashes(bad)


def test_tampered_status_and_error_detected_via_context_hash(trace):
    bad = _replace(trace, 3, error={"type": "KeyError", "message": "tampered"})
    with pytest.raises(ValueError, match="context_hash mismatch"):
        verify_hashes(bad)


def test_error_traceback_is_not_part_of_context_hash(trace):
    tool = trace[3]
    with_traceback = _replace(
        trace,
        3,
        error={
            "type": tool.error["type"],
            "message": tool.error["message"],
            "traceback": "Traceback from /Users/alice/project/agent.py",
        },
    )
    verify_hashes(with_traceback)

    edited_traceback = _replace(
        with_traceback,
        3,
        error={
            "type": tool.error["type"],
            "message": tool.error["message"],
            "traceback": "Traceback from /home/bob/project/agent.py",
        },
    )
    verify_hashes(edited_traceback)


def test_error_type_and_message_still_drive_context_hash(trace):
    tool = trace[3]
    bad = _replace(
        trace,
        3,
        error={
            "type": tool.error["type"],
            "message": "tampered",
            "traceback": "Traceback from /Users/alice/project/agent.py",
        },
    )
    with pytest.raises(ValueError, match="context_hash mismatch"):
        verify_hashes(bad)


def test_legacy_error_hash_with_traceback_still_verifies(trace):
    tool = trace[3]
    error = {
        "type": tool.error["type"],
        "message": tool.error["message"],
        "traceback": "Traceback from /Users/alice/project/agent.py",
    }
    legacy_context = context_hash(
        [trace[2].context_hash],
        tool.event_type,
        tool.name,
        tool.payload,
        tool.historical_response,
        tool.status,
        error,
        include_error_traceback_for_legacy=True,
    )
    legacy = _replace(trace, 3, error=error, context_hash=legacy_context)
    verify_hashes(legacy[:4])


def test_parent_order_is_pinned_into_context_hash(trace):
    final = trace[4]
    assert len(final.parent_event_ids) == 2
    bad = _replace(trace, 4, parent_event_ids=list(reversed(final.parent_event_ids)))
    with pytest.raises(ValueError, match="context_hash mismatch"):
        verify_hashes(bad)


def test_upstream_change_ripples_downstream(trace):
    # Replace the root with a self-consistent event carrying a different
    # payload: the root itself verifies, but its children chained the old
    # context hash, so the mismatch surfaces downstream.
    meta = trace[0]
    new_root = dataclasses.replace(
        make_event(meta, 1, "root_input", payload={"query": "different"}),
        event_id=trace[1].event_id,  # keep the id children point at; ids are never hashed
    )
    bad = [meta, new_root] + trace[2:]
    with pytest.raises(ValueError, match="context_hash mismatch"):
        verify_hashes(bad)
