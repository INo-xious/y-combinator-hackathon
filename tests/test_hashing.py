"""Canonical JSON strictness and golden-hash stability tests (PLAN §6, §8).

The golden fixture pins the exact canonical strings and SHA-256 digests: any
accidental change to canonicalization (key order, separators, escaping,
float repr, hash input shape) fails these tests instead of silently breaking
every existing trace.
"""

import hashlib
import json
from collections import OrderedDict
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from flight_recorder.hashing import (
    argument_hash,
    canonical_json,
    context_hash,
    validate_json_value,
)

GOLDEN_PATH = Path(__file__).parent / "fixtures" / "golden_hashes.json"
GOLDEN = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

HEX64 = "ab" * 32
HEX64_OTHER = "cd" * 32


def _ids(cases):
    return [case["description"] for case in cases]


# --- Golden fixtures -------------------------------------------------------


def test_golden_fixture_is_populated():
    assert len(GOLDEN["canonical"]) >= 7
    assert len(GOLDEN["argument_hash"]) >= 4
    assert len(GOLDEN["context_hash"]) >= 4


@pytest.mark.parametrize("case", GOLDEN["canonical"], ids=_ids(GOLDEN["canonical"]))
def test_golden_canonical_json(case):
    canon = canonical_json(case["input"])
    assert canon == case["canonical"]
    assert hashlib.sha256(canon.encode("utf-8")).hexdigest() == case["sha256"]


@pytest.mark.parametrize("case", GOLDEN["argument_hash"], ids=_ids(GOLDEN["argument_hash"]))
def test_golden_argument_hash(case):
    assert argument_hash(case["event_type"], case["name"], case["payload"]) == case["sha256"]


@pytest.mark.parametrize("case", GOLDEN["context_hash"], ids=_ids(GOLDEN["context_hash"]))
def test_golden_context_hash(case):
    assert (
        context_hash(
            case["parent_context_hashes"],
            case["event_type"],
            case["name"],
            case["payload"],
            case["historical_response"],
            case["status"],
            case["error"],
        )
        == case["sha256"]
    )


def test_golden_context_hashes_chain():
    # Each fixture case's digest feeds the next case's parents, so a change
    # anywhere upstream ripples through every downstream golden value.
    cases = GOLDEN["context_hash"]
    assert cases[1]["parent_context_hashes"] == [cases[0]["sha256"]]
    assert cases[2]["parent_context_hashes"] == [cases[1]["sha256"]]
    assert cases[3]["parent_context_hashes"] == [cases[1]["sha256"], cases[2]["sha256"]]


# --- Canonical form properties ---------------------------------------------


def test_key_order_is_irrelevant():
    assert canonical_json({"b": 2, "a": 1}) == canonical_json({"a": 1, "b": 2})
    assert canonical_json({"b": 2, "a": 1}) == '{"a":1,"b":2}'


def test_no_whitespace_in_separators():
    assert canonical_json({"a": [1, 2], "b": {"c": 3}}) == '{"a":[1,2],"b":{"c":3}}'


def test_unicode_is_not_ascii_escaped():
    assert canonical_json("é") == '"é"'
    assert "\\u" not in canonical_json({"k": "héllo"})


def test_repeated_calls_are_stable():
    value = {"x": [1, {"y": "z"}], "w": 3.5}
    assert canonical_json(value) == canonical_json(value)


def test_int_and_float_of_equal_value_canonicalize_differently():
    # 1 and 1.0 compare equal in Python but are distinct canonical JSON;
    # payload builders must be consistent about numeric types.
    assert canonical_json(1) == "1"
    assert canonical_json(1.0) == "1.0"


# --- Strictness rejections --------------------------------------------------


class _Custom:
    pass


class _StrSubclass(str):
    pass


@pytest.mark.parametrize(
    ("value", "match"),
    [
        pytest.param({1: "a"}, "non-string dict key", id="int-key"),
        pytest.param({True: "a"}, "non-string dict key", id="bool-key"),
        pytest.param({None: "a"}, "non-string dict key", id="none-key"),
        pytest.param({(1, 2): "a"}, "non-string dict key", id="tuple-key"),
        pytest.param(b"raw", "bytes are not allowed", id="bytes"),
        pytest.param(bytearray(b"raw"), "bytes are not allowed", id="bytearray"),
        pytest.param({"v": b"raw"}, "bytes are not allowed", id="nested-bytes"),
        pytest.param(float("nan"), "NaN and Infinity", id="nan"),
        pytest.param(float("inf"), "NaN and Infinity", id="inf"),
        pytest.param(float("-inf"), "NaN and Infinity", id="-inf"),
        pytest.param({"deep": [{"x": float("nan")}]}, "NaN and Infinity", id="nested-nan"),
        pytest.param(_Custom(), "unsupported type", id="custom-object"),
        pytest.param({1, 2}, "unsupported type", id="set"),
        pytest.param((1, 2), "unsupported type", id="tuple"),
        pytest.param(Decimal("1"), "unsupported type", id="decimal"),
        pytest.param(datetime(2026, 7, 4), "unsupported type", id="datetime"),
        pytest.param(OrderedDict(a=1), "unsupported type", id="dict-subclass"),
        pytest.param(_StrSubclass("s"), "unsupported type", id="str-subclass"),
    ],
)
def test_rejects_non_canonical_values(value, match):
    with pytest.raises(ValueError, match=match):
        canonical_json(value)


def test_rejection_reports_path_to_offending_value():
    with pytest.raises(ValueError, match=r"\$\.a\[1\]"):
        validate_json_value({"a": [1, b"x"]})


def test_validate_json_value_accepts_all_exact_json_types():
    validate_json_value({"s": "x", "i": 0, "f": 3.5, "b": True, "n": None, "l": [{}], "d": {}})


# --- argument_hash semantics -------------------------------------------------


def test_argument_hash_rejects_metadata():
    with pytest.raises(ValueError, match="metadata events have no argument_hash"):
        argument_hash("metadata", None, {"schema_version": "1.0"})


def test_argument_hash_is_64_lowercase_hex():
    digest = argument_hash("tool_call", "lookup_customer", {"customer_id": 123})
    assert len(digest) == 64
    assert digest == digest.lower()
    int(digest, 16)


def test_argument_hash_ignores_payload_insertion_order():
    assert argument_hash("tool_call", "t", {"a": 1, "b": 2}) == argument_hash(
        "tool_call", "t", {"b": 2, "a": 1}
    )


def test_argument_hash_differs_by_each_component():
    base = argument_hash("tool_call", "lookup_customer", {"customer_id": 123})
    assert argument_hash("llm_call", "lookup_customer", {"customer_id": 123}) != base
    assert argument_hash("tool_call", "fetch_orders", {"customer_id": 123}) != base
    assert argument_hash("tool_call", "lookup_customer", {"customer_id": 124}) != base
    assert argument_hash("tool_call", None, {"customer_id": 123}) != base


def test_argument_hash_rejects_non_canonical_payload():
    with pytest.raises(ValueError, match="bytes are not allowed"):
        argument_hash("tool_call", "t", {"blob": b"raw"})


# --- context_hash semantics --------------------------------------------------


def _ctx(**overrides):
    base = {
        "parent_context_hashes": [HEX64],
        "event_type": "tool_call",
        "name": "fetch_orders",
        "payload": {"customer_id": 123, "limit": 5},
        "historical_response": {"orders": [1, 2, 3]},
        "status": "ok",
        "error": None,
    }
    base.update(overrides)
    return context_hash(**base)


def test_context_hash_rejects_metadata():
    with pytest.raises(ValueError, match="metadata events have no context_hash"):
        context_hash([], "metadata", None, {}, None, "ok", None)


def test_context_hash_is_sensitive_to_parent_order():
    assert _ctx(parent_context_hashes=[HEX64, HEX64_OTHER]) != _ctx(
        parent_context_hashes=[HEX64_OTHER, HEX64]
    )


def test_context_hash_ripples_when_a_parent_hash_changes():
    assert _ctx(parent_context_hashes=[HEX64]) != _ctx(parent_context_hashes=[HEX64_OTHER])


def test_context_hash_differs_by_status_and_error():
    ok = _ctx()
    failed = _ctx(
        historical_response=None,
        status="error",
        error={"type": "KeyError", "message": "'orders'"},
    )
    other_error = _ctx(
        historical_response=None,
        status="error",
        error={"type": "KeyError", "message": "'customer'"},
    )
    assert ok != failed
    assert failed != other_error


def test_context_hash_differs_by_response():
    assert _ctx(historical_response={"orders": [1]}) != _ctx(historical_response={"orders": [2]})


def test_context_hash_equal_inputs_equal_output():
    assert _ctx() == _ctx()


def test_context_hash_accepts_empty_parents_for_root():
    digest = _ctx(
        parent_context_hashes=[],
        event_type="root_input",
        name=None,
        historical_response=None,
    )
    assert len(digest) == 64


@pytest.mark.parametrize(
    "parents",
    [
        pytest.param((HEX64,), id="tuple-not-list"),
        pytest.param([HEX64[:63]], id="63-chars"),
        pytest.param([HEX64.upper()], id="uppercase-hex"),
        pytest.param(["not-a-hash"], id="not-hex"),
        pytest.param([None], id="none-entry"),
    ],
)
def test_context_hash_rejects_malformed_parent_hashes(parents):
    with pytest.raises(ValueError, match="parent_context_hashes"):
        _ctx(parent_context_hashes=parents)
