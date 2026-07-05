"""Optional framework integrations for Agent-RR.

These modules avoid hard dependencies on LangChain, OpenAI, and Anthropic.
Import the wrapper for the framework you use; if the framework is not
installed, local fakes that expose ``.invoke`` / ``.create`` still work in
tests and demos.
"""

__all__: list[str] = []
