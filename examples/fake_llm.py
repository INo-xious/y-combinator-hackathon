"""Deterministic fake LLM: pure dict-lookup responses, no network."""

def call_llm(prompt: str) -> str:
    print("🤖 FAKE_LLM EXECUTED")
    
    if "how to proceed" in prompt.lower() and "customer 123" in prompt.lower():
        return '{"actions": [{"tool": "lookup_customer", "args": {"customer_id": "123"}}, {"tool": "fetch_orders", "args": {"customer_id": "123"}}]}'
    
    if "summarize" in prompt.lower() and "alice" in prompt.lower():
        return "Customer Alice (Active) has 5 recent orders totaling $120.00."
    
    if "summarize" in prompt.lower() and "bob" in prompt.lower():
        return "Customer Bob (Inactive) has 3 recent orders."
        
    return "I do not understand the prompt."
