import json
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.llm.base import LLMProvider, LLMResult
from app.llm.prompts import FEW_SHOT_EXAMPLES, GOOD_SYSTEM, build_prompt
from app.main import app
from app.routers import llm as llm_router

client = TestClient(app)


class FakeLLM(LLMProvider):
    def __init__(self, name: str = "fake", fail: bool = False):
        self.name = name
        self.model = f"{name}-1"
        self.fail = fail
        self.calls: list[dict] = []

    def complete(self, system: str, messages: list[dict], temperature: float = 0.2) -> LLMResult:
        if self.fail:
            raise RuntimeError("rate limit")
        self.calls.append({"system": system, "messages": messages})
        return LLMResult(
            text="- one\n- two\n- three", input_tokens=len(messages) * 10, output_tokens=6
        )

    def stream(self, system: str, messages: list[dict], temperature: float = 0.2) -> Iterator[str]:
        if self.fail:
            raise RuntimeError("stream broke")
        yield from ["RAG ", "matlab ", "search + answer"]


@pytest.fixture
def providers(monkeypatch):
    registry = {"openai": FakeLLM("openai"), "claude": FakeLLM("claude")}

    def fake_get_llm(provider=None):
        name = (provider or "openai").lower()
        if name not in registry:
            raise ValueError(f"{name} is not configured")
        return registry[name]

    monkeypatch.setattr(llm_router, "get_llm", fake_get_llm)
    return registry


def read_events(response) -> list[dict]:
    return [
        json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")
    ]


def test_build_prompt_bad_has_no_format():
    system, messages = build_prompt("bad", "Kafka")
    assert system != GOOD_SYSTEM
    assert len(messages) == 1


def test_build_prompt_few_shot_adds_examples_as_history():
    system, messages = build_prompt("few_shot", "Kafka")
    assert system == GOOD_SYSTEM
    assert len(messages) == len(FEW_SHOT_EXAMPLES) * 2 + 1
    assert [m["role"] for m in messages[:2]] == ["user", "assistant"]
    assert messages[-1] == {"role": "user", "content": "Topic: Kafka"}


def test_stream_sends_tokens_then_done(providers):
    r = client.post("/api/llm/stream", json={"prompt": "RAG?"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    events = read_events(r)
    assert events[0]["type"] == "start"
    assert (
        "".join(e["text"] for e in events if e["type"] == "token") == "RAG matlab search + answer"
    )
    assert events[-1]["type"] == "done"
    assert events[-1]["chunks"] == 3


def test_stream_reports_provider_error_as_event(providers):
    providers["openai"].fail = True
    events = read_events(client.post("/api/llm/stream", json={"prompt": "x"}))
    assert events[-1]["type"] == "error"


def test_stream_unknown_provider_is_400(providers):
    r = client.post("/api/llm/stream", json={"prompt": "x", "provider": "gemini"})
    assert r.status_code == 400


def test_compare_runs_every_provider(providers):
    r = client.post("/api/llm/compare", json={"prompt": "hi"})
    assert r.status_code == 200
    data = r.json()
    assert [x["provider"] for x in data["results"]] == ["openai", "claude"]
    assert all(x["status"] == "ok" for x in data["results"])
    assert data["fastest"] in {"openai", "claude"}


def test_compare_marks_missing_and_failing_providers(providers):
    providers["claude"].fail = True
    r = client.post("/api/llm/compare", json={"prompt": "hi", "providers": ["claude", "gemini"]})
    status = {x["provider"]: x["status"] for x in r.json()["results"]}
    assert status == {"claude": "error", "gemini": "not_configured"}
    assert r.json()["fastest"] is None


def test_prompt_styles_returns_each_style(providers):
    r = client.post("/api/llm/prompt-styles", json={"topic": "Kafka"})
    assert r.status_code == 200
    results = r.json()["results"]
    assert [x["style"] for x in results] == ["bad", "good", "few_shot"]
    assert results[2]["input_tokens"] > results[1]["input_tokens"]
    assert results[0]["bullet_count"] == 3


def test_prompt_styles_rejects_unknown_style(providers):
    r = client.post("/api/llm/prompt-styles", json={"styles": ["magic"]})
    assert r.status_code == 422
