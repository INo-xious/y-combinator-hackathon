"""Payload encryption tests (P0 roadmap: Security).

A reversible in-test stub cipher keeps the suite independent of the optional
``cryptography`` dependency; one importorskip-gated test covers real Fernet.
"""

import base64
import json

import pytest

from flight_recorder.crypto import (
    ENCRYPTED_MARKER,
    decrypt_event_fields,
    encrypt_event_fields,
    is_encrypted_event_dict,
    load_fernet_cipher,
)
from flight_recorder.dag import validate_trace, verify_hashes
from flight_recorder.recorder import Recorder
from flight_recorder.replayer import Replayer
from flight_recorder.signing import verify_signatures
from flight_recorder.storage import read_events


class StubCipher:
    """Reversible stand-in cipher: base64 with a marker prefix."""

    alg = "stub-base64"

    def encrypt(self, text):
        return "stub:" + base64.b64encode(text.encode("utf-8")).decode("ascii")

    def decrypt(self, token):
        if not token.startswith("stub:"):
            raise ValueError("not a stub token")
        return base64.b64decode(token[len("stub:"):]).decode("utf-8")


SECRET = "the launch code is 0000"


def _record_trace(path, **recorder_kwargs):
    with Recorder(agent_id="demo-agent", capture_to=path, **recorder_kwargs) as rec:
        root_id = rec.record_root_input({"prompt": SECRET})
        _, llm_id = rec.record_llm_call(
            "llm_plan", {"prompt": SECRET}, lambda: {"answer": SECRET}, [root_id]
        )
        rec.record_final_output({"answer": "done"}, [llm_id])


def _replay_trace(path, **replayer_kwargs):
    with Replayer(trace_file=path, **replayer_kwargs) as rep:
        root_id = rep.record_root_input({"prompt": SECRET})
        response, llm_id = rep.record_llm_call(
            "llm_plan", {"prompt": SECRET}, lambda: None, [root_id]
        )
        rep.record_final_output({"answer": "done"}, [llm_id])
    return response


def test_encrypted_trace_hides_plaintext_on_disk(tmp_path):
    trace = tmp_path / "trace.jsonl"
    _record_trace(trace, cipher=StubCipher())
    raw = trace.read_text()
    assert SECRET not in raw
    assert ENCRYPTED_MARKER in raw
    # The metadata line stays plaintext so readers can identify the trace.
    first_line = json.loads(raw.splitlines()[0])
    assert not is_encrypted_event_dict(first_line)
    assert first_line["payload"]["schema_version"] == "1.0"


def test_encrypted_trace_roundtrips_and_replays(tmp_path):
    trace = tmp_path / "trace.jsonl"
    _record_trace(trace, cipher=StubCipher())

    events = read_events(trace, cipher=StubCipher())
    assert events[1].payload == {"prompt": SECRET}
    # Hashes were computed over plaintext and verify after decryption.
    validate_trace(events)
    verify_hashes(events)

    assert _replay_trace(trace, cipher=StubCipher()) == {"answer": SECRET}


def test_reading_encrypted_trace_without_cipher_fails(tmp_path):
    trace = tmp_path / "trace.jsonl"
    _record_trace(trace, cipher=StubCipher())
    with pytest.raises(ValueError, match="encrypted trace.*needs a cipher"):
        read_events(trace)
    with pytest.raises(ValueError, match="encrypted trace"):
        Replayer(trace_file=trace).__enter__()


def test_wrong_cipher_fails_with_clear_error(tmp_path):
    class OtherCipher(StubCipher):
        def decrypt(self, token):
            raise ValueError("bad key")

    trace = tmp_path / "trace.jsonl"
    _record_trace(trace, cipher=StubCipher())
    with pytest.raises(ValueError, match="failed to decrypt"):
        read_events(trace, cipher=OtherCipher())


def test_unencrypted_traces_unchanged(tmp_path):
    trace = tmp_path / "trace.jsonl"
    _record_trace(trace)
    raw = trace.read_text()
    assert SECRET in raw  # no cipher, no transform
    assert ENCRYPTED_MARKER not in raw
    # Passing a cipher for a plaintext trace is harmless.
    events = read_events(trace, cipher=StubCipher())
    verify_hashes(events)


def test_signing_and_encryption_compose(tmp_path):
    trace = tmp_path / "trace.jsonl"
    _record_trace(trace, cipher=StubCipher(), signing_key=b"key")
    events = read_events(trace, cipher=StubCipher())
    verify_hashes(events)
    verify_signatures(events, b"key", require=True)
    assert _replay_trace(
        trace, cipher=StubCipher(), signing_key=b"key", require_signatures=True
    ) == {"answer": SECRET}


def test_encrypt_decrypt_event_fields_are_inverse():
    data = {
        "event_type": "llm_call",
        "payload": {"prompt": SECRET},
        "historical_response": {"answer": 42},
        "error": None,
    }
    encrypted = encrypt_event_fields(data, StubCipher())
    assert ENCRYPTED_MARKER in encrypted["payload"]
    assert encrypted["payload"][ENCRYPTED_MARKER]["alg"] == "stub-base64"
    assert decrypt_event_fields(encrypted, StubCipher()) == data


def test_none_fields_stay_none():
    data = {"event_type": "root_input", "payload": {"q": 1}, "historical_response": None}
    encrypted = encrypt_event_fields(data, StubCipher())
    assert encrypted["historical_response"] is None
    assert ENCRYPTED_MARKER in encrypted["payload"]


def test_load_fernet_cipher_without_key_is_none(monkeypatch):
    monkeypatch.delenv("AGENT_M2_ENCRYPTION_KEY", raising=False)
    assert load_fernet_cipher() is None


def test_fernet_cipher_end_to_end(tmp_path):
    cryptography = pytest.importorskip("cryptography")
    from cryptography.fernet import Fernet

    key = Fernet.generate_key()
    trace = tmp_path / "trace.jsonl"
    _record_trace(trace, cipher=load_fernet_cipher(key))
    assert SECRET not in trace.read_text()
    assert _replay_trace(trace, cipher=load_fernet_cipher(key)) == {"answer": SECRET}
