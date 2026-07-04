"""Demo customer-support agent function taking a Recorder or Replayer."""
import json
from typing import Union

from flight_recorder.recorder import Recorder
from flight_recorder.replayer import Replayer
from examples.fake_llm import call_llm
from examples.fake_tools import lookup_customer, fetch_orders


def run_support_agent(rr: Union[Recorder, Replayer], query: str, limit: int = 5):
    """
    Executes a 7-event customer support flow:
    1. metadata (written automatically by Recorder on enter)
    2. root_input
    3. llm_call (planner)
    4. tool_call (lookup_customer)
    5. tool_call (fetch_orders)
    6. llm_call (summarizer)
    7. final_output
    """
    # 2. Root Input
    root_id = rr.record_root_input({"query": query, "limit": limit})
    
    # 3. LLM Planner
    planner_payload = {"prompt": f"User asked: {query}. How to proceed?"}
    response_str, llm1_id = rr.record_llm_call(
        "planner", 
        planner_payload, 
        lambda: call_llm(planner_payload["prompt"]), 
        [root_id]
    )
    
    # Parse the LLM's plan
    plan = json.loads(response_str)
    customer_id = plan["actions"][0]["args"]["customer_id"]
    
    # 4. Tool Call (lookup_customer)
    tool1_payload = {"customer_id": customer_id}
    customer_info, tool1_id = rr.record_tool_call(
        "lookup_customer",
        tool1_payload,
        lambda: lookup_customer(customer_id),
        [llm1_id]
    )
    
    # 5. Tool Call (fetch_orders)
    tool2_payload = {"customer_id": customer_id, "limit": limit}
    orders, tool2_id = rr.record_tool_call(
        "fetch_orders",
        tool2_payload,
        lambda: fetch_orders(customer_id, limit),
        [llm1_id]
    )
    
    # 6. LLM Summarizer
    summarizer_payload = {
        "prompt": f"Summarize the customer data. Name: {customer_info.get('name', 'Unknown')}",
        "customer": customer_info,
        "orders": orders
    }
    summary, llm2_id = rr.record_llm_call(
        "summarizer",
        summarizer_payload,
        lambda: call_llm(summarizer_payload["prompt"]),
        [llm1_id, tool1_id, tool2_id]
    )
    
    # 7. Final Output
    rr.record_final_output(summary, [llm2_id])
    return summary
