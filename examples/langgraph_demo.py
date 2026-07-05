"""Self-contained LangGraph-style Agent-RR demo.

This file intentionally uses tiny fake runnables instead of real LangGraph,
LangChain, OpenAI, or Anthropic dependencies. The integration points are the
same ones a LangGraph app uses: graph.invoke(), model.invoke(), and tool.invoke().

Run:

    python examples/langgraph_demo.py
"""

from __future__ import annotations

from pathlib import Path
import sys
from tempfile import gettempdir
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from flight_recorder.errors import ReplayDivergence
from flight_recorder.integrations.langchain import run_agent_rr, wrap_llm, wrap_tool
from flight_recorder.recorder import Recorder
from flight_recorder.replayer import Replayer


class FakeSupportModel:
    name = "support_model"

    def invoke(self, input: dict[str, Any], config: dict | None = None, **kwargs: Any) -> dict:
        stage = input["stage"]
        if stage == "plan":
            return {
                "customer_id": "cust_123",
                "actions": ["lookup_customer", "fetch_orders"],
            }
        if stage == "summarize":
            customer = input["customer"]
            orders = input["orders"]
            total = sum(order["total"] for order in orders)
            return {
                "answer": (
                    f"{customer['name']} has {len(orders)} recent orders "
                    f"worth ${total} total. Offer priority support."
                )
            }
        raise ValueError(f"unknown support model stage: {stage}")


class FakeTool:
    def __init__(self, name: str, func):
        self.name = name
        self._func = func

    def invoke(self, input: dict[str, Any], config: dict | None = None, **kwargs: Any) -> Any:
        return self._func(input)


def lookup_customer(input: dict[str, Any]) -> dict:
    return {
        "customer_id": input["customer_id"],
        "name": "Ada Lovelace",
        "tier": "enterprise",
    }


def fetch_orders(input: dict[str, Any]) -> list[dict]:
    limit = input["limit"]
    orders = [
        {"id": "ord_1", "total": 199},
        {"id": "ord_2", "total": 299},
        {"id": "ord_3", "total": 499},
        {"id": "ord_4", "total": 149},
        {"id": "ord_5", "total": 249},
    ]
    return orders[:limit]


class CustomerSupportGraph:
    """A LangGraph-shaped compiled graph with a single .invoke() entrypoint."""

    def __init__(
        self,
        model: Any,
        tools: dict[str, Any],
        *,
        prompt_version: str = "v1",
        order_limit: int = 5,
    ):
        self._model = model
        self._tools = tools
        self._prompt_version = prompt_version
        self._order_limit = order_limit

    def invoke(self, payload: dict[str, Any]) -> dict:
        plan = self._model.invoke(
            {
                "stage": "plan",
                "prompt": (
                    f"{self._prompt_version}: decide which customer-support "
                    f"actions answer this query"
                ),
                "query": payload["query"],
            }
        )
        customer = self._tools["lookup_customer"].invoke(
            {"customer_id": plan["customer_id"]}
        )
        orders = self._tools["fetch_orders"].invoke(
            {"customer_id": plan["customer_id"], "limit": self._order_limit}
        )
        return self._model.invoke(
            {
                "stage": "summarize",
                "prompt": f"{self._prompt_version}: write a concise support summary",
                "customer": customer,
                "orders": orders,
            }
        )


def build_graph(*, prompt_version: str = "v1", order_limit: int = 5) -> CustomerSupportGraph:
    # 3-line integration:
    model = wrap_llm(FakeSupportModel(), name="support_model")
    tools = {
        "lookup_customer": wrap_tool(FakeTool("lookup_customer", lookup_customer)),
        "fetch_orders": wrap_tool(FakeTool("fetch_orders", fetch_orders)),
    }
    return CustomerSupportGraph(
        model,
        tools,
        prompt_version=prompt_version,
        order_limit=order_limit,
    )


def run_demo(trace_file: Path) -> None:
    payload = {"query": "Customer cust_123 says their last order was late."}

    with Recorder(
        agent_id="langgraph-support-demo",
        capture_to=trace_file,
        overwrite=True,
    ) as rr:
        recorded = run_agent_rr(rr, payload, build_graph())
    print("recorded:", recorded["answer"])

    with Replayer(trace_file=trace_file) as rr:
        replayed = run_agent_rr(rr, payload, build_graph())
    print("replayed:", replayed["answer"])

    try:
        with Replayer(trace_file=trace_file) as rr:
            run_agent_rr(rr, payload, build_graph(prompt_version="v2"))
    except ReplayDivergence as exc:
        print("divergence:", exc.reason)
        print("at_sequence_index:", exc.at_sequence_index)


if __name__ == "__main__":
    run_demo(Path(gettempdir()) / "agent_rr_langgraph_demo.jsonl")
