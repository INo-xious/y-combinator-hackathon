"""JSON-safe serialization helpers for optional framework wrappers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from typing import Any

from flight_recorder.hashing import validate_json_value

_LANGCHAIN_MESSAGE = "__agent_rr_langchain_message__"
_ATTR_OBJECT = "__agent_rr_attr_object__"
_PYTHON_OBJECT = "__agent_rr_python_object__"


class AttrDict(dict):
    """A small replay object for SDK responses that supports attribute access."""

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name) from None


def to_jsonable(value: Any) -> Any:
    """Convert common SDK/framework objects into strict JSON-compatible data.

    Values already accepted by Agent-RR's canonical JSON validator are returned
    unchanged. Objects from Pydantic-style SDKs are converted through
    ``model_dump(mode="json")`` when available.
    """

    try:
        validate_json_value(value)
        return value
    except ValueError:
        pass

    langchain = _langchain_message_to_json(value)
    if langchain is not None:
        return langchain

    if is_dataclass(value) and not isinstance(value, type):
        return to_jsonable(asdict(value))

    if isinstance(value, tuple):
        return [to_jsonable(item) for item in value]

    if isinstance(value, Mapping):
        return {str(key): to_jsonable(item) for key, item in value.items()}

    if isinstance(value, list):
        return [to_jsonable(item) for item in value]

    if hasattr(value, "model_dump") and callable(value.model_dump):
        try:
            return to_jsonable(value.model_dump(mode="json"))
        except TypeError:
            return to_jsonable(value.model_dump())

    for method_name in ("to_dict", "dict"):
        method = getattr(value, method_name, None)
        if callable(method):
            try:
                return to_jsonable(method())
            except TypeError:
                pass

    if hasattr(value, "__dict__"):
        public = {
            key: item
            for key, item in vars(value).items()
            if not key.startswith("_")
        }
        if public:
            return {
                _PYTHON_OBJECT: f"{type(value).__module__}.{type(value).__qualname__}",
                "attributes": to_jsonable(public),
            }

    return {
        _PYTHON_OBJECT: f"{type(value).__module__}.{type(value).__qualname__}",
        "repr": repr(value),
    }


def from_jsonable(value: Any) -> Any:
    """Best-effort reconstruction for replay responses.

    LangChain messages are restored when ``langchain_core`` is installed.
    SDK dictionaries become ``AttrDict`` recursively so common code like
    ``response.output_text`` keeps working during replay.
    """

    langchain = _langchain_message_from_json(value)
    if langchain is not None:
        return langchain

    if isinstance(value, list):
        return [from_jsonable(item) for item in value]

    if isinstance(value, dict):
        if _PYTHON_OBJECT in value and "attributes" in value:
            return AttrDict(
                {
                    key: from_jsonable(item)
                    for key, item in value["attributes"].items()
                }
            )
        if _PYTHON_OBJECT in value and "repr" in value:
            return AttrDict({"repr": value["repr"], "type": value[_PYTHON_OBJECT]})
        return AttrDict({key: from_jsonable(item) for key, item in value.items()})

    return value


def _langchain_message_to_json(value: Any) -> dict | None:
    try:
        from langchain_core.messages import BaseMessage, message_to_dict  # type: ignore[import-not-found,import-untyped]
    except Exception:
        return None

    if isinstance(value, BaseMessage):
        return {_LANGCHAIN_MESSAGE: message_to_dict(value)}
    return None


def _langchain_message_from_json(value: Any) -> Any | None:
    if not (isinstance(value, dict) and _LANGCHAIN_MESSAGE in value):
        return None
    try:
        from langchain_core.messages import messages_from_dict
    except Exception:
        return AttrDict(value[_LANGCHAIN_MESSAGE])
    return messages_from_dict([value[_LANGCHAIN_MESSAGE]])[0]
