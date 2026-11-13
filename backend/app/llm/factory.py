from functools import lru_cache

from app.config import settings
from app.llm.base import LLMProvider
from app.llm.claude_provider import ClaudeProvider
from app.llm.openai_provider import OpenAIProvider

SUPPORTED = ("openai", "claude")


@lru_cache
def get_llm(provider: str | None = None) -> LLMProvider:
    name = (provider or settings.LLM_PROVIDER).lower()

    if name == "openai":
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is missing in .env")
        return OpenAIProvider(settings.OPENAI_API_KEY, settings.OPENAI_MODEL)

    if name == "claude":
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is missing in .env")
        return ClaudeProvider(
            settings.ANTHROPIC_API_KEY, settings.CLAUDE_MODEL, settings.CLAUDE_EFFORT
        )

    raise ValueError(f"Unknown LLM provider '{name}'. Use one of: {', '.join(SUPPORTED)}")
