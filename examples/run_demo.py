"""Runs the demo agent end-to-end: record, replay, and divergence demonstration."""
import sys
from pathlib import Path

from flight_recorder.recorder import Recorder
from flight_recorder.replayer import Replayer
from flight_recorder.errors import ReplayDivergence
from examples.demo_agent import run_support_agent


def main():
    trace_file = Path("demo_trace.jsonl")
    query = "Look up customer 123 and summarize their last 5 orders."
    
    print("\n" + "=" * 80)
    print("PHASE 1: RECORDING")
    print("=" * 80)
    print("Running agent with Recorder (limit=5).")
    print("Notice that the fake tools and LLM actually execute:")
    print("-" * 40)
    with Recorder("demo-support", trace_file, overwrite=True) as rr:
        run_support_agent(rr, query, limit=5)
    print("-" * 40)
    print(f"✅ Recording complete. Trace saved to {trace_file}")
    
    print("\n" + "=" * 80)
    print("PHASE 2: REPLAYING (DETERMINISTIC)")
    print("=" * 80)
    print("Running exact same agent function with Replayer (limit=5).")
    print("The Replayer short-circuits functions and returns historical data.")
    print("EXPECTATION: NO 'EXECUTED' logs should appear below:")
    print("-" * 40)
    with Replayer(trace_file) as rr:
        run_support_agent(rr, query, limit=5)
    print("-" * 40)
    print("✅ Replay successful! The DAG matched the historical trace perfectly.")
    
    print("\n" + "=" * 80)
    print("PHASE 3: TIME-TRAVEL DEBUGGING (DIVERGENCE DETECTION)")
    print("=" * 80)
    print("Simulating a developer changing code logic: limit=3 instead of 5.")
    print("The Replayer will instantly detect this payload mismatch.")
    print("-" * 40)
    try:
        with Replayer(trace_file) as rr:
            run_support_agent(rr, query, limit=3)
        print("❌ ERROR: Replay succeeded but it should have diverged!")
        sys.exit(1)
    except ReplayDivergence as e:
        print("✅ Caught expected ReplayDivergence!")
        print("\n--- Divergence Details ---")
        print(e)
        print("--------------------------")
        
    print("\n🎉 Demo completed successfully. MVP Business Value Proven.\n")

if __name__ == "__main__":
    main()
