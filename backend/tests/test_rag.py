import pytest
from fastapi.testclient import TestClient

from app import db
from app.ingestion import youtube
from app.ingestion.youtube import Captions
from app.main import app
from app.models import init_db
from app.routers import chat as chat_router
from app.services import rag
from app.vectorstore.chroma_store import Hit
from tests.fakes import FakeLLM

SEGMENTS = [
    {"text": "welcome to spring boot basics", "start": 0.0, "end": 5.0},
    {"text": "set the database url in application properties", "start": 252.0, "end": 260.0},
    {"text": "thanks for watching see you next time", "start": 600.0, "end": 605.0},
]


@pytest.fixture
def llm(monkeypatch):
    fake = FakeLLM()
    monkeypatch.setattr(chat_router, "get_llm", lambda provider=None: fake)
    return fake


@pytest.fixture
def client(tmp_path, monkeypatch, llm):
    db.configure(f"sqlite:///{tmp_path / 'test.db'}")
    init_db()
    monkeypatch.setattr(
        youtube,
        "fetch_captions",
        lambda vid, languages=None: Captions(segments=SEGMENTS, language="en", is_generated=False),
    )
    monkeypatch.setattr(youtube, "fetch_metadata", lambda vid: {"title": "Spring", "channel": "c"})
    monkeypatch.setattr(rag.settings, "CHUNK_MAX_WORDS", 8)
    monkeypatch.setattr(rag.settings, "CHUNK_OVERLAP_WORDS", 0)
    with TestClient(app) as c:
        c.video_id = c.post("/api/videos", json={"url": "dQw4w9WgXcQ"}).json()["id"]
        yield c


def test_find_citations_and_seconds():
    text = "Set it [04:12]. Again [04:12] and [1:02:05], not [abc]."
    assert rag.find_citations(text) == ["04:12", "1:02:05"]
    assert rag.to_seconds("04:12") == 252
    assert rag.to_seconds("1:02:05") == 3725


def test_context_has_timestamps_and_title():
    hits = [Hit(1, 0, 252.0, 260.0, "database url", 0.9, "Spring")]
    context = rag.build_context(hits)
    assert context.startswith("<context>")
    assert "[04:12] (until 04:20) from video 'Spring'" in context
    assert "database url" in context


def test_chat_uses_retrieved_chunks(client, llm):
    llm.replies = ["Database URL properties file mein set karo [04:12]."]
    r = client.post(
        "/api/chat", json={"question": "database url kahan set karein", "video_id": client.video_id}
    )
    data = r.json()
    assert r.status_code == 200
    assert data["found"] is True
    assert data["citations"] == [{"timestamp": "04:12", "seconds": 252}]
    assert any(s["timestamp"] == "04:12" for s in data["sources"])
    call = llm.calls[0]
    assert call["temperature"] <= 0.3
    assert "Answer ONLY from the transcript" in call["system"]
    assert "set the database url" in call["messages"][-1]["content"]


def test_chat_not_found(client, llm):
    llm.replies = ["NOT_FOUND"]
    data = client.post(
        "/api/chat", json={"question": "kubernetes kya hai", "video_id": client.video_id}
    ).json()
    assert data["found"] is False
    assert data["citations"] == []
    assert "nahi mila" in data["answer"]


def test_chat_keeps_history(client, llm):
    history = [
        {"role": "user", "content": "video kis baare mein hai"},
        {"role": "assistant", "content": "Spring Boot [00:00]"},
    ]
    client.post(
        "/api/chat",
        json={"question": "aur database?", "video_id": client.video_id, "history": history},
    )
    assert llm.calls[0]["messages"][:2] == history


def test_chat_errors(client, llm, monkeypatch):
    assert (
        client.post("/api/chat", json={"question": "hi there", "video_id": 99}).status_code == 404
    )

    def broken(*args, **kwargs):
        raise RuntimeError("rate limit")

    monkeypatch.setattr(llm, "complete", broken)
    r = client.post("/api/chat", json={"question": "database", "video_id": client.video_id})
    assert r.status_code == 502


def test_chat_bad_provider(client, monkeypatch):
    def bad(provider=None):
        raise ValueError("Unknown LLM provider 'x'")

    monkeypatch.setattr(chat_router, "get_llm", bad)
    r = client.post("/api/chat", json={"question": "database", "provider": "x"})
    assert r.status_code == 400


def test_compare_with_and_without_rag(client, llm):
    llm.replies = ["Generic answer about Spring.", "Properties file [04:12]."]
    data = client.post(
        "/api/chat/compare", json={"question": "database url?", "video_id": client.video_id}
    ).json()
    assert data["without_rag"]["citations"] == []
    assert data["with_rag"]["citations"][0]["timestamp"] == "04:12"
    assert "<context>" not in llm.calls[0]["messages"][0]["content"]
