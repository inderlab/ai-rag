import pytest
from fastapi.testclient import TestClient

from app import db
from app.config import settings
from app.ingestion import youtube
from app.ingestion.chunker import Chunk
from app.ingestion.youtube import Captions
from app.main import app
from app.models import init_db
from app.routers import insights as insights_router
from app.services import insights
from app.services.insights import Chapter, VideoInsights
from tests.fakes import FakeLLM

SEGMENTS = [
    {"text": "welcome to spring boot basics", "start": 0.0, "end": 5.0},
    {"text": "set the database url in application properties", "start": 252.0, "end": 260.0},
    {"text": "thanks for watching see you next time", "start": 600.0, "end": 605.0},
]

REPLY = {
    "title": " Spring Boot database setup ",
    "summary": "Shows how to connect Spring Boot to a database.",
    "chapters": [
        {"start": "[04:12]", "title": "Database URL"},
        {"start": "00:03", "title": "Intro"},
        {"start": "04:12", "title": "Duplicate"},
        {"start": "99:00", "title": "Too late"},
        {"start": "soon", "title": "Broken"},
    ],
    "tags": ["#Spring", "spring", "Database "],
    "key_points": ["Set the URL in properties", " "],
}


@pytest.fixture
def llm(monkeypatch):
    fake = FakeLLM()
    monkeypatch.setattr(insights_router, "get_llm", lambda provider=None: fake)
    monkeypatch.setattr(insights, "get_llm", lambda provider=None: fake)
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
    with TestClient(app) as c:
        c.video_id = c.post("/api/videos", json={"url": "dQw4w9WgXcQ"}).json()["id"]
        yield c


def test_clean_fixes_chapters_and_tags():
    data = insights.clean(VideoInsights(**REPLY), duration=605.0)
    assert data.title == "Spring Boot database setup"
    assert [c.start for c in data.chapters] == ["00:00", "04:12"]
    assert data.chapters[0].title == "Intro"
    assert data.chapters[1].title == "Database URL"
    assert data.tags == ["spring", "database"]
    assert data.key_points == ["Set the URL in properties"]


def test_timed_blocks_put_a_marker_every_30_seconds():
    from types import SimpleNamespace as S

    segs = [S(position=i, start=i * 10.0, end=i * 10.0 + 10, text=f"w{i}") for i in range(7)]
    blocks = insights.timed_blocks(segs)
    assert [(b.start, b.text) for b in blocks] == [
        (0.0, "w0 w1 w2"),
        (30.0, "w3 w4 w5"),
        (60.0, "w6"),
    ]
    assert insights.transcript_text(blocks).startswith("[00:00] w0 w1 w2\n\n[00:30] w3")


def test_groups_split_long_transcripts():
    chunks = [Chunk(i, i * 10.0, i * 10.0 + 10, "w " * 100, 100, i, i) for i in range(5)]
    assert [len(g) for g in insights.groups(chunks, 250)] == [2, 2, 1]
    assert [len(g) for g in insights.groups(chunks, 1000)] == [5]


def test_generate_merges_parts(llm):
    chunks = [Chunk(i, i * 10.0, i * 10.0 + 10, "w " * 100, 100, i, i) for i in range(3)]
    llm.structured_replies = [REPLY, REPLY, REPLY, REPLY]
    data, tokens_in, tokens_out = insights.generate(llm, chunks, 150)
    assert [c["schema"] for c in llm.calls] == ["VideoInsights"] * 4
    assert "partial insights" in llm.calls[-1]["system"]
    assert tokens_in == 2000 and tokens_out == 320
    assert isinstance(data.chapters[0], Chapter)


def test_post_then_get_insights(client, llm):
    llm.structured_replies = [REPLY]
    r = client.post(f"/api/videos/{client.video_id}/insights")
    assert r.status_code == 200
    data = client.get(f"/api/videos/{client.video_id}/insights").json()
    assert data["chapters"] == [
        {"start": "00:00", "title": "Intro", "seconds": 0},
        {"start": "04:12", "title": "Database URL", "seconds": 252},
    ]
    assert data["provider"] == "fake"
    assert "[00:00] welcome to spring boot" in llm.calls[0]["messages"][0]["content"]


def test_get_insights_404_before_generate(client):
    assert client.get(f"/api/videos/{client.video_id}/insights").status_code == 404
    assert client.get("/api/videos/99/insights").status_code == 404


def test_insights_llm_failure_is_502(client, llm):
    r = client.post(f"/api/videos/{client.video_id}/insights")
    assert r.status_code == 502


def test_auto_insights_after_ingest(tmp_path, monkeypatch, llm):
    monkeypatch.setattr(settings, "AUTO_INSIGHTS", True)
    db.configure(f"sqlite:///{tmp_path / 'auto.db'}")
    init_db()
    monkeypatch.setattr(
        youtube,
        "fetch_captions",
        lambda vid, languages=None: Captions(segments=SEGMENTS, language="en", is_generated=False),
    )
    monkeypatch.setattr(youtube, "fetch_metadata", lambda vid: {"title": "Spring", "channel": "c"})
    llm.structured_replies = [REPLY]
    with TestClient(app) as c:
        video_id = c.post("/api/videos", json={"url": "dQw4w9WgXcQ"}).json()["id"]
        assert c.get(f"/api/videos/{video_id}/insights").json()["title"].startswith("Spring")
