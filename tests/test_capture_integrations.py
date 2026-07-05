"""Contextvar capture and optional framework integration tests."""

import pytest

from flight_recorder.capture import capture_context, get_current_parent_ids
from flight_recorder.errors import ReplayDivergence
from flight_recorder.integrations.anthropic import wrap_anthropic
from flight_recorder.integrations.langchain import run_agent_rr, wrap_llm, wrap_tool
from flight_recorder.integrations.openai import wrap_openai
from flight_recorder.recorder import Recorder
from flight_recorder.replayer import Replayer
from flight_recorder.storage import read_events


class FakeRunnable:
    def __init__(self, name, func, *, poison=False):
        self.name = name
        self._func = func
        self._poison = poison

    def invoke(self, input, config=None, **kwargs):
        if self._poison:
            raise AssertionError(f"{self.name} should not execute during replay")
        return self._func(input)


class MiniGraph:
    def __init__(self, model, tool, *, prompt="plan-v1"):
        self.model = model
        self.tool = tool
        self.prompt = prompt

    def invoke(self, payload):
        plan = self.model.invoke({"prompt": self.prompt, "query": payload["query"]})
        tool_result = self.tool.invoke({"customer_id": plan["customer_id"]})
        return self.model.invoke(
            {"prompt": "summary-v1", "customer": tool_result}
        )


def build_graph(*, prompt="plan-v1", poison=False):
    model = wrap_llm(
        FakeRunnable(
            "model",
            lambda input: (
                {"customer_id": "cust_123"}
                if input["prompt"].startswith("plan")
                else {"answer": f"hello {input['customer']['name']}"}
            ),
            poison=poison,
        )
    )
    tool = wrap_tool(
        FakeRunnable(
            "lookup_customer",
            lambda input: {"customer_id": input["customer_id"], "name": "Ada"},
            poison=poison,
        )
    )
    return MiniGraph(model, tool, prompt=prompt)


def test_langchain_wrappers_record_replay_and_track_parents(tmp_path):
    trace = tmp_path / "trace.jsonl"
    payload = {"query": "help customer cust_123"}

    with Recorder("demo", trace) as rr:
        assert run_agent_rr(rr, payload, build_graph()) == {"answer": "hello Ada"}

    events = read_events(trace)
    root, plan, tool, summary, final = events[1:]
    assert root.event_type == "root_input"
    assert plan.parent_event_ids == [root.event_id]
    assert tool.parent_event_ids == [plan.event_id]
    assert summary.parent_event_ids == [tool.event_id]
    assert final.parent_event_ids == [summary.event_id]

    with Replayer(trace) as rr:
        assert run_agent_rr(rr, payload, build_graph(poison=True)) == {
            "answer": "hello Ada"
        }
    assert rr.report.clean


def test_langchain_prompt_change_diverges_deterministically(tmp_path):
    trace = tmp_path / "trace.jsonl"
    payload = {"query": "help customer cust_123"}

    with Recorder("demo", trace) as rr:
        run_agent_rr(rr, payload, build_graph(prompt="plan-v1"))

    with pytest.raises(ReplayDivergence, match="argument_hash mismatch") as excinfo:
        with Replayer(trace) as rr:
            run_agent_rr(rr, payload, build_graph(prompt="plan-v2"))

    assert excinfo.value.at_sequence_index == 2


class _SDKResponse:
    def __init__(self, **values):
        self._values = values

    def model_dump(self, mode="json"):
        return dict(self._values)

    def __getattr__(self, name):
        return self._values[name]


class _OpenAIResponses:
    def __init__(self, *, poison=False):
        self.poison = poison

    def create(self, **kwargs):
        if self.poison:
            raise AssertionError("OpenAI create should not execute during replay")
        return _SDKResponse(output_text=f"answer:{kwargs['input']}")


class _OpenAIClient:
    def __init__(self, *, poison=False):
        self.responses = _OpenAIResponses(poison=poison)


def test_openai_wrapper_captures_create_and_replays_object_like_response(tmp_path):
    trace = tmp_path / "trace.jsonl"

    with Recorder("sdk", trace) as rr:
        root = rr.record_root_input({"q": "hello"})
        client = wrap_openai(_OpenAIClient())
        with capture_context(rr, [root]):
            response = client.responses.create(model="gpt-test", input="hello")
            rr.record_final_output(
                {"text": response.output_text}, get_current_parent_ids()
            )

    with Replayer(trace) as rr:
        root = rr.record_root_input({"q": "hello"})
        client = wrap_openai(_OpenAIClient(poison=True))
        with capture_context(rr, [root]):
            response = client.responses.create(model="gpt-test", input="hello")
            assert response.output_text == "answer:hello"
            rr.record_final_output(
                {"text": response.output_text}, get_current_parent_ids()
            )


class _AnthropicMessages:
    def __init__(self, *, poison=False):
        self.poison = poison

    def create(self, **kwargs):
        if self.poison:
            raise AssertionError("Anthropic create should not execute during replay")
        return _SDKResponse(text=f"message:{kwargs['messages'][0]['content']}")


class _AnthropicClient:
    def __init__(self, *, poison=False):
        self.messages = _AnthropicMessages(poison=poison)


def test_anthropic_wrapper_captures_messages_create(tmp_path):
    trace = tmp_path / "trace.jsonl"
    kwargs = {"model": "claude-test", "messages": [{"role": "user", "content": "hi"}]}

    with Recorder("sdk", trace) as rr:
        root = rr.record_root_input({"q": "hi"})
        client = wrap_anthropic(_AnthropicClient())
        with capture_context(rr, [root]):
            response = client.messages.create(**kwargs)
            rr.record_final_output({"text": response.text}, get_current_parent_ids())

    with Replayer(trace) as rr:
        root = rr.record_root_input({"q": "hi"})
        client = wrap_anthropic(_AnthropicClient(poison=True))
        with capture_context(rr, [root]):
            response = client.messages.create(**kwargs)
            assert response.text == "message:hi"
            rr.record_final_output({"text": response.text}, get_current_parent_ids())


class DummyOpenAI:
    def __init__(self, api_key):
        self.api_key = api_key
        
    def close(self):
        pass

    class _Chat:
        pass

    chat = _Chat()

def test_openai_proxy_passthrough():
    from flight_recorder.integrations.openai import _OpenAIProxy
    
    client = wrap_openai(DummyOpenAI(api_key="fake-key"))
    
    # Should be scalar, not proxy
    assert client.api_key == "fake-key" 
    
    # Should be callable, not proxy
    assert callable(client.close) 
    
    # Should still correctly proxy the capture chain
    assert isinstance(client.chat, _OpenAIProxy)
