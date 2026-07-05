"""Optional framework integrations for Agent-RR.

These modules avoid hard dependencies on LangChain, OpenAI, Anthropic,
LiteLLM, and requests. Import the wrapper for the framework you use
(``openai.wrap_openai``, ``anthropic.wrap_anthropic``, ``langchain.wrap_llm``,
``litellm.wrap_litellm``, ``requests.wrap_requests``); if the framework is
not installed, local fakes that expose ``.invoke`` / ``.create`` /
``.request`` still work in tests and demos.
"""

__all__: list[str] = []
