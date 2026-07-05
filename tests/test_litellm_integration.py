"""LiteLLM wrapper tests (P0 roadmap: Native Integrations Expansion)."""

import pytest

from flight_recorder.capture import capture_context, get_current_parent_ids
from flight_recorder.errors import ReplayDivergence
from flight_recorder.integrations.litellm import wrap_completion, wrap_litellm
from flight_recorder.recorder import Recorder
from flight_recorder.replayer import Replayer
from flight_recorder.storage import read_events


class _FakeResponse:
    def __init__(self, data):
        object.__setattr__(self, "_data", data)

    def model_dump(self, mode="json"):
        return self._data

    def __getattr__(self, name):
        from flight_recorder.integrations._serialization import from_jsonable

        try:
            return from_jsonable(self._data[name])
        except KeyError:
            raise AttributeError(name) from None


def _completion_response(text):
    return {
        "id": "resp-1",
        "object": "chat.completion",
        "model": "gpt-test",
        "choices": [
            {"index": 0, "message": {"role": "assistant", "content": text},
             "finish_reason": "stop"}
        ],
    }


def _make_fake_completion(*, poison=False):
    def completion(**kwargs):
        if poison:
            raise AssertionError("completion must not execute during replay")
        if kwargs.get("stream") is True:
            text = f"streamed:{kwargs['messages'][0]['content']}"
            pieces = [text[: len(text) // 2], text[len(text) // 2 :]]
            return (
                _FakeResponse(
                    {"id": "s1", "model": kwargs["model"],
                     "choices": [{"index": 0,
                                  "delta": {"role": "assistant", "content": piece},
                                  "finish_reason": "stop" if is_last else None}]}
                )
                for is_last, piece in ((piece is pieces[-1], piece) for piece in pieces)
            )
        return _FakeResponse(_completion_response(f"echo:{kwargs['messages'][0]['content']}"))

    return completion


def _run_agent(rr, completion, prompt="hi"):
    root = rr.record_root_input({"q": prompt})
    with capture_context(rr, [root]):
        response = completion(
            model="gpt-test", messages=[{"role": "user", "content": prompt}]
        )
        text = response.choices[0].message.content
        rr.record_final_output({"text": text}, get_current_parent_ids())
    return text


def test_wrap_completion_records_and_replays(tmp_path):
    trace = tmp_path / "trace.jsonl"

    with Recorder("litellm", trace) as rr:
        recorded = _run_agent(rr, wrap_completion(_make_fake_completion()))
    assert recorded == "echo:hi"

    llm_events = [e for e in read_events(trace) if e.event_type == "llm_call"]
    assert [e.name for e in llm_events] == ["litellm.completion"]

    with Replayer(trace) as rr:
        replayed = _run_agent(rr, wrap_completion(_make_fake_completion(poison=True)))
    assert replayed == recorded


def test_wrap_completion_streaming(tmp_path):
    trace = tmp_path / "trace.jsonl"

    def stream_text(completion):
        return "".join(
            choice.delta.content
            for chunk in completion(
                model="gpt-test",
                messages=[{"role": "user", "content": "hi"}],
                stream=True,
            )
            for choice in chunk.choices
            if getattr(choice.delta, "content", None)
        )

    with Recorder("litellm", trace) as rr:
        root = rr.record_root_input({"q": "hi"})
        with capture_context(rr, [root]):
            recorded = stream_text(wrap_completion(_make_fake_completion()))
            rr.record_final_output({"text": recorded}, get_current_parent_ids())
    assert recorded == "streamed:hi"

    with Replayer(trace) as rr:
        root = rr.record_root_input({"q": "hi"})
        with capture_context(rr, [root]):
            replayed = stream_text(wrap_completion(_make_fake_completion(poison=True)))
            rr.record_final_output({"text": replayed}, get_current_parent_ids())
    assert replayed == recorded


def test_divergence_on_changed_prompt(tmp_path):
    trace = tmp_path / "trace.jsonl"
    with Recorder("litellm", trace) as rr:
        _run_agent(rr, wrap_completion(_make_fake_completion()), prompt="hi")

    with pytest.raises(ReplayDivergence):
        with Replayer(trace) as rr:
            _run_agent(rr, wrap_completion(_make_fake_completion(poison=True)), prompt="bye")


def test_wrap_litellm_proxy_wraps_endpoints_and_delegates():
    class _FakeLiteLLMModule:
        api_base = "https://example"

        @staticmethod
        def completion(**kwargs):
            return _FakeResponse(_completion_response("live"))

        @staticmethod
        def embedding(**kwargs):
            return _FakeResponse({"data": [{"embedding": [1, 2]}]})

    llm = wrap_litellm(_FakeLiteLLMModule())
    # Outside a capture context calls pass through.
    assert llm.completion(model="m", messages=[]).choices[0].message.content == "live"
    assert llm.api_base == "https://example"


def test_wrap_litellm_records_embedding(tmp_path):
    class _FakeLiteLLMModule:
        @staticmethod
        def completion(**kwargs):
            raise AssertionError("unused")

        @staticmethod
        def embedding(**kwargs):
            return _FakeResponse({"data": [{"embedding": [1, 2]}]})

    trace = tmp_path / "trace.jsonl"
    with Recorder("litellm", trace) as rr:
        root = rr.record_root_input({"q": "embed"})
        llm = wrap_litellm(_FakeLiteLLMModule())
        with capture_context(rr, [root]):
            result = llm.embedding(model="embed-test", input=["hello"])
            rr.record_final_output(
                {"dims": len(result.data[0].embedding)}, get_current_parent_ids()
            )
    names = [e.name for e in read_events(trace) if e.event_type == "llm_call"]
    assert names == ["litellm.embedding"]
