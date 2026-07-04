"""Deterministic fake tools: pure functions of their payloads, no I/O."""

def lookup_customer(customer_id: str) -> dict:
    print("🛠️ FAKE_TOOL EXECUTED: lookup_customer")
    db = {
        "123": {"name": "Alice", "status": "Active"},
        "456": {"name": "Bob", "status": "Inactive"}
    }
    return db.get(customer_id, {"error": "not found"})

def fetch_orders(customer_id: str, limit: int) -> list:
    print(f"🛠️ FAKE_TOOL EXECUTED: fetch_orders (limit={limit})")
    orders = {
        "123": [
            {"id": "o1", "amount": 10.0},
            {"id": "o2", "amount": 20.0},
            {"id": "o3", "amount": 30.0},
            {"id": "o4", "amount": 25.0},
            {"id": "o5", "amount": 35.0},
            {"id": "o6", "amount": 50.0},
        ],
        "456": [
            {"id": "o7", "amount": 100.0},
        ]
    }
    return orders.get(customer_id, [])[:limit]
