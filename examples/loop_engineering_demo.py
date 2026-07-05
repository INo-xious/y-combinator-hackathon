"""Self-contained Agent-RR demo for hand-rolled agent loops.

Run:

    python examples/loop_engineering_demo.py
"""

from __future__ import annotations

from pathlib import Path
import sys
from tempfile import gettempdir
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from flight_recorder.errors import ReplayDivergence
from flight_recorder.loops import LoopRun
from flight_recorder.recorder import Recorder
from flight_recorder.replayer import Replayer


def _poison(name: str):
    raise AssertionError(f"{name} should not execute during replay")


def fake_reasoner(payload: dict[str, Any], *, poison: bool = False) -> dict[str, Any]:
    if poison:
        _poison("fake_reasoner")
    print(f"executed fake_reasoner iteration={payload['iteration']}")
    if payload["iteration"] == 1:
        return {
            "thought": "Find the customer before drafting a reply.",
            "tool": "lookup_customer",
            "customer_id": "cust_123",
        }
    return {
        "thought": "Use the customer tier to draft a support response.",
        "tool": "draft_reply",
    }


def lookup_customer(customer_id: str, *, poison: bool = False) -> dict[str, Any]:
    if poison:
        _poison("lookup_customer")
    print(f"executed lookup_customer customer_id={customer_id}")
    return {
        "customer_id": customer_id,
        "name": "Ada Lovelace",
        "tier": "enterprise",
    }


def draft_reply(
    customer: dict[str, Any],
    ticket: str,
    *,
    tone: str,
    poison: bool = False,
) -> dict[str, str]:
    if poison:
        _poison("draft_reply")
    print(f"executed draft_reply tone={tone}")
    return {
        "reply": (
            f"{tone.title()} reply for {customer['name']}: "
            f"we reviewed ticket {ticket} and will prioritize it."
        )
    }


def run_loop_agent(rr: Any, *, tone: str = "friendly", poison: bool = False) -> dict[str, str]:
    loop = LoopRun.start(
        rr,
        {
            "ticket_id": "ticket_42",
            "message": "My enterprise support ticket has not moved.",
        },
    )

    first = loop.step()
    plan, _plan_id = first.llm(
        "think",
        {"iteration": 1, "goal": "choose first support action"},
        lambda: fake_reasoner(
            {"iteration": 1, "goal": "choose first support action"}, poison=poison
        ),
    )
    customer, _customer_id = first.tool(
        "lookup_customer",
        {"customer_id": plan["customer_id"]},
        lambda: lookup_customer(plan["customer_id"], poison=poison),
    )

    second = loop.step()
    next_action, _next_action_id = second.llm(
        "think",
        {
            "iteration": 2,
            "customer_tier": customer["tier"],
            "available_context": ["ticket", "customer"],
        },
        lambda: fake_reasoner(
            {
                "iteration": 2,
                "customer_tier": customer["tier"],
                "available_context": ["ticket", "customer"],
            },
            poison=poison,
        ),
    )
    reply, _reply_id = second.tool(
        next_action["tool"],
        {"customer_id": customer["customer_id"], "ticket_id": "ticket_42", "tone": tone},
        lambda: draft_reply(
            customer,
            "ticket_42",
            tone=tone,
            poison=poison,
        ),
    )

    loop.final({"reply": reply["reply"]})
    return reply


def run_demo(trace_file: Path) -> None:
    print("recording loop trace")
    with Recorder("loop-engineering-demo", trace_file, overwrite=True) as rr:
        recorded = run_loop_agent(rr, tone="friendly")
    print("recorded:", recorded["reply"])

    print("\nreplaying with poison callables")
    with Replayer(trace_file) as rr:
        replayed = run_loop_agent(rr, tone="friendly", poison=True)
    print("replayed:", replayed["reply"])

    print("\nreplaying with intentional loop drift")
    try:
        with Replayer(trace_file) as rr:
            run_loop_agent(rr, tone="terse", poison=True)
    except ReplayDivergence as exc:
        print("divergence:", exc.reason)
        print("boundary:", exc.expected["name"])
        print("expected payload:", exc.expected["payload"])
        print("actual payload:", exc.actual["payload"])


if __name__ == "__main__":
    run_demo(Path(gettempdir()) / "agent_rr_loop_engineering_demo.jsonl")
