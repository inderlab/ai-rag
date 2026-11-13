from collections.abc import Iterator

import anthropic

from app.llm.base import LLMProvider, LLMResult


class ClaudeProvider(LLMProvider):
    name = "claude"
    supports_temperature = False

    def __init__(self, api_key: str, model: str, effort: str = "low", max_tokens: int = 16000):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.effort = effort
        self.max_tokens = max_tokens

    def complete(self, system: str, messages: list[dict], temperature: float = 0.2) -> LLMResult:
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            output_config={"effort": self.effort},
            system=system,
            messages=messages,
        )
        return LLMResult(
            text="".join(block.text for block in resp.content if block.type == "text"),
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
        )

    def stream(self, system: str, messages: list[dict], temperature: float = 0.2) -> Iterator[str]:
        with self.client.messages.stream(
            model=self.model,
            max_tokens=self.max_tokens,
            output_config={"effort": self.effort},
            system=system,
            messages=messages,
        ) as s:
            yield from s.text_stream
