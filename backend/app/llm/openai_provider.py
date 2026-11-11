from collections.abc import Iterator

from openai import OpenAI

from app.llm.base import LLMProvider


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str, base_url: str | None = None):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def chat(self, system: str, messages: list[dict], temperature: float = 0.2) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            messages=[{"role": "system", "content": system}, *messages],
        )
        return resp.choices[0].message.content or ""

    def stream(self, system: str, messages: list[dict]) -> Iterator[str]:
        stream = self.client.chat.completions.create(
            model=self.model,
            stream=True,
            messages=[{"role": "system", "content": system}, *messages],
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
