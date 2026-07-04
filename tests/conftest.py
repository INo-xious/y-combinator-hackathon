"""Shared hash-consistent trace builders for storage/dag/recorder tests.

These build events by hand (rather than through the Recorder) so tests can
construct arbitrary — including deliberately broken — trace shapes.
"""

import uuid

from flight_recorder.events import RECORDER_VERSION, SCHEMA_VERSION, TraceEvent
from flight_recorder.hashing import argument_hash, context_hash

TS = "2026-07-04T12:00:00Z"
AGENT_ID = "demo-agent"


def make_metadata(run_id=None, agent_id=AGENT_ID) -> TraceEvent:
    run_id = run_id or str(uuid.uuid4())
    return TraceEvent(
        event_id=str(uuid.uuid4()),
        run_id=run_id,
        agent_id=agent_id,
        parent_event_ids=[],
        call_sequence_index=0,
        event_type="metadata",
        name=None,
        timestamp=TS,
        payload={
            "schema_version": SCHEMA_VERSION,
            "recorder_version": RECORDER_VERSION,
            "trace_creation_time": TS,
            "run_id": run_id,
            "agent_id": agent_id,
        },
        historical_response=None,
        status="ok",
        error=None,
        argument_hash=None,
        context_hash=None,
        latency_ms=None,
    )


def make_event(
    metadata: TraceEvent,
    sequence: int,
    event_type: str,
    *,
    name=None,
    payload=None,
    parents=(),
    historical_response=None,
    status="ok",
    error=None,
    latency_ms=None,
) -> TraceEvent:
    """Build a hash-consistent event; *parents* are TraceEvent objects whose
    ids and context hashes are chained in the given order."""
    return TraceEvent(
        event_id=str(uuid.uuid4()),
        run_id=metadata.run_id,
        agent_id=metadata.agent_id,
        parent_event_ids=[p.event_id for p in parents],
        call_sequence_index=sequence,
        event_type=event_type,
        name=name,
        timestamp=TS,
        payload=payload,
        historical_response=historical_response,
        status=status,
        error=error,
        argument_hash=argument_hash(event_type, name, payload),
        context_hash=context_hash(
            [p.context_hash for p in parents],
            event_type,
            name,
            payload,
            historical_response,
            status,
            error,
        ),
        latency_ms=latency_ms,
    )


def make_trace(agent_id=AGENT_ID) -> list[TraceEvent]:
    """metadata → root_input → llm_call (ok) → tool_call (error) →
    final_output with two ordered parents [llm, tool]."""
    meta = make_metadata(agent_id=agent_id)
    root = make_event(meta, 1, "root_input", payload={"query": "look up customer 123"})
    llm = make_event(
        meta,
        2,
        "llm_call",
        name="llm_plan",
        payload={"prompt": "plan"},
        parents=[root],
        historical_response={"plan": ["fetch_orders"]},
        latency_ms=12,
    )
    tool = make_event(
        meta,
        3,
        "tool_call",
        name="fetch_orders",
        payload={"customer_id": 123},
        parents=[llm],
        status="error",
        error={"type": "KeyError", "message": "'orders'"},
        latency_ms=3,
    )
    final = make_event(meta, 4, "final_output", payload={"answer": "done"}, parents=[llm, tool])
    return [meta, root, llm, tool, final]
