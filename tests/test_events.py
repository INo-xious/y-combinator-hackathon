"""Schema, invariant, and serialization round-trip tests for TraceEvent (PLAN §1, §8).

Trace-level invariants (metadata first, monotonic indices, parent < child
sequence, unique ids, single run_id) belong to dag.py and are not tested here.
"""

import dataclasses
import json

import pytest

from flight_recorder.events import (
    BOUNDARY_EVENT_TYPES,
    EVENT_FIELDS,
    EVENT_TYPES,
    METADATA_PAYLOAD_KEYS,
    RECORDER_VERSION,
    SCHEMA_VERSION,
    STATUSES,
    TraceEvent,
)
from flight_recorder.hashing import argument_hash, context_hash

RUN_ID = "7f5f2f64-6b8e-4f39-9c39-2f2b6a8c1d10"
AGENT_ID = "demo-agent"
TS = "2026-07-04T12:00:00Z"

METADATA_ID = "0d9a4f7e-1c2b-4d3e-8f4a-5b6c7d8e9f01"
ROOT_ID = "1a2b3c4d-5e6f-4a1b-9c2d-3e4f5a6b7c8d"
LLM_ID = "2b3c4d5e-6f7a-4b2c-8d3e-4f5a6b7c8d9e"
TOOL_ID = "3c4d5e6f-7a8b-4c3d-9e4f-5a6b7c8d9e0f"
FINAL_ID = "4d5e6f7a-8b9c-4d4e-8f5a-6b7c8d9e0f1a"


def _event(**overrides) -> TraceEvent:
    base = dict(
        event_id=METADATA_ID,
        run_id=RUN_ID,
        agent_id=AGENT_ID,
        parent_event_ids=[],
        call_sequence_index=0,
        event_type="metadata",
        name=None,
        timestamp=TS,
        payload=None,
        historical_response=None,
        status="ok",
        error=None,
        argument_hash=None,
        context_hash=None,
        latency_ms=None,
    )
    base.update(overrides)
    return TraceEvent(**base)


def metadata_event(**overrides) -> TraceEvent:
    return _event(
        payload={
            "schema_version": SCHEMA_VERSION,
            "recorder_version": RECORDER_VERSION,
            "trace_creation_time": TS,
            "run_id": RUN_ID,
            "agent_id": AGENT_ID,
        },
        **overrides,
    )


def root_input_event(**overrides) -> TraceEvent:
    payload = {"query": "Look up customer 123 and summarize their last 5 orders."}
    return _event(
        event_id=ROOT_ID,
        call_sequence_index=1,
        event_type="root_input",
        payload=payload,
        argument_hash=argument_hash("root_input", None, payload),
        context_hash=context_hash([], "root_input", None, payload, None, "ok", None),
        **overrides,
    )


def llm_call_event(**overrides) -> TraceEvent:
    payload = {"prompt": "Plan the task", "temperature": 0}
    response = {"plan": ["lookup_customer", "fetch_orders"]}
    root_ctx = root_input_event().context_hash
    defaults = dict(
        event_id=LLM_ID,
        parent_event_ids=[ROOT_ID],
        call_sequence_index=2,
        event_type="llm_call",
        name="llm_plan",
        payload=payload,
        historical_response=response,
        argument_hash=argument_hash("llm_call", "llm_plan", payload),
        context_hash=context_hash([root_ctx], "llm_call", "llm_plan", payload, response, "ok", None),
        latency_ms=12,
    )
    defaults.update(overrides)
    return _event(**defaults)


def failed_tool_event(**overrides) -> TraceEvent:
    payload = {"customer_id": 123, "limit": 5}
    error = {"type": "KeyError", "message": "'orders'", "traceback": "Traceback: ..."}
    llm_ctx = llm_call_event().context_hash
    defaults = dict(
        event_id=TOOL_ID,
        parent_event_ids=[LLM_ID],
        call_sequence_index=3,
        event_type="tool_call",
        name="fetch_orders",
        payload=payload,
        status="error",
        error=error,
        argument_hash=argument_hash("tool_call", "fetch_orders", payload),
        context_hash=context_hash([llm_ctx], "tool_call", "fetch_orders", payload, None, "error", error),
        latency_ms=3,
    )
    defaults.update(overrides)
    return _event(**defaults)


def final_output_event(**overrides) -> TraceEvent:
    payload = {"answer": "Customer 123 has 5 recent orders."}
    llm_ctx = llm_call_event().context_hash
    return _event(
        event_id=FINAL_ID,
        parent_event_ids=[LLM_ID],
        call_sequence_index=4,
        event_type="final_output",
        payload=payload,
        argument_hash=argument_hash("final_output", None, payload),
        context_hash=context_hash([llm_ctx], "final_output", None, payload, None, "ok", None),
        **overrides,
    )


ALL_FACTORIES = [metadata_event, root_input_event, llm_call_event, failed_tool_event, final_output_event]
FACTORY_IDS = ["metadata", "root_input", "llm_call", "failed_tool_call", "final_output"]


# --- Schema constants ---------------------------------------------------------


def test_schema_constants_match_plan():
    assert SCHEMA_VERSION == "1.0"
    assert EVENT_TYPES == ("metadata", "root_input", "llm_call", "tool_call", "final_output")
    assert BOUNDARY_EVENT_TYPES == ("llm_call", "tool_call")
    assert STATUSES == ("ok", "error")
    assert METADATA_PAYLOAD_KEYS == {
        "schema_version",
        "recorder_version",
        "trace_creation_time",
        "run_id",
        "agent_id",
    }


def test_event_fields_match_plan_order():
    assert EVENT_FIELDS == (
        "event_id",
        "run_id",
        "agent_id",
        "parent_event_ids",
        "call_sequence_index",
        "event_type",
        "name",
        "timestamp",
        "payload",
        "historical_response",
        "status",
        "error",
        "argument_hash",
        "context_hash",
        "latency_ms",
        "signature",
    )


# --- Valid events and round-trips ---------------------------------------------


@pytest.mark.parametrize("factory", ALL_FACTORIES, ids=FACTORY_IDS)
def test_valid_events_validate(factory):
    factory().validate()


@pytest.mark.parametrize("factory", ALL_FACTORIES, ids=FACTORY_IDS)
def test_json_round_trip_preserves_equality(factory):
    event = factory()
    line = json.dumps(event.to_dict())
    assert TraceEvent.from_dict(json.loads(line)) == event


def test_to_dict_deep_copies_mutable_payloads():
    event = llm_call_event()
    event.to_dict()["payload"]["prompt"] = "mutated"
    assert event.payload["prompt"] == "Plan the task"


def test_to_dict_uses_schema_field_order():
    assert tuple(metadata_event().to_dict()) == EVENT_FIELDS


# --- from_dict strictness -------------------------------------------------------


def test_from_dict_rejects_missing_fields():
    data = metadata_event().to_dict()
    del data["context_hash"]
    with pytest.raises(ValueError, match="missing fields: context_hash"):
        TraceEvent.from_dict(data)


def test_from_dict_rejects_unknown_fields():
    data = metadata_event().to_dict()
    data["extra"] = 1
    with pytest.raises(ValueError, match="unknown fields: 'extra'"):
        TraceEvent.from_dict(data)


def test_from_dict_rejects_non_dict():
    with pytest.raises(ValueError, match="must be a JSON object"):
        TraceEvent.from_dict([1, 2, 3])


def test_from_dict_validates():
    data = llm_call_event().to_dict()
    data["name"] = None
    with pytest.raises(ValueError, match="name is required"):
        TraceEvent.from_dict(data)


# --- Per-event invariants --------------------------------------------------------


def _assert_invalid(factory, match, **overrides):
    event = dataclasses.replace(factory(), **overrides)
    with pytest.raises(ValueError, match=match):
        event.validate()


@pytest.mark.parametrize(
    ("overrides", "match"),
    [
        pytest.param({"event_id": "not-a-uuid"}, "event_id is not a valid UUID", id="bad-event-id"),
        pytest.param({"event_id": 42}, "event_id must be a UUID string", id="non-str-event-id"),
        pytest.param({"run_id": "xyz"}, "run_id is not a valid UUID", id="bad-run-id"),
        pytest.param({"agent_id": ""}, "agent_id must be a non-empty string", id="empty-agent-id"),
        pytest.param({"event_type": "bogus"}, "event_type 'bogus'", id="bad-event-type"),
        pytest.param({"status": "unknown"}, "status 'unknown'", id="bad-status"),
        pytest.param({"call_sequence_index": "3"}, "call_sequence_index must be an int", id="str-index"),
        pytest.param({"call_sequence_index": True}, "call_sequence_index must be an int", id="bool-index"),
        pytest.param({"parent_event_ids": ("x",)}, "parent_event_ids must be a list", id="tuple-parents"),
        pytest.param(
            {"parent_event_ids": ["not-a-uuid"]},
            r"parent_event_ids\[0\] is not a valid UUID",
            id="bad-parent-uuid",
        ),
        pytest.param({"timestamp": "not-a-time"}, "timestamp is not ISO 8601", id="bad-timestamp"),
        pytest.param({"timestamp": ""}, "timestamp must be a non-empty ISO 8601", id="empty-timestamp"),
        pytest.param({"latency_ms": -1}, "latency_ms", id="negative-latency"),
        pytest.param({"latency_ms": True}, "latency_ms", id="bool-latency"),
        pytest.param({"payload": {"blob": b"raw"}}, "payload is not strict JSON", id="bytes-payload"),
        pytest.param({"payload": {1: "x"}}, "payload is not strict JSON", id="non-str-key-payload"),
    ],
)
def test_common_field_invariants(overrides, match):
    # Applied to a boundary event, but these rules hold for every type.
    _assert_invalid(llm_call_event, match, **overrides)


def test_timestamp_accepts_z_and_offset_forms():
    llm_call_event(timestamp="2026-07-04T12:00:00Z").validate()
    llm_call_event(timestamp="2026-07-04T12:00:00+00:00").validate()
    llm_call_event(timestamp="2026-07-04T12:00:00.123456+02:00").validate()


@pytest.mark.parametrize(
    ("overrides", "match"),
    [
        pytest.param({"call_sequence_index": 1}, "must have call_sequence_index 0", id="nonzero-index"),
        pytest.param({"parent_event_ids": [ROOT_ID]}, "must have empty parent_event_ids", id="has-parents"),
        pytest.param({"name": "x"}, "name must be null", id="has-name"),
        pytest.param({"status": "error"}, "status must be 'ok'", id="error-status"),
        pytest.param(
            {"historical_response": {"x": 1}},
            "historical_response must be null",
            id="has-response",
        ),
        pytest.param({"argument_hash": "ab" * 32}, "must be null on the metadata event", id="has-arg-hash"),
        pytest.param({"context_hash": "ab" * 32}, "must be null on the metadata event", id="has-ctx-hash"),
        pytest.param({"payload": None}, "metadata payload must be a dict", id="null-payload"),
    ],
)
def test_metadata_event_invariants(overrides, match):
    _assert_invalid(metadata_event, match, **overrides)


def test_metadata_payload_schema_version_mismatch_is_explicit():
    payload = metadata_event().payload | {"schema_version": "2.0"}
    _assert_invalid(metadata_event, "unsupported schema_version '2.0'", payload=payload)


def test_metadata_payload_key_set_is_exact():
    base = metadata_event().payload
    missing = {k: v for k, v in base.items() if k != "trace_creation_time"}
    _assert_invalid(metadata_event, "missing \\['trace_creation_time'\\]", payload=missing)
    _assert_invalid(metadata_event, "unexpected \\['extra'\\]", payload=base | {"extra": 1})


def test_metadata_payload_must_self_reference_run_and_agent():
    other_uuid = "9e8d7c6b-5a4f-4e3d-8c2b-1a0f9e8d7c6b"
    base = metadata_event().payload
    _assert_invalid(metadata_event, "run_id must match", payload=base | {"run_id": other_uuid})
    _assert_invalid(metadata_event, "agent_id must match", payload=base | {"agent_id": "other"})


def test_non_metadata_events_cannot_use_sequence_zero():
    _assert_invalid(root_input_event, "call_sequence_index >= 1", call_sequence_index=0)


def test_root_input_must_have_no_parents():
    _assert_invalid(root_input_event, "must have empty parent_event_ids", parent_event_ids=[LLM_ID])


@pytest.mark.parametrize(
    ("factory", "overrides", "match"),
    [
        pytest.param(llm_call_event, {"name": None}, "name is required", id="llm-no-name"),
        pytest.param(llm_call_event, {"name": ""}, "name is required", id="llm-empty-name"),
        pytest.param(root_input_event, {"name": "x"}, "name must be null", id="root-has-name"),
        pytest.param(final_output_event, {"name": "x"}, "name must be null", id="final-has-name"),
    ],
)
def test_name_presence_matrix(factory, overrides, match):
    _assert_invalid(factory, match, **overrides)


@pytest.mark.parametrize(
    ("factory", "overrides", "match"),
    [
        pytest.param(
            llm_call_event,
            {"historical_response": None},
            "historical_response is required for successful boundary calls",
            id="ok-boundary-null-response",
        ),
        pytest.param(
            llm_call_event,
            {"historical_response": {"blob": b"raw"}},
            "historical_response is not strict JSON",
            id="ok-boundary-bytes-response",
        ),
        pytest.param(
            root_input_event,
            {"historical_response": {"x": 1}},
            "historical_response must be null",
            id="root-has-response",
        ),
        pytest.param(
            final_output_event,
            {"historical_response": {"x": 1}},
            "historical_response must be null",
            id="final-has-response",
        ),
        pytest.param(
            failed_tool_event,
            {"historical_response": {"x": 1}},
            "historical_response must be null",
            id="failed-call-has-response",
        ),
    ],
)
def test_historical_response_matrix(factory, overrides, match):
    _assert_invalid(factory, match, **overrides)


@pytest.mark.parametrize(
    ("overrides", "match"),
    [
        pytest.param({"error": None}, "error must be a dict when status is 'error'", id="null-error"),
        pytest.param({"error": "boom"}, "error must be a dict", id="str-error"),
        pytest.param({"error": {"type": "KeyError"}}, "error.message is required", id="no-message"),
        pytest.param({"error": {"message": "boom"}}, "error.type is required", id="no-type"),
        pytest.param({"error": {"type": "", "message": "boom"}}, "error.type must be a non-empty", id="empty-type"),
        pytest.param(
            {"error": {"type": "KeyError", "message": "boom", "code": 1}},
            "unsupported keys",
            id="extra-key",
        ),
        pytest.param(
            {"error": {"type": "KeyError", "message": "boom", "traceback": 1}},
            "error.traceback must be a string",
            id="non-str-traceback",
        ),
    ],
)
def test_error_dict_invariants(overrides, match):
    _assert_invalid(failed_tool_event, match, **overrides)


def test_error_must_be_null_when_ok():
    _assert_invalid(
        llm_call_event,
        "error must be null when status is 'ok'",
        error={"type": "KeyError", "message": "boom"},
    )


def test_error_status_is_boundary_only():
    _assert_invalid(root_input_event, "status must be 'ok' for root_input", status="error")
    _assert_invalid(final_output_event, "status must be 'ok' for final_output", status="error")


@pytest.mark.parametrize(
    ("overrides", "match"),
    [
        pytest.param({"argument_hash": None}, "argument_hash must be a 64-char", id="null-arg-hash"),
        pytest.param({"context_hash": None}, "context_hash must be a 64-char", id="null-ctx-hash"),
        pytest.param({"argument_hash": "ab" * 31}, "argument_hash must be a 64-char", id="short-hash"),
        pytest.param({"argument_hash": "AB" * 32}, "argument_hash must be a 64-char", id="uppercase-hash"),
        pytest.param({"context_hash": "zz" * 32}, "context_hash must be a 64-char", id="non-hex-hash"),
    ],
)
def test_hash_fields_required_on_non_metadata(overrides, match):
    _assert_invalid(llm_call_event, match, **overrides)


def test_latency_accepts_null_and_non_negative_ints():
    llm_call_event(latency_ms=None).validate()
    llm_call_event(latency_ms=0).validate()
    llm_call_event(latency_ms=12).validate()
