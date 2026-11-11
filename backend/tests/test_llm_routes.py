from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.llm.base import LLMProvider, LLMResult
from app.main import app
from app.routers import llm as llm_router

client = TestClient(app)


class FakeLLM(LLMProvider):
    name = "fake"
    model = "fake-1"

    def __init__(self):
        self.calls: list[dict] = []

    def complete(self, system: str, messages: list[dict], temperature: float = 0.2) -> LLMResult:
        self.calls.append({"system": system, "messages": messages, "temperature": temperature})
        text = "same" if temperature == 0 else f"random-{len(self.calls)}"
        return LLMResult(text=text, input_tokens=10, output_tokens=3)

    def stream(self, system: str, messages: list[dict]) -> Iterator[str]:
        yield "x"


@pytest.fixture
def fake(monkeypatch):
    f = FakeLLM()
    monkeypatch.setattr(llm_router, "get_llm", lambda provider=None: f)
    return f


def test_providers_lists_both():
    r = client.get("/api/llm/providers")
    assert r.status_code == 200
    assert {p["name"] for p in r.json()} == {"openai", "claude"}


def test_llm_test_returns_usage(fake):
    r = client.post("/api/llm/test", json={"prompt": "hi", "temperature": 0})
    assert r.status_code == 200
    data = r.json()
    assert data["answer"] == "same"
    assert data["input_tokens"] == 10
    assert data["output_tokens"] == 3


def test_llm_test_rejects_bad_temperature():
    r = client.post("/api/llm/test", json={"temperature": 2})
    assert r.status_code == 422


def test_chat_sends_full_history(fake):
    history = [
        {"role": "user", "content": "Mera naam Inder hai"},
        {"role": "assistant", "content": "Namaste Inder"},
        {"role": "user", "content": "Mera naam kya hai?"},
    ]
    r = client.post("/api/llm/chat", json={"messages": history})
    assert r.status_code == 200
    assert fake.calls[0]["messages"] == history
    assert r.json()["messages"][-1]["role"] == "assistant"
    assert len(r.json()["messages"]) == 4


def test_chat_rejects_assistant_last(fake):
    r = client.post("/api/llm/chat", json={"messages": [{"role": "assistant", "content": "hi"}]})
    assert r.status_code == 400


def test_temperature_compare(fake):
    r = client.post("/api/llm/temperature", json={"prompt": "q", "temperatures": [0, 1], "runs": 3})
    assert r.status_code == 200
    data = r.json()
    assert len(data["results"]) == 6
    assert data["identical_by_temperature"] == {"0.0": True, "1.0": False}
