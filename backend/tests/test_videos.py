import pytest
from fastapi.testclient import TestClient
from youtube_transcript_api import TranscriptsDisabled

from app import db
from app.ingestion import youtube
from app.ingestion.youtube import Captions
from app.main import app
from app.models import Video, VideoStatus, init_db

URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

SEGMENTS = [
    {"text": "Spring Boot intro", "start": 0.0, "end": 4.5},
    {"text": "Database connect karna", "start": 4.5, "end": 9.0},
    {"text": "application.properties mein URL", "start": 252.0, "end": 260.0},
]


@pytest.fixture
def client(tmp_path, monkeypatch):
    db.configure(f"sqlite:///{tmp_path / 'test.db'}")
    init_db()
    state = {"captions_calls": 0, "fail": None}

    def fake_captions(video_id, languages=youtube.DEFAULT_LANGUAGES):
        state["captions_calls"] += 1
        if state["fail"]:
            raise state["fail"]
        return Captions(segments=list(SEGMENTS), language="en", is_generated=True)

    monkeypatch.setattr(youtube, "fetch_captions", fake_captions)
    monkeypatch.setattr(
        youtube, "fetch_metadata", lambda vid: {"title": "Spring Boot", "channel": "Inder"}
    )
    with TestClient(app) as c:
        c.state = state
        yield c


def test_add_video_runs_background_job(client):
    r = client.post("/api/videos", json={"url": URL})
    assert r.status_code == 202
    video_id = r.json()["id"]

    v = client.get(f"/api/videos/{video_id}").json()
    assert v["status"] == "ready"
    assert v["title"] == "Spring Boot"
    assert v["segment_count"] == 3
    assert v["duration"] == "04:20"
    assert v["language"] == "en"


def test_add_same_video_twice_is_deduplicated(client):
    first = client.post("/api/videos", json={"url": URL})
    second = client.post("/api/videos", json={"url": "https://youtu.be/dQw4w9WgXcQ"})
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert client.state["captions_calls"] == 1
    assert len(client.get("/api/videos").json()) == 1


def test_bad_url_is_400(client):
    assert client.post("/api/videos", json={"url": "https://vimeo.com/123"}).status_code == 400


def test_transcript_pagination_and_search(client):
    video_id = client.post("/api/videos", json={"url": URL}).json()["id"]

    page = client.get(f"/api/videos/{video_id}/transcript", params={"limit": 2}).json()
    assert page["total"] == 3
    assert [s["position"] for s in page["segments"]] == [0, 1]

    found = client.get(f"/api/videos/{video_id}/transcript", params={"q": "properties"}).json()
    assert found["total"] == 1
    assert found["segments"][0]["timestamp"] == "04:12"


def test_failed_video_shows_friendly_error_and_can_retry(client):
    client.state["fail"] = TranscriptsDisabled("dQw4w9WgXcQ")
    video_id = client.post("/api/videos", json={"url": URL}).json()["id"]

    v = client.get(f"/api/videos/{video_id}").json()
    assert v["status"] == "failed"
    assert v["error"] == "Captions are turned off for this video"
    assert client.get(f"/api/videos/{video_id}/transcript").status_code == 409

    client.state["fail"] = None
    assert client.post(f"/api/videos/{video_id}/retry").status_code == 202
    assert client.get(f"/api/videos/{video_id}").json()["status"] == "ready"


def test_retry_ready_video_is_409(client):
    video_id = client.post("/api/videos", json={"url": URL}).json()["id"]
    assert client.post(f"/api/videos/{video_id}/retry").status_code == 409


def test_list_filter_by_status(client):
    client.post("/api/videos", json={"url": URL})
    assert len(client.get("/api/videos", params={"status": "ready"}).json()) == 1
    assert client.get("/api/videos", params={"status": "failed"}).json() == []


def test_delete_video_removes_segments(client):
    video_id = client.post("/api/videos", json={"url": URL}).json()["id"]
    assert client.delete(f"/api/videos/{video_id}").status_code == 204
    assert client.get(f"/api/videos/{video_id}").status_code == 404


def test_unknown_video_is_404(client):
    assert client.get("/api/videos/999").status_code == 404


def test_startup_marks_interrupted_jobs_failed(tmp_path):
    db.configure(f"sqlite:///{tmp_path / 'restart.db'}")
    init_db()
    with db.SessionLocal() as s:
        s.add(Video(youtube_id="dQw4w9WgXcQ", url=URL, status=VideoStatus.PROCESSING))
        s.commit()
    with TestClient(app) as c:
        assert c.get("/api/videos/1").json()["status"] == "failed"


def test_friendly_error_falls_back_to_first_line():
    assert youtube.friendly_error(RuntimeError("boom\nlong trace")) == "boom"
