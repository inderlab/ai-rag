from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


@dataclass
class LLMResult:
    text: str
    input_tokens: int
    output_tokens: int


@dataclass
class StructuredResult(Generic[T]):
    data: T
    input_tokens: int
    output_tokens: int


class LLMProvider(ABC):
    name: str
    model: str
    supports_temperature: bool = True

    @abstractmethod
    def complete(
        self, system: str, messages: list[dict], temperature: float = 0.2
    ) -> LLMResult: ...

    def chat(self, system: str, messages: list[dict], temperature: float = 0.2) -> str:
        return self.complete(system, messages, temperature).text

    @abstractmethod
    def stream(
        self, system: str, messages: list[dict], temperature: float = 0.2
    ) -> Iterator[str]: ...

    @abstractmethod
    def structured(
        self, system: str, messages: list[dict], schema: type[T], temperature: float = 0.2
    ) -> StructuredResult[T]: ...
