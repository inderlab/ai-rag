import pytest
from fastapi.testclient import TestClient

from app import db
from app.agents import graph, router
from app.ingestion import youtube
from app.ingestion.youtube import Captions
from app.main import app
from app.models import init_db
from app.routers import agent as agent_router
from app.services import rag
from tests.fakes import FakeLLM

SEGMENTS = [
    {"text": "welcome to spring boot basics", "start": 0.0, "end": 5.0},
    {"text": "set the database url in application properties", "start": 252.0, "end": 260.0},
    {"text": "thanks for watching see you next time", "start": 600.0, "end": 605.0},
]


@pytest.fixture
def llm(monkeypatch):
    fake = FakeLLM()
    monkeypatch.setattr(agent_router, "get_llm", lambda provider=None: fake)
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


def test_router_returns_intent(llm):
    llm.structured_replies = [{"intent": "quiz", "reason": "asks for MCQs"}]
    out = router.route(llm, {"question": "5 MCQ banao", "video_id": 1})
    assert out["intent"] == "quiz"
    assert out["steps"] == ["router:quiz"]
    assert "A video is open." in llm.calls[0]["messages"][0]["content"]


def test_router_without_video_searches_library(llm):
    llm.structured_replies = [{"intent": "qa", "reason": "question"}]
    out = router.route(llm, {"question": "docker kya hai", "video_id": None})
    assert out["intent"] == "search_library"


def test_graph_runs_router_retriever_answer(client, llm):
    llm.structured_replies = [{"intent": "qa", "reason": "content question"}]
    llm.replies = ["Properties file mein [04:12]."]
    state = graph.run(llm, "database url kahan", client.video_id)
    assert state["steps"] == ["router:qa", "retriever:3", "answer"]
    assert state["citations"] == ["04:12"]
    assert state["input_tokens"] == 600


def test_agent_route_shows_trace(client, llm):
    llm.structured_replies = [{"intent": "qa", "reason": "content question"}]
    llm.replies = ["Properties file mein [04:12]."]
    r = client.post(
        "/api/agent/chat", json={"question": "database url kahan", "video_id": client.video_id}
    )
    data = r.json()
    assert r.status_code == 200
    assert data["intent"] == "qa"
    assert data["steps"][0] == "router:qa"
    assert data["citations"][0]["seconds"] == 252


def test_agent_route_llm_error_is_502(client, llm):
    r = client.post(
        "/api/agent/chat", json={"question": "hello there", "video_id": client.video_id}
    )
    assert r.status_code == 502
