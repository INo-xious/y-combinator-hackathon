"""Streaming LLM record/replay tests (P0 roadmap: Streaming Support).

Fake SDK clients emit chunk generators; record buffers and aggregates them,
replay yields a synthetic chunk stream with identical concatenated content —
and never touches the live client (poison).
"""

import pytest

from flight_recorder.capture import capture_context, get_current_parent_ids
from flight_recorder.errors import ReplayDivergence
from flight_recorder.integrations._serialization import from_jsonable
from flight_recorder.integrations._streaming import (
    STREAM_MARKER,
    ReplayableStream,
    aggregate_anthropic_events,
    aggregate_openai_chunks,
    synthesize_anthropic_events,
    synthesize_openai_chunks,
)
from flight_recorder.integrations.anthropic import wrap_anthropic
from flight_recorder.integrations.openai import wrap_openai
from flight_recorder.recorder import Recorder
from flight_recorder.replayer import Replayer
from flight_recorder.storage import read_events


# --- aggregation unit tests -------------------------------------------------------


def _openai_chunks(text="Hello world", chunk_size=5):
    pieces = [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]
    chunks = [
        {"id": "c1", "created": 1, "model": "gpt-test",
         "choices": [{"index": 0, "delta": {"role": "assistant", "content": pieces[0]}, "finish_reason": None}]}
    ]
    for piece in pieces[1:]:
        chunks.append(
            {"id": "c1", "created": 1, "model": "gpt-test",
             "choices": [{"index": 0, "delta": {"content": piece}, "finish_reason": None}]}
        )
    chunks.append(
        {"id": "c1", "created": 1, "model": "gpt-test",
         "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
         "usage": {"total_tokens": 7}}
    )
    return chunks


def test_aggregate_openai_chunks_concatenates_content():
    aggregated = aggregate_openai_chunks(_openai_chunks())
    assert aggregated["id"] == "c1"
    assert aggregated["model"] == "gpt-test"
    choice = aggregated["choices"][0]
    assert choice["message"] == {"role": "assistant", "content": "Hello world"}
    assert choice["finish_reason"] == "stop"
    assert aggregated["usage"] == {"total_tokens": 7}


def test_aggregate_openai_chunks_is_chunking_independent():
    # The determinism point of storing the aggregate: however the network
    # split the stream, the stored response is identical.
    assert aggregate_openai_chunks(_openai_chunks(chunk_size=1)) == aggregate_openai_chunks(
        _openai_chunks(chunk_size=100)
    )


def test_aggregate_openai_multi_choice_and_tool_calls():
    chunks = [
        {"id": "c2", "choices": [
            {"index": 1, "delta": {"role": "assistant", "content": "B"}, "finish_reason": None},
        ]},
        {"id": "c2", "choices": [
            {"index": 0, "delta": {"role": "assistant", "tool_calls": [
                {"index": 0, "id": "call_1", "type": "function",
                 "function": {"name": "get_weather", "arguments": '{"cit'}}]},
             "finish_reason": None},
        ]},
        {"id": "c2", "choices": [
            {"index": 0, "delta": {"tool_calls": [
                {"index": 0, "function": {"arguments": 'y": "SF"}'}}]},
             "finish_reason": "tool_calls"},
            {"index": 1, "delta": {"content": "!"}, "finish_reason": "stop"},
        ]},
    ]
    aggregated = aggregate_openai_chunks(chunks)
    assert [c["index"] for c in aggregated["choices"]] == [0, 1]
    tool_call = aggregated["choices"][0]["message"]["tool_calls"][0]
    assert tool_call["id"] == "call_1"
    assert tool_call["function"] == {"name": "get_weather", "arguments": '{"city": "SF"}'}
    assert aggregated["choices"][0]["finish_reason"] == "tool_calls"
    assert aggregated["choices"][1]["message"]["content"] == "B!"


def test_aggregate_openai_empty_stream():
    aggregated = aggregate_openai_chunks([])
    assert aggregated == {"object": "chat.completion", "choices": []}


def test_synthesize_openai_chunks_roundtrips_content():
    aggregated = aggregate_openai_chunks(_openai_chunks())
    synthetic = synthesize_openai_chunks(aggregated)
    text = "".join(
        choice.delta.content
        for chunk in synthetic
        for choice in chunk.choices
        if getattr(choice.delta, "content", None)
    )
    assert text == "Hello world"
    assert synthetic[-1].choices[0].finish_reason == "stop"
    assert synthetic[-1].usage == {"total_tokens": 7}


def _anthropic_events(text="streamed reply"):
    half = len(text) // 2
    return [
        {"type": "message_start", "message": {"id": "m1", "type": "message", "role": "assistant",
                                              "content": [], "model": "claude-test",
                                              "usage": {"input_tokens": 3}}},
        {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": text[:half]}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": text[half:]}},
        {"type": "content_block_stop", "index": 0},
        {"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": None},
         "usage": {"output_tokens": 5}},
        {"type": "message_stop"},
    ]


def test_aggregate_anthropic_events_folds_message():
    message = aggregate_anthropic_events(_anthropic_events())
    assert message["id"] == "m1"
    assert message["content"] == [{"type": "text", "text": "streamed reply"}]
    assert message["stop_reason"] == "end_turn"
    assert message["usage"] == {"input_tokens": 3, "output_tokens": 5}


def test_aggregate_anthropic_tool_use_partial_json():
    events = [
        {"type": "message_start", "message": {"id": "m2", "content": []}},
        {"type": "content_block_start", "index": 0,
         "content_block": {"type": "tool_use", "id": "tu1", "name": "get_weather"}},
        {"type": "content_block_delta", "index": 0,
         "delta": {"type": "input_json_delta", "partial_json": '{"city"'}},
        {"type": "content_block_delta", "index": 0,
         "delta": {"type": "input_json_delta", "partial_json": ': "SF"}'}},
        {"type": "content_block_stop", "index": 0},
        {"type": "message_stop"},
    ]
    message = aggregate_anthropic_events(events)
    assert message["content"][0]["input_json"] == '{"city": "SF"}'


def test_synthesize_anthropic_events_roundtrips_text():
    message = aggregate_anthropic_events(_anthropic_events())
    synthetic = synthesize_anthropic_events(message)
    text = "".join(
        event.delta.text
        for event in synthetic
        if event.type == "content_block_delta" and event.delta.type == "text_delta"
    )
    assert text == "streamed reply"
    stop_reasons = [event.delta.stop_reason for event in synthetic if event.type == "message_delta"]
    assert stop_reasons == ["end_turn"]


def test_replayable_stream_is_iterator_and_context_manager():
    stream = ReplayableStream([1, 2, 3])
    with stream as s:
        assert next(s) == 1
        assert list(s) == [2, 3]


# --- OpenAI wrapper end-to-end -------------------------------------------------------


class _FakeChunk:
    """SDK-chunk stand-in: attribute access for consumers, model_dump for
    the serializer."""

    def __init__(self, data):
        object.__setattr__(self, "_data", data)

    def model_dump(self, mode="json"):
        return self._data

    def __getattr__(self, name):
        try:
            return from_jsonable(self._data[name])
        except KeyError:
            raise AttributeError(name) from None


class _ChatCompletions:
    def __init__(self, *, poison=False):
        self.poison = poison

    def create(self, **kwargs):
        if self.poison:
            raise AssertionError("create must not execute during replay")
        if kwargs.get("stream") is True:
            return (_FakeChunk(c) for c in _openai_chunks())
        raise AssertionError("expected a streaming call")


class _Chat:
    def __init__(self, *, poison=False):
        self.completions = _ChatCompletions(poison=poison)


class _OpenAIClient:
    def __init__(self, *, poison=False):
        self.chat = _Chat(poison=poison)


def _stream_openai_run(rr, client):
    root = rr.record_root_input({"q": "hello"})
    with capture_context(rr, [root]):
        stream = client.chat.completions.create(
            model="gpt-test",
            messages=[{"role": "user", "content": "hello"}],
            stream=True,
        )
        text = "".join(
            choice.delta.content
            for chunk in stream
            for choice in chunk.choices
            if getattr(choice.delta, "content", None)
        )
        rr.record_final_output({"text": text}, get_current_parent_ids())
    return text


def test_openai_streaming_records_and_replays(tmp_path):
    trace = tmp_path / "trace.jsonl"

    with Recorder("sdk", trace) as rr:
        recorded_text = _stream_openai_run(rr, wrap_openai(_OpenAIClient()))
    assert recorded_text == "Hello world"

    events = read_events(trace)
    llm_events = [e for e in events if e.event_type == "llm_call"]
    assert len(llm_events) == 1
    stored = llm_events[0].historical_response
    assert stored[STREAM_MARKER] == "openai.chat.chunks"
    assert stored["chunk_count"] == 4
    assert stored["aggregated"]["choices"][0]["message"]["content"] == "Hello world"
    # stream=True is part of the argument hash: a non-streaming replay of a
    # streamed call diverges.
    assert llm_events[0].payload["kwargs"]["stream"] is True

    with Replayer(trace) as rr:
        replayed_text = _stream_openai_run(rr, wrap_openai(_OpenAIClient(poison=True)))
    assert replayed_text == recorded_text


def test_openai_streaming_divergence_on_changed_prompt(tmp_path):
    trace = tmp_path / "trace.jsonl"
    with Recorder("sdk", trace) as rr:
        _stream_openai_run(rr, wrap_openai(_OpenAIClient()))

    with pytest.raises(ReplayDivergence):
        with Replayer(trace) as rr:
            root = rr.record_root_input({"q": "hello"})
            client = wrap_openai(_OpenAIClient(poison=True))
            with capture_context(rr, [root]):
                client.chat.completions.create(
                    model="gpt-test",
                    messages=[{"role": "user", "content": "DIFFERENT"}],
                    stream=True,
                )


# --- Anthropic wrapper end-to-end ------------------------------------------------------


class _AnthropicMessages:
    def __init__(self, *, poison=False):
        self.poison = poison

    def create(self, **kwargs):
        if self.poison:
            raise AssertionError("create must not execute during replay")
        assert kwargs.get("stream") is True
        return (_FakeChunk(e) for e in _anthropic_events())

    def stream(self, **kwargs):
        raise AssertionError("stream helper should be refused before reaching the SDK")


class _AnthropicClient:
    def __init__(self, *, poison=False):
        self.messages = _AnthropicMessages(poison=poison)


def _stream_anthropic_run(rr, client):
    root = rr.record_root_input({"q": "hi"})
    with capture_context(rr, [root]):
        stream = client.messages.create(
            model="claude-test",
            messages=[{"role": "user", "content": "hi"}],
            stream=True,
        )
        text = "".join(
            event.delta.text
            for event in stream
            if event.type == "content_block_delta" and event.delta.type == "text_delta"
        )
        rr.record_final_output({"text": text}, get_current_parent_ids())
    return text


def test_anthropic_streaming_records_and_replays(tmp_path):
    trace = tmp_path / "trace.jsonl"

    with Recorder("sdk", trace) as rr:
        recorded_text = _stream_anthropic_run(rr, wrap_anthropic(_AnthropicClient()))
    assert recorded_text == "streamed reply"

    stored = [e for e in read_events(trace) if e.event_type == "llm_call"][0].historical_response
    assert stored[STREAM_MARKER] == "anthropic.message_events"
    assert stored["aggregated"]["content"] == [{"type": "text", "text": "streamed reply"}]

    with Replayer(trace) as rr:
        replayed_text = _stream_anthropic_run(rr, wrap_anthropic(_AnthropicClient(poison=True)))
    assert replayed_text == recorded_text


def test_anthropic_stream_helper_refused_in_context(tmp_path):
    trace = tmp_path / "trace.jsonl"
    with Recorder("sdk", trace) as rr:
        root = rr.record_root_input({"q": "hi"})
        client = wrap_anthropic(_AnthropicClient())
        with capture_context(rr, [root]):
            with pytest.raises(NotImplementedError, match="messages.stream"):
                client.messages.stream(model="claude-test")
            rr.record_final_output({"ok": True}, [root])
