"""The agent's brain — one place, provider-agnostic.

`init_chat_model` reads a "provider:model" string (e.g. "openai:gpt-4o-mini"),
so changing the model is a single env var (LLM_MODEL) with zero code changes.
"""
from langchain.chat_models import init_chat_model

from . import config


def get_llm(temperature: float = 0.0, **kwargs):
    """Return the configured chat model."""
    return init_chat_model(config.LLM_MODEL, temperature=temperature, **kwargs)
