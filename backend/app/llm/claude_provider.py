from collections.abc import Iterator

import anthropic

from app.llm.base import LLMProvider


class ClaudeProvider(LLMProvider):
    name = "claude"

    def __init__(self, api_key: str, model: str, max_tokens: int = 1500):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens

    def chat(self, system: str, messages: list[dict], temperature: float = 0.2) -> str:
        # Claude takes the system prompt as its own field, and max_tokens is required
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=temperature,
            system=system,
            messages=messages,
        )
        return "".join(block.text for block in resp.content if block.type == "text")

    def stream(self, system: str, messages: list[dict]) -> Iterator[str]:
        with self.client.messages.stream(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=messages,
        ) as s:
            yield from s.text_stream
