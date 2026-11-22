import json

import pytest
from fastapi.testclient import TestClient

from app import db
from app.agents import graph, router, specialists, verifier
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


def route(intent: str, query: str = "database url") -> dict:
    return {"intent": intent, "reason": "test", "search_query": query}


INSIGHTS = {
    "title": "Spring Boot database",
    "summary": "Connect Spring Boot to a database.",
    "chapters": [{"start": "00:00", "title": "Intro"}, {"start": "04:12", "title": "URL"}],
    "tags": ["spring"],
    "key_points": ["Set the URL"],
}

QUIZ = {
    "questions": [
        {
            "question": "URL kahan set hota hai?",
            "options": ["pom.xml", "application properties", "main.java", "README"],
            "answer": 1,
            "explanation": "Video properties file batata hai.",
            "timestamp": "[04:12]",
        },
        {
            "question": "Broken",
            "options": ["a", "b"],
            "answer": 0,
            "explanation": "x",
            "timestamp": "00:00",
        },
    ],
    "notes": ["URL properties mein"],
}


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


def ask(client, question: str, video_id: int | None = -1) -> dict:
    vid = client.video_id if video_id == -1 else video_id
    r = client.post("/api/chat", json={"question": question, "video_id": vid})
    assert r.status_code == 200, r.text
    return r.json()


def test_router_rewrites_query_and_needs_video(llm):
    llm.structured_replies = [route("quiz", "  "), route("qa", "docker basics")]
    out = router.route(llm, {"question": "5 MCQ banao", "video_id": 1})
    assert out["intent"] == "quiz"
    assert out["search_query"] == "5 MCQ banao"
    out = router.route(llm, {"question": "docker kya hai batao", "video_id": None})
    assert out["intent"] == "search_library"
    assert out["search_query"] == "docker basics"


HITS = [Hit(1, 0, 250.0, 262.0, "database url", 0.9)]


def test_verifier_passes_good_citations():
    out = verifier.verify({"answer": "x [04:12]", "citations": ["04:12"], "chunks": HITS})
    assert out["verified"] is True
    assert out["steps"] == ["verifier:ok"]


def test_verifier_asks_for_retry_then_strips():
    state = {"answer": "x [09:00] y [04:12].", "citations": ["09:00", "04:12"], "chunks": HITS}
    first = verifier.verify({**state, "retries": 0})
    assert first["steps"] == ["verifier:retry"]
    assert "[09:00]" in first["verify_notes"][0]
    final = verifier.verify({**state, "retries": 1})
    assert final["steps"] == ["verifier:failed"]
    assert final["citations"] == ["04:12"]
    assert final["answer"] == "x y [04:12]."


def test_verifier_skips_not_found_and_flags_missing_citations():
    assert verifier.check("nahi mila", [], HITS, found=False) == []
    assert "no [mm:ss]" in verifier.check("bas aise hi", [], HITS, found=True)[0]


def test_qa_path_with_retry(client, llm):
    llm.structured_replies = [route("qa")]
    llm.replies = ["Wrong time [08:00].", "Properties file mein [04:12]."]
    data = ask(client, "database url kahan set karein?")
    assert data["intent"] == "qa"
    assert data["steps"] == [
        "router:qa",
        "retriever:3",
        "answer",
        "verifier:retry",
        "answer:retry",
        "verifier:ok",
    ]
    assert data["verified"] is True
    assert data["citations"][0]["timestamp"] == "04:12"
    assert "Your previous answer had problems" in llm.calls[-1]["system"]


def test_retriever_uses_rewritten_query(client, llm, monkeypatch):
    seen = {}
    original = rag.retrieve

    def spy(query, video_id, k):
        seen["query"] = query
        return original(query, video_id, k)

    monkeypatch.setattr(rag, "retrieve", spy)
    llm.structured_replies = [route("qa", "database url properties")]
    llm.replies = ["[04:12] properties."]
    ask(client, "DB ka url kidhar daalna hai bhai?")
    assert seen["query"] == "database url properties"


def test_summary_path_uses_insights(client, llm):
    llm.structured_replies = [route("summary"), INSIGHTS, route("summary")]
    first = ask(client, "is video ka summary do")
    assert first["steps"] == ["router:summary", "summarizer"]
    assert "**Spring Boot database**" in first["answer"]
    assert [c["timestamp"] for c in first["citations"]] == ["00:00", "04:12"]
    second = ask(client, "summary please")
    assert second["input_tokens"] == 500
    assert len([c for c in llm.calls if c.get("schema") == "VideoInsights"]) == 1


def test_quiz_path(client, llm):
    llm.structured_replies = [route("quiz"), QUIZ]
    data = ask(client, "2 MCQ banao")
    assert data["steps"] == ["router:quiz", "quiz:1"]
    assert data["quiz"]["questions"][0]["timestamp"] == "04:12"
    assert "**Q1. URL kahan set hota hai?**" in data["answer"]
    assert "Answer: b)" in data["answer"]


def test_library_path_without_video(client, llm):
    llm.structured_replies = [route("qa")]
    llm.replies = ["Video 'Spring' mein [04:12]."]
    data = ask(client, "kaunsi video database url batati hai", video_id=None)
    assert data["intent"] == "search_library"
    assert data["steps"][1] == "library_search:3/1"
    assert "different videos" in llm.calls[-1]["system"]
    assert "from video 'Spring'" in llm.calls[-1]["messages"][-1]["content"]


def test_spread_keeps_words_under_limit():
    from app.ingestion.chunker import Chunk

    blocks = [Chunk(i, i * 30.0, i * 30.0 + 30, "w " * 100, 100, i, i) for i in range(100)]
    picked = specialists.spread(blocks, 2000)
    assert 18 <= len(picked) <= 21
    assert picked[0].start == 0.0 and picked[-1].start > 2500


def test_stream_sends_steps_tokens_and_done(client, llm):
    llm.structured_replies = [route("qa")]
    llm.replies = ["Properties file mein [04:12]."]
    body = {"question": "database url kahan", "video_id": client.video_id}
    with client.stream("POST", "/api/chat/stream", json=body) as r:
        events = [json.loads(line[6:]) for line in r.iter_lines() if line.startswith("data: ")]
    types = [e["type"] for e in events]
    assert types[0] == "start"
    assert "token" in types and "step" in types
    assert types[-1] == "done"
    tokens = "".join(e["text"] for e in events if e["type"] == "token")
    assert tokens.strip() == "Properties file mein [04:12]."
    assert events[-1]["result"]["verified"] is True


def test_stream_reports_errors(client, llm):
    body = {"question": "database url kahan", "video_id": client.video_id}
    with client.stream("POST", "/api/chat/stream", json=body) as r:
        events = [json.loads(line[6:]) for line in r.iter_lines() if line.startswith("data: ")]
    assert events[-1]["type"] == "error"


def test_graph_run_direct(client, llm):
    llm.structured_replies = [route("qa")]
    llm.replies = ["[04:12] ok."]
    state = graph.run(llm, "database url", client.video_id)
    assert state["verified"] is True
