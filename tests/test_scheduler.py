"""DagScheduler unit tests: readiness, unlocking, guards, liveness (DESIGN-SESSION-4 §2).

Shapes are built with the hash-consistent conftest builders. The scheduler
is specified over validated flight-recorder traces (metadata first, root
second, parents at strictly lower sequence indices), not arbitrary DAGs.
"""

import uuid

import pytest

from conftest import make_event, make_metadata
from flight_recorder.errors import FlightRecorderError, SchedulingError
from flight_recorder.replayer import DagScheduler


def chain_trace():
    """metadata -> root -> A -> B -> final (single path)."""
    meta = make_metadata()
    root = make_event(meta, 1, "root_input", payload={"q": 1})
    a = make_event(meta, 2, "llm_call", name="a", payload={"p": 1},
                   parents=[root], historical_response={"r": 1})
    b = make_event(meta, 3, "tool_call", name="b", payload={"p": 2},
                   parents=[a], historical_response={"r": 2})
    final = make_event(meta, 4, "final_output", payload={"answer": 1}, parents=[b])
    return [meta, root, a, b, final]


def diamond_trace():
    """metadata -> root -> {A, B} -> C -> final (C needs both A and B)."""
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


# --- construction and initial readiness -------------------------------------------


def test_initial_ready_set_is_parentless_events_only():
    events = diamond_trace()
    scheduler = DagScheduler(events)
    ready = scheduler.ready_events()
    assert [e.event_id for e in ready] == [events[1].event_id]  # root only


def test_metadata_is_never_schedulable():
    events = chain_trace()
    scheduler = DagScheduler(events)
    meta_id = events[0].event_id
    assert meta_id not in [e.event_id for e in scheduler.pending]
    with pytest.raises(SchedulingError):
        scheduler.is_ready(meta_id)


def test_pending_is_all_non_metadata_events_in_sequence_order():
    events = diamond_trace()
    scheduler = DagScheduler(events)
    assert [e.event_id for e in scheduler.pending] == [e.event_id for e in events[1:]]
    assert scheduler.done is False


# --- unlocking ------------------------------------------------------------------


def test_child_unlocks_only_when_last_parent_completes():
    events = diamond_trace()
    meta, root, a, b, c, final = events
    scheduler = DagScheduler(events)
    scheduler.complete(root.event_id)
    assert scheduler.is_ready(a.event_id) and scheduler.is_ready(b.event_id)
    assert not scheduler.is_ready(c.event_id)

    scheduler.complete(a.event_id)
    assert not scheduler.is_ready(c.event_id)  # b still pending

    scheduler.complete(b.event_id)
    assert scheduler.is_ready(c.event_id)
    assert not scheduler.is_ready(final.event_id)


def test_completed_chain_drains_to_done():
    events = chain_trace()
    scheduler = DagScheduler(events)
    for event in events[1:]:
        assert scheduler.is_ready(event.event_id)
        scheduler.complete(event.event_id)
    assert scheduler.done is True
    assert scheduler.pending == []
    assert scheduler.ready_events() == []


def test_is_ready_is_false_for_consumed_events():
    events = chain_trace()
    scheduler = DagScheduler(events)
    root_id = events[1].event_id
    scheduler.complete(root_id)
    assert scheduler.is_ready(root_id) is False


def test_scheduling_error_is_a_flight_recorder_error():
    assert issubclass(SchedulingError, FlightRecorderError)


# --- guards ----------------------------------------------------------------------


def fanout_trace(width=4):
    """metadata -> root -> llm -> {tool_0..tool_n} -> final (wide independent siblings)."""
    meta = make_metadata()
    root = make_event(meta, 1, "root_input", payload={"q": 1})
    llm = make_event(meta, 2, "llm_call", name="plan", payload={"p": 0},
                     parents=[root], historical_response={"r": 0})
    tools = [
        make_event(meta, 3 + i, "tool_call", name=f"tool_{i}", payload={"i": i},
                   parents=[llm], historical_response={"r": i})
        for i in range(width)
    ]
    final = make_event(meta, 3 + width, "final_output",
                       payload={"answer": 1}, parents=tools)
    return [meta, root, llm, *tools, final]


def duplicates_trace():
    """Two identical (type, name, payload, parents) events at different sequences."""
    meta = make_metadata()
    root = make_event(meta, 1, "root_input", payload={"q": 1})
    t1 = make_event(meta, 2, "tool_call", name="t", payload={"p": 1},
                    parents=[root], historical_response={"r": "first"})
    t2 = make_event(meta, 3, "tool_call", name="t", payload={"p": 1},
                    parents=[root], historical_response={"r": "second"})
    final = make_event(meta, 4, "final_output", payload={"answer": 1}, parents=[t1, t2])
    return [meta, root, t1, t2, final]


def test_complete_unknown_id_raises():
    scheduler = DagScheduler(chain_trace())
    with pytest.raises(SchedulingError, match="unknown event_id"):
        scheduler.complete(str(uuid.uuid4()))


def test_complete_twice_raises():
    events = chain_trace()
    scheduler = DagScheduler(events)
    scheduler.complete(events[1].event_id)
    with pytest.raises(SchedulingError, match="already completed"):
        scheduler.complete(events[1].event_id)


def test_complete_non_ready_raises_and_names_missing_parents():
    events = diamond_trace()
    scheduler = DagScheduler(events)
    with pytest.raises(SchedulingError, match="not ready"):
        scheduler.complete(events[4].event_id)  # C before root/A/B


def test_constructor_rejects_duplicate_event_ids():
    import dataclasses

    events = chain_trace()
    clone = dataclasses.replace(events[3], event_id=events[2].event_id)
    with pytest.raises(SchedulingError, match="duplicate event_id"):
        DagScheduler([events[0], events[1], events[2], clone])


def test_constructor_rejects_unknown_parent():
    import dataclasses

    events = chain_trace()
    orphan = dataclasses.replace(events[2], parent_event_ids=[str(uuid.uuid4())])
    with pytest.raises(SchedulingError, match="not a schedulable event"):
        DagScheduler([events[0], events[1], orphan])


def test_constructor_rejects_metadata_as_parent():
    import dataclasses

    events = chain_trace()
    bad = dataclasses.replace(events[2], parent_event_ids=[events[0].event_id])
    with pytest.raises(SchedulingError, match="not a schedulable event"):
        DagScheduler([events[0], events[1], bad])


def test_query_guards_on_unknown_ids():
    scheduler = DagScheduler(chain_trace())
    with pytest.raises(SchedulingError, match="unknown event_id"):
        scheduler.is_ready("not-an-id")
    with pytest.raises(SchedulingError, match="unknown event_id"):
        scheduler.missing_parents("not-an-id")


# --- missing_parents -------------------------------------------------------------


def test_missing_parents_preserves_recorded_order_and_shrinks():
    events = diamond_trace()
    meta, root, a, b, c, final = events
    scheduler = DagScheduler(events)
    assert scheduler.missing_parents(c.event_id) == [a.event_id, b.event_id]
    scheduler.complete(root.event_id)
    scheduler.complete(a.event_id)
    assert scheduler.missing_parents(c.event_id) == [b.event_id]
    scheduler.complete(b.event_id)
    assert scheduler.missing_parents(c.event_id) == []


# --- liveness property ------------------------------------------------------------


@pytest.mark.parametrize(
    "build", [chain_trace, diamond_trace, fanout_trace, duplicates_trace]
)
@pytest.mark.parametrize("policy", ["lowest", "highest"])
def test_ready_set_never_empty_until_drained(build, policy):
    """Theorem 1: any adversarial-but-legal drain policy reaches done."""
    events = build()
    scheduler = DagScheduler(events)
    consumed_count = 0
    while not scheduler.done:
        ready = scheduler.ready_events()
        assert ready, "ready set empty while events remain pending (liveness violated)"
        pick = ready[0] if policy == "lowest" else ready[-1]
        scheduler.complete(pick.event_id)
        consumed_count += 1
    assert consumed_count == len(events) - 1  # everything but metadata
    assert scheduler.pending == []
