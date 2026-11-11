from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass


@dataclass
class LLMResult:
    text: str
    input_tokens: int
    output_tokens: int


class LLMProvider(ABC):
    name: str
    model: str

    @abstractmethod
    def complete(
        self, system: str, messages: list[dict], temperature: float = 0.2
    ) -> LLMResult: ...

    def chat(self, system: str, messages: list[dict], temperature: float = 0.2) -> str:
        return self.complete(system, messages, temperature).text

    @abstractmethod
    def stream(self, system: str, messages: list[dict]) -> Iterator[str]: ...
