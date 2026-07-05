"""Determinism proofs for canonical JSON hashing (P0 roadmap: Hardened Determinism).

These tests pin the canonicalization contract: equivalent representations
hash identically, intentionally distinct representations stay distinct, and
the opt-in ``float_policy="reject"`` / ``float_hex`` escape hatch works.
"""

import json

import pytest

from flight_recorder.hashing import (
    FLOAT_POLICIES,
    argument_hash,
    canonical_json,
    context_hash,
    float_hex,
    validate_json_value,
)
from flight_recorder.recorder import Recorder
from flight_recorder.replayer import Replayer


# --- Equivalent representations hash identically -------------------------------


def test_float_arithmetic_and_literal_hash_identically():
    computed = 0.1 + 0.2
    literal = 0.30000000000000004
    assert computed == literal
    assert argument_hash("tool_call", "t", {"x": computed}) == argument_hash(
        "tool_call", "t", {"x": literal}
    )


def test_dict_insertion_order_is_irrelevant():
    forward = {"a": 1, "b": 2, "c": {"x": [1.5, 2.5]}}
    backward = {}
    backward["c"] = {"x": [1.5, 2.5]}
    backward["b"] = 2
    backward["a"] = 1
    assert canonical_json(forward) == canonical_json(backward)
    assert argument_hash("llm_call", "n", forward) == argument_hash("llm_call", "n", backward)


def test_json_roundtrip_preserves_canonical_text():
    # Serializing and re-parsing a payload must not change its hash: the
    # replayer hashes values decoded from disk against values built in memory.
    payload = {"pi": 3.141592653589793, "tiny": 5e-324, "big": 1.7976931348623157e308,
               "neg": -2.5, "int": 7, "text": "π"}
    roundtripped = json.loads(json.dumps(payload))
    assert canonical_json(payload) == canonical_json(roundtripped)


# --- Intentionally distinct representations stay distinct ----------------------


def test_int_and_integral_float_hash_differently():
    # 1 and 1.0 are different JSON texts ("1" vs "1.0"): type disambiguation
    # is deliberate, not a determinism leak.
    assert canonical_json(1) == "1"
    assert canonical_json(1.0) == "1.0"
    assert argument_hash("tool_call", "t", 1) != argument_hash("tool_call", "t", 1.0)


def test_negative_zero_hashes_differently_from_zero():
    # -0.0 is a distinct IEEE 754 value and canonicalizes as "-0.0"; pinned
    # so a platform where this changed would fail loudly.
    assert canonical_json(-0.0) == "-0.0"
    assert canonical_json(0.0) == "0.0"
    assert argument_hash("tool_call", "t", -0.0) != argument_hash("tool_call", "t", 0.0)


# --- Canonical text is platform-independent -------------------------------------


@pytest.mark.parametrize(
    ("value", "expected_text"),
    [
        (0.1, "0.1"),
        (0.1 + 0.2, "0.30000000000000004"),
        (1e16, "1e+16"),
        (1e-5, "1e-05"),
        (5e-324, "5e-324"),  # smallest subnormal
        (1.7976931348623157e308, "1.7976931348623157e+308"),  # largest double
        (123456789.123456789, "123456789.12345679"),
        (-2.5, "-2.5"),
        (3.141592653589793, "3.141592653589793"),
    ],
)
def test_float_canonical_text_is_pinned(value, expected_text):
    # CPython's float repr is the shortest round-trip form (PEP-compliant
    # since 3.1) and platform-independent; these hardcoded expectations prove
    # the canonical text — and therefore the hash — matches across machines.
    assert canonical_json(value) == expected_text


# --- float_policy="reject" and float_hex -----------------------------------------


def test_float_policies_constant():
    assert FLOAT_POLICIES == ("allow", "reject")


def test_reject_policy_refuses_floats_with_pointer_to_float_hex():
    with pytest.raises(ValueError, match=r"float_policy='reject'.*float_hex"):
        validate_json_value({"x": [1.5]}, float_policy="reject")
    with pytest.raises(ValueError, match="float_policy='reject'"):
        argument_hash("tool_call", "t", {"x": 1.5}, float_policy="reject")
    with pytest.raises(ValueError, match="float_policy='reject'"):
        context_hash([], "root_input", None, 1.5, None, "ok", None, float_policy="reject")


def test_reject_policy_still_allows_ints_and_strings():
    validate_json_value({"x": [1, "1.5", True, None]}, float_policy="reject")


def test_unknown_float_policy_rejected():
    with pytest.raises(ValueError, match="float_policy must be one of"):
        canonical_json(1, float_policy="strict")


def test_float_hex_roundtrips_and_rejects_non_floats():
    for value in (0.1, -0.0, 5e-324, 1.7976931348623157e308, 3.5):
        text = float_hex(value)
        # Bit-exact round trip: same IEEE 754 representation, sign included.
        assert float.fromhex(text).hex() == value.hex()
    with pytest.raises(TypeError):
        float_hex(1)
    with pytest.raises(ValueError):
        float_hex(float("nan"))


def test_recorder_reject_policy_fails_on_float_payload(tmp_path):
    trace = tmp_path / "trace.jsonl"
    with pytest.raises(ValueError, match="float_policy='reject'"):
        with Recorder(agent_id="a", capture_to=trace, float_policy="reject") as rec:
            rec.record_root_input({"temperature": 0.7})
            rec.record_final_output({"done": True}, [])


def test_recorder_and_replayer_reject_policy_roundtrip(tmp_path):
    trace = tmp_path / "trace.jsonl"
    with Recorder(agent_id="a", capture_to=trace, float_policy="reject") as rec:
        root_id = rec.record_root_input({"temperature": float_hex(0.7)})
        rec.record_final_output({"done": True}, [root_id])
    with Replayer(trace_file=trace, float_policy="reject") as rep:
        root_id = rep.record_root_input({"temperature": float_hex(0.7)})
        rep.record_final_output({"done": True}, [root_id])


def test_recorder_invalid_float_policy_rejected(tmp_path):
    with pytest.raises(ValueError, match="float_policy must be one of"):
        Recorder(agent_id="a", capture_to=tmp_path / "t.jsonl", float_policy="bogus")
    with pytest.raises(ValueError, match="float_policy must be one of"):
        Replayer(trace_file=tmp_path / "t.jsonl", float_policy="bogus")
