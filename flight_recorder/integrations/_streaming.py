"""Streaming LLM capture: deterministic chunk aggregation and replay streams.

Network chunk boundaries are nondeterministic (they depend on packet timing),
so traces never store raw chunks. During record the wrapper consumes the
provider stream inside ``call()``, folds the chunks into one aggregated
response, and stores only that — the trace is independent of how the network
happened to split the stream. The caller still iterates chunks: the buffered
originals on record, a synthetic stream rebuilt from the aggregate on replay.
Code that only accumulates deltas behaves identically on both paths; code
that depends on exact chunk boundaries is out of scope (documented limitation).

Record buffers the whole stream before the event is written (``call()`` must
complete before the recorder writes exactly one event; a lazy tee would let
other events interleave mid-record). ``latency_ms`` is therefore the full
stream consumption time.

TODO: a lazy-tee mode that yields chunks while recording, writing the event
on stream exhaustion.

Stored shape (strict JSON, no schema change)::

    {"__agent_rr_stream__": "openai.chat.chunks" | "anthropic.message_events",
     "aggregated": {...}, "chunk_count": N}
"""

from __future__ import annotations

from typing import Any, Iterable, Iterator, Literal

from ._serialization import from_jsonable

STREAM_MARKER = "__agent_rr_stream__"
STREAM_KIND_OPENAI = "openai.chat.chunks"
STREAM_KIND_ANTHROPIC = "anthropic.message_events"


def is_stream_response(value: Any) -> bool:
    """True when *value* is the stored form of a streamed response."""
    return type(value) is dict and STREAM_MARKER in value


def stream_response(kind: str, aggregated: dict, chunk_count: int) -> dict:
    """Build the stored ``historical_response`` for a streamed call."""
    return {STREAM_MARKER: kind, "aggregated": aggregated, "chunk_count": chunk_count}


class ReplayableStream:
    """List-backed chunk iterator returned by wrappers for streamed calls.

    Iterates buffered raw chunks (record) or synthetic chunks (replay). The
    no-op context-manager methods keep ``with client...create(stream=True)``
    call sites working on both paths.
    """

    def __init__(self, chunks: list[Any]):
        self._chunks = chunks
        self._iterator: Iterator[Any] = iter(chunks)

    def __iter__(self) -> Iterator[Any]:
        return self._iterator

    def __next__(self) -> Any:
        return next(self._iterator)

    def __enter__(self) -> "ReplayableStream":
        return self

    def __exit__(self, exc_type, exc, tb) -> Literal[False]:
        return False


# --- OpenAI chat-completion chunks ---------------------------------------------


def aggregate_openai_chunks(chunks: Iterable[dict]) -> dict:
    """Fold serialized OpenAI chat-completion chunks into one completion dict.

    Deterministic: chunks are folded in stream order; per-choice ``delta``
    content and tool-call argument fragments are concatenated, and the last
    non-null ``finish_reason``/``usage`` win. LiteLLM emits the same chunk
    shape, so its wrapper reuses this fold.
    """
    aggregated: dict[str, Any] = {"object": "chat.completion", "choices": []}
    choices_by_index: dict[int, dict] = {}
    for chunk in chunks:
        if type(chunk) is not dict:
            continue
        for key in ("id", "created", "model", "system_fingerprint"):
            if aggregated.get(key) is None and chunk.get(key) is not None:
                aggregated[key] = chunk[key]
        if chunk.get("usage") is not None:
            aggregated["usage"] = chunk["usage"]
        for chunk_choice in chunk.get("choices") or []:
            index = chunk_choice.get("index", 0)
            choice = choices_by_index.setdefault(
                index,
                {"index": index, "message": {"role": None, "content": None}, "finish_reason": None},
            )
            _fold_openai_delta(choice["message"], chunk_choice.get("delta") or {})
            if chunk_choice.get("finish_reason") is not None:
                choice["finish_reason"] = chunk_choice["finish_reason"]
    aggregated["choices"] = [choices_by_index[i] for i in sorted(choices_by_index)]
    return aggregated


def _fold_openai_delta(message: dict, delta: dict) -> None:
    if delta.get("role") is not None:
        message["role"] = delta["role"]
    if delta.get("content") is not None:
        message["content"] = (message["content"] or "") + delta["content"]
    for fragment in delta.get("tool_calls") or []:
        tool_calls = message.setdefault("tool_calls", [])
        index = fragment.get("index", 0)
        while len(tool_calls) <= index:
            tool_calls.append(
                {"index": len(tool_calls), "id": None, "type": None,
                 "function": {"name": None, "arguments": ""}}
            )
        tool_call = tool_calls[index]
        for key in ("id", "type"):
            if fragment.get(key) is not None:
                tool_call[key] = fragment[key]
        function_fragment = fragment.get("function") or {}
        if function_fragment.get("name") is not None:
            tool_call["function"]["name"] = function_fragment["name"]
        if function_fragment.get("arguments"):
            tool_call["function"]["arguments"] += function_fragment["arguments"]


def synthesize_openai_chunks(aggregated: dict) -> list[Any]:
    """Rebuild a minimal chunk stream from an aggregated completion.

    Exact original chunk boundaries are gone by design; replay yields one
    content chunk per choice plus one finishing chunk, which is equivalent
    for any consumer that concatenates deltas.
    """
    base = {
        key: aggregated.get(key)
        for key in ("id", "created", "model", "system_fingerprint")
        if aggregated.get(key) is not None
    }
    base["object"] = "chat.completion.chunk"
    chunks: list[dict] = []
    for choice in aggregated.get("choices") or []:
        message = choice.get("message") or {}
        delta = {key: message[key] for key in ("role", "content", "tool_calls") if message.get(key) is not None}
        chunks.append(
            {**base, "choices": [{"index": choice.get("index", 0), "delta": delta, "finish_reason": None}]}
        )
    finish = {
        **base,
        "choices": [
            {"index": choice.get("index", 0), "delta": {}, "finish_reason": choice.get("finish_reason")}
            for choice in aggregated.get("choices") or []
        ],
    }
    if aggregated.get("usage") is not None:
        finish["usage"] = aggregated["usage"]
    chunks.append(finish)
    return [from_jsonable(chunk) for chunk in chunks]


# --- Anthropic message stream events --------------------------------------------


def aggregate_anthropic_events(events: Iterable[dict]) -> dict:
    """Fold serialized Anthropic message-stream events into one message dict."""
    message: dict[str, Any] = {}
    content: list[dict] = []
    for event in events:
        if type(event) is not dict:
            continue
        event_type = event.get("type")
        if event_type == "message_start":
            message = dict(event.get("message") or {})
            content = list(message.get("content") or [])
        elif event_type == "content_block_start":
            index = event.get("index", len(content))
            while len(content) <= index:
                content.append({})
            content[index] = dict(event.get("content_block") or {})
        elif event_type == "content_block_delta":
            index = event.get("index", 0)
            while len(content) <= index:
                content.append({})
            _fold_anthropic_delta(content[index], event.get("delta") or {})
        elif event_type == "message_delta":
            for key, value in (event.get("delta") or {}).items():
                message[key] = value
            if event.get("usage") is not None:
                usage = dict(message.get("usage") or {})
                usage.update(event["usage"])
                message["usage"] = usage
        # content_block_stop and message_stop carry no data to fold.
    message["content"] = content
    return message


def _fold_anthropic_delta(block: dict, delta: dict) -> None:
    delta_type = delta.get("type")
    if delta_type == "text_delta":
        block["text"] = block.get("text", "") + (delta.get("text") or "")
    elif delta_type == "input_json_delta":
        # Concatenated partial_json is kept as a string under "input_json".
        # TODO: parse it into "input" once complete, like the SDK does.
        block["input_json"] = block.get("input_json", "") + (delta.get("partial_json") or "")
    elif delta_type == "thinking_delta":
        block["thinking"] = block.get("thinking", "") + (delta.get("thinking") or "")


def synthesize_anthropic_events(aggregated: dict) -> list[Any]:
    """Rebuild a minimal event stream from an aggregated message.

    Text (and thinking/input_json) is delivered through delta events, not the
    start block, so consumers that concatenate deltas — the normal streaming
    pattern — produce the same final content on replay as they did live.
    """
    message_start = dict(aggregated)
    content = message_start.pop("content", [])
    stop_reason = message_start.pop("stop_reason", None)
    stop_sequence = message_start.pop("stop_sequence", None)
    usage = message_start.get("usage")
    message_start["content"] = []
    events: list[dict] = [{"type": "message_start", "message": message_start}]
    for index, block in enumerate(content):
        start_block = dict(block)
        deltas: list[dict] = []
        if "text" in start_block:
            deltas.append({"type": "text_delta", "text": start_block["text"]})
            start_block["text"] = ""
        if "thinking" in start_block:
            deltas.append({"type": "thinking_delta", "thinking": start_block["thinking"]})
            start_block["thinking"] = ""
        if "input_json" in start_block:
            deltas.append(
                {"type": "input_json_delta", "partial_json": start_block.pop("input_json")}
            )
        events.append({"type": "content_block_start", "index": index, "content_block": start_block})
        for delta in deltas:
            events.append({"type": "content_block_delta", "index": index, "delta": delta})
        events.append({"type": "content_block_stop", "index": index})
    message_delta: dict[str, Any] = {
        "type": "message_delta",
        "delta": {"stop_reason": stop_reason, "stop_sequence": stop_sequence},
    }
    if usage is not None:
        message_delta["usage"] = usage
    events.append(message_delta)
    events.append({"type": "message_stop"})
    return [from_jsonable(event) for event in events]
