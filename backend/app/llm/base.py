from abc import ABC, abstractmethod
from collections.abc import Iterator


class LLMProvider(ABC):
    """Common interface so the rest of the app doesn't care which model it talks to."""

    name: str
    model: str

    @abstractmethod
    def chat(self, system: str, messages: list[dict], temperature: float = 0.2) -> str: ...

    @abstractmethod
    def stream(self, system: str, messages: list[dict]) -> Iterator[str]: ...

    # structured() gets added on Day 8
