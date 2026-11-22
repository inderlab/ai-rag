import hashlib
import math
from collections.abc import Iterator

from app.llm.base import LLMProvider, LLMResult, StructuredResult

DIM = 64


class FakeModel:
    name = "fake-bow"
    dimension = DIM

    def __init__(self):
        self.encoded: list[str] = []

    def encode(self, texts: list[str]) -> list[list[float]]:
        self.encoded.extend(texts)
        out = []
        for text in texts:
            vec = [0.0] * DIM
            for word in text.lower().split()[1:]:
                vec[int(hashlib.md5(word.encode()).hexdigest(), 16) % DIM] += 1.0
            norm = math.sqrt(sum(x * x for x in vec)) or 1.0
            out.append([x / norm for x in vec])
        return out


class FakeLLM(LLMProvider):
    name = "fake"
    model = "fake-1"

    def __init__(self, replies: list[str] | None = None):
        self.replies = list(replies or [])
        self.structured_replies: list[dict] = []
        self.calls: list[dict] = []

    def complete(self, system: str, messages: list[dict], temperature: float = 0.2) -> LLMResult:
        self.calls.append({"system": system, "messages": messages, "temperature": temperature})
        text = self.replies.pop(0) if self.replies else "ok"
        return LLMResult(text=text, input_tokens=100, output_tokens=20)

    def stream(self, system: str, messages: list[dict], temperature: float = 0.2) -> Iterator[str]:
        text = self.complete(system, messages, temperature).text
        for word in text.split(" "):
            yield word + " "

    def structured(self, system, messages, schema, temperature=0.2):
        self.calls.append({"system": system, "messages": messages, "schema": schema.__name__})
        data = self.structured_replies.pop(0)
        return StructuredResult(data=schema(**data), input_tokens=500, output_tokens=80)
