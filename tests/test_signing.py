"""HMAC-SHA256 trace signing tests (P0 roadmap: Security)."""

import json

import pytest

from flight_recorder.recorder import Recorder
from flight_recorder.replayer import Replayer
from flight_recorder.signing import (
    SIGNING_KEY_ENV_VAR,
    resolve_signing_key,
    sign_event,
    verify_signatures,
)
from flight_recorder.storage import read_events

from conftest import make_trace

KEY = b"test-signing-key"


def _record_signed_trace(path, signing_key=KEY):
    with Recorder(agent_id="demo-agent", capture_to=path, signing_key=signing_key) as rec:
        root_id = rec.record_root_input({"query": "hi"})
        _, llm_id = rec.record_llm_call(
            "llm_plan", {"prompt": "plan"}, lambda: {"plan": ["x"]}, [root_id]
        )
        rec.record_final_output({"answer": "done"}, [llm_id])
    return read_events(path)


# --- key resolution -------------------------------------------------------------


def test_resolve_signing_key_precedence(monkeypatch):
    monkeypatch.setenv(SIGNING_KEY_ENV_VAR, "env-key")
    assert resolve_signing_key("explicit") == b"explicit"
    assert resolve_signing_key(b"raw") == b"raw"
    assert resolve_signing_key(None) == b"env-key"
    monkeypatch.delenv(SIGNING_KEY_ENV_VAR)
    assert resolve_signing_key(None) is None


def test_resolve_signing_key_rejects_empty_and_wrong_type():
    with pytest.raises(ValueError, match="non-empty"):
        resolve_signing_key("")
    with pytest.raises(ValueError, match="non-empty"):
        resolve_signing_key(b"")
    with pytest.raises(TypeError, match="bytes or str"):
        resolve_signing_key(123)


# --- sign + verify round trip -----------------------------------------------------


def test_signed_trace_verifies(tmp_path):
    events = _record_signed_trace(tmp_path / "trace.jsonl")
    assert all(event.signature is not None for event in events)
    verify_signatures(events, KEY)
    verify_signatures(events, KEY, require=True)


def test_signed_trace_replays(tmp_path):
    trace = tmp_path / "trace.jsonl"
    _record_signed_trace(trace)
    with Replayer(trace_file=trace, signing_key=KEY, require_signatures=True) as rep:
        root_id = rep.record_root_input({"query": "hi"})
        response, llm_id = rep.record_llm_call(
            "llm_plan", {"prompt": "plan"}, lambda: None, [root_id]
        )
        rep.record_final_output({"answer": "done"}, [llm_id])
    assert response == {"plan": ["x"]}


def test_wrong_key_detected(tmp_path):
    events = _record_signed_trace(tmp_path / "trace.jsonl")
    with pytest.raises(ValueError, match="does not verify"):
        verify_signatures(events, b"other-key")


def test_replayer_rejects_tampered_trace_at_entry(tmp_path):
    trace = tmp_path / "trace.jsonl"
    _record_signed_trace(trace)
    with pytest.raises(ValueError, match="does not verify"):
        Replayer(trace_file=trace, signing_key=b"other-key").__enter__()


# --- tampering scenarios ----------------------------------------------------------


def test_tampered_payload_detected(tmp_path):
    """Editing a payload and recomputing the hashes still fails: the HMAC over
    context_hash cannot be forged without the key."""
    trace = tmp_path / "trace.jsonl"
    _record_signed_trace(trace)
    lines = [json.loads(line) for line in trace.read_text().splitlines()]
    # Attacker edits the recorded response and recomputes both hashes so
    # verify_hashes passes.
    from flight_recorder.hashing import argument_hash, context_hash

    root, llm = lines[1], lines[2]
    llm["historical_response"] = {"plan": ["FORGED"]}
    root_ctx = context_hash([], "root_input", None, root["payload"], None, "ok", None)
    llm["context_hash"] = context_hash(
        [root_ctx], "llm_call", "llm_plan", llm["payload"],
        llm["historical_response"], "ok", None,
    )
    lines[2] = llm
    trace.write_text("".join(json.dumps(l) + "\n" for l in lines))

    events = read_events(trace)
    with pytest.raises(ValueError, match="does not verify"):
        verify_signatures(events, KEY)


def test_cross_trace_splice_detected(tmp_path):
    """An event signed in one trace cannot be spliced into another: run_id is
    part of the signed projection, and validate_trace forces a single run_id
    per file, so the attacker must rewrite it — which breaks the signature."""
    events_a = _record_signed_trace(tmp_path / "a.jsonl")
    events_b = _record_signed_trace(tmp_path / "b.jsonl")
    foreign = events_b[2]
    foreign.run_id = events_a[0].run_id  # blend into trace a
    spliced = events_a[:2] + [foreign] + events_a[3:]
    with pytest.raises(ValueError, match="does not verify"):
        verify_signatures(spliced, KEY)


def test_resequenced_event_detected(tmp_path):
    """Moving a signed event to a different sequence position is detected:
    call_sequence_index is part of the signed projection."""
    events = _record_signed_trace(tmp_path / "trace.jsonl")
    moved = events[2]
    moved.call_sequence_index = 3
    with pytest.raises(ValueError, match="does not verify"):
        verify_signatures([moved], KEY)


def test_tampered_metadata_payload_detected(tmp_path):
    """The metadata event has null hashes, so its payload is signed directly."""
    events = _record_signed_trace(tmp_path / "trace.jsonl")
    events[0].payload["agent_id"] = "someone-else"
    events[0].agent_id = "someone-else"
    with pytest.raises(ValueError, match="does not verify"):
        verify_signatures(events, KEY)


# --- backward compatibility --------------------------------------------------------


def test_unsigned_trace_passes_unless_required():
    events = make_trace()
    verify_signatures(events, KEY)  # unsigned events pass without require
    with pytest.raises(ValueError, match="unsigned but"):
        verify_signatures(events, KEY, require=True)


def test_unsigned_trace_bytes_unchanged(tmp_path):
    """No signing key: the written JSON lines carry no signature field at all."""
    trace = tmp_path / "trace.jsonl"
    with Recorder(agent_id="demo-agent", capture_to=trace) as rec:
        root_id = rec.record_root_input({"query": "hi"})
        rec.record_final_output({"answer": "done"}, [root_id])
    for line in trace.read_text().splitlines():
        assert "signature" not in json.loads(line)


def test_old_fixture_trace_still_loads_and_validates():
    events = read_events("tests/fixtures/example_trace.jsonl")
    assert all(event.signature is None for event in events)


def test_signature_field_validated():
    events = make_trace()
    events[1].signature = "not-hex"
    with pytest.raises(ValueError, match="signature must be null or a 64-char"):
        events[1].validate()


def test_sign_event_is_deterministic(tmp_path):
    events = _record_signed_trace(tmp_path / "trace.jsonl")
    for event in events:
        assert sign_event(event, KEY) == event.signature


def test_require_signatures_needs_a_key(tmp_path, monkeypatch):
    monkeypatch.delenv(SIGNING_KEY_ENV_VAR, raising=False)
    with pytest.raises(ValueError, match="needs a signing key"):
        Replayer(trace_file=tmp_path / "t.jsonl", require_signatures=True)


def test_cli_validate_signatures(tmp_path, monkeypatch, capsys):
    from flight_recorder.cli import main

    trace = tmp_path / "trace.jsonl"
    _record_signed_trace(trace, signing_key="cli-key")

    # Without a key: validates as before, no signatures_verified in output.
    monkeypatch.delenv(SIGNING_KEY_ENV_VAR, raising=False)
    assert main(["validate", str(trace)]) == 0
    assert "signatures_verified" not in json.loads(capsys.readouterr().out)

    # --require-signatures without a key is an explicit error.
    assert main(["validate", str(trace), "--require-signatures"]) == 1
    assert "AGENT_M2_SIGNING_KEY" in capsys.readouterr().out

    # With the right key: verified.
    monkeypatch.setenv(SIGNING_KEY_ENV_VAR, "cli-key")
    assert main(["validate", str(trace), "--require-signatures"]) == 0
    assert json.loads(capsys.readouterr().out)["signatures_verified"] is True

    # With the wrong key: invalid.
    monkeypatch.setenv(SIGNING_KEY_ENV_VAR, "wrong-key")
    assert main(["validate", str(trace)]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "invalid"


def test_recorder_picks_up_env_key(tmp_path, monkeypatch):
    monkeypatch.setenv(SIGNING_KEY_ENV_VAR, "env-key")
    trace = tmp_path / "trace.jsonl"
    with Recorder(agent_id="demo-agent", capture_to=trace) as rec:
        root_id = rec.record_root_input({"query": "hi"})
        rec.record_final_output({"answer": "done"}, [root_id])
    events = read_events(trace)
    verify_signatures(events, b"env-key", require=True)
