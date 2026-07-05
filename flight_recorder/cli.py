"""agent-m2 CLI entry point: record, replay, and validate commands.

The CLI is deliberately a thin proof surface over the library APIs: it runs a
deterministic in-process demo agent for ``record``/``replay`` and performs full
trace validation for ``validate``. Command results are one JSON object on
stdout so shell scripts and CI can consume them without parsing prose.
"""

from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from pathlib import Path
from typing import Any, Optional, Sequence

from .crypto import load_fernet_cipher
from .dag import validate_trace, verify_hashes
from .errors import ReplayDivergence
from .recorder import Recorder
from .report import TraceValidationReport
from .replayer import Replayer
from .signing import resolve_signing_key, verify_signatures
from .storage import iter_events, read_events
from .viewer import write_trace_html

DEMO_AGENT_ID = "demo-agent"
DEMO_QUERY = "Look up customer 123 and summarize their last 5 orders."


def _poison_call() -> Any:
    raise AssertionError("call() must not have been executed during replay")


def _call_returning(value: Any, *, execute_calls: bool):
    if execute_calls:
        return lambda: value
    return _poison_call


def _run_demo_agent(recorder_or_replayer: Any, *, execute_calls: bool) -> dict[str, str]:
    """Run the PLAN §4 customer-support demo against Recorder or Replayer."""
    root_id = recorder_or_replayer.record_root_input({"query": DEMO_QUERY})
    plan, llm1_id = recorder_or_replayer.record_llm_call(
        "llm_plan",
        {"prompt": "plan", "temperature": 0},
        _call_returning({"plan": ["lookup_customer", "fetch_orders"]}, execute_calls=execute_calls),
        [root_id],
    )
    customer, tool1_id = recorder_or_replayer.record_tool_call(
        "lookup_customer",
        {"customer_id": 123},
        _call_returning({"name": "Ada"}, execute_calls=execute_calls),
        [llm1_id],
    )
    orders, tool2_id = recorder_or_replayer.record_tool_call(
        "fetch_orders",
        {"customer_id": 123, "limit": 5},
        _call_returning({"orders": [1, 2, 3]}, execute_calls=execute_calls),
        [llm1_id],
    )
    answer, llm2_id = recorder_or_replayer.record_llm_call(
        "llm_summary",
        {"prompt": "summarize"},
        _call_returning({"answer": "3 recent orders"}, execute_calls=execute_calls),
        [llm1_id, tool1_id, tool2_id],
    )
    final_id = recorder_or_replayer.record_final_output(
        {"answer": answer["answer"]},
        [llm2_id],
    )
    return {
        "root": root_id,
        "llm1": llm1_id,
        "tool1": tool1_id,
        "tool2": tool2_id,
        "llm2": llm2_id,
        "final": final_id,
    }


def _emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def _reason_for(exc: Exception) -> str:
    if isinstance(exc, FileExistsError):
        return "file exists"
    return str(exc) or type(exc).__name__


def _error_payload(exc: Exception, trace_file: Path) -> dict[str, Any]:
    return {
        "status": "error",
        "reason": _reason_for(exc),
        "error_type": type(exc).__name__,
        "trace_file": str(trace_file),
    }


def _run_record(trace_file: Path, *, overwrite: bool) -> int:
    try:
        with Recorder(
            agent_id=DEMO_AGENT_ID,
            capture_to=trace_file,
            overwrite=overwrite,
        ) as recorder:
            _run_demo_agent(recorder, execute_calls=True)
            run_id = recorder.run_id
        events_count = sum(1 for _ in iter_events(trace_file))
    except Exception as exc:
        _emit(_error_payload(exc, trace_file))
        return 1

    _emit(
        {
            "status": "success",
            "trace_file": str(trace_file),
            "run_id": run_id,
            "events_count": events_count,
        }
    )
    return 0


def _run_replay(trace_file: Path) -> int:
    try:
        with Replayer(trace_file=trace_file, cipher=load_fernet_cipher()) as replayer:
            _run_demo_agent(replayer, execute_calls=False)
        report = replayer.report
    except ReplayDivergence as exc:
        # Humans get the pretty diagnosis on stderr; stdout stays one JSON
        # object so CI scripts keep parsing exactly what they did before.
        print(exc.pretty(), file=sys.stderr)
        payload = {"status": "divergence", **exc.detail(), "trace_file": str(trace_file)}
        _emit(payload)
        return 1
    except Exception as exc:
        _emit(_error_payload(exc, trace_file))
        return 1

    _emit(
        {
            "status": "success",
            "trace_file": str(trace_file),
            "run_id": report.run_id,
            "matched_events": len(report.matched_event_ids),
            "final_output_matched": report.final_output_matched,
        }
    )
    return 0


def _run_validate(trace_file: Path, *, require_signatures: bool = False) -> int:
    # The signing key only ever comes from the environment: a CLI flag would
    # leak the secret into shell history and process listings.
    signing_key = resolve_signing_key(None)
    try:
        # Encrypted traces decrypt with the AGENT_M2_ENCRYPTION_KEY env var;
        # without it, reading one fails with a message naming that variable.
        events = read_events(trace_file, cipher=load_fernet_cipher())
        validate_trace(events, require_complete=True)
        verify_hashes(events)
        signatures_verified: Optional[bool] = None
        if require_signatures and signing_key is None:
            raise ValueError(
                "--require-signatures needs a signing key: set AGENT_M2_SIGNING_KEY"
            )
        if signing_key is not None:
            verify_signatures(events, signing_key, require=require_signatures)
            signatures_verified = True
    except Exception as exc:
        report = TraceValidationReport(
            valid=False,
            events=0,
            hashes_verified=False,
            errors=[str(exc)],
        )
        payload = report.to_dict()
        payload["trace_file"] = str(trace_file)
        _emit(payload)
        return 1

    report = TraceValidationReport(
        valid=True,
        events=len(events),
        hashes_verified=True,
        signatures_verified=signatures_verified,
    )
    payload = report.to_dict()
    payload["trace_file"] = str(trace_file)
    _emit(payload)
    return 0


def _run_view(
    trace_file: Path,
    *,
    output_file: Optional[Path],
    open_browser: bool,
) -> int:
    try:
        events = read_events(trace_file, cipher=load_fernet_cipher())
        validate_trace(events, require_complete=True)
        verify_hashes(events)
        html_file = write_trace_html(events, trace_file, output_file)
    except Exception as exc:
        _emit(_error_payload(exc, trace_file))
        return 1

    opened = False
    if open_browser:
        # Browser launch failures (headless CI, no default browser) must not
        # fail the command: the HTML file already exists and is the product.
        try:
            opened = webbrowser.open(html_file.resolve().as_uri())
        except Exception:
            opened = False

    _emit(
        {
            "status": "success",
            "trace_file": str(trace_file),
            "html_file": str(html_file),
            "events_count": len(events),
            "opened": opened,
        }
    )
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-m2",
        description="Record, replay, and validate deterministic agent traces.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    record = subparsers.add_parser("record", help="run the deterministic demo with Recorder")
    record.add_argument("trace_file", type=Path)
    record.add_argument(
        "--overwrite",
        action="store_true",
        help="truncate an existing trace file before recording",
    )

    replay = subparsers.add_parser("replay", help="run the deterministic demo with Replayer")
    replay.add_argument("trace_file", type=Path)

    validate = subparsers.add_parser("validate", help="validate a trace file and hashes")
    validate.add_argument("trace_file", type=Path)
    validate.add_argument(
        "--require-signatures",
        action="store_true",
        help="fail unless every event carries a valid HMAC signature "
        "(key from AGENT_M2_SIGNING_KEY; never a flag, to keep it out of "
        "shell history)",
    )

    view = subparsers.add_parser(
        "view", help="render the trace's causal DAG to HTML and open it"
    )
    view.add_argument("trace_file", type=Path)
    view.add_argument(
        "--output",
        type=Path,
        default=None,
        help="HTML output path (default: trace file with .html suffix)",
    )
    view.add_argument(
        "--no-open",
        action="store_true",
        help="write the HTML file without opening a browser",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the ``agent-m2`` console script."""
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1

    if args.command == "record":
        return _run_record(args.trace_file, overwrite=args.overwrite)
    if args.command == "replay":
        return _run_replay(args.trace_file)
    if args.command == "validate":
        return _run_validate(
            args.trace_file,
            require_signatures=args.require_signatures,
        )
    if args.command == "view":
        return _run_view(
            args.trace_file,
            output_file=args.output,
            open_browser=not args.no_open,
        )
    parser.error(f"unknown command: {args.command}")
    return 2
