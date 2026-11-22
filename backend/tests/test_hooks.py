import json

import httpx
import pytest
from fastapi.testclient import TestClient
from youtube_transcript_api import TranscriptsDisabled

from app import db
from app.config import settings
from app.ingestion import youtube
from app.ingestion.youtube import Captions
from app.main import app
from app.models import init_db
from app.services import hooks

SEGMENTS = [{"text": "welcome to spring boot", "start": 0.0, "end": 5.0}]


@pytest.fixture
def sent(tmp_path, monkeypatch):
    db.configure(f"sqlite:///{tmp_path / 'test.db'}")
    init_db()
    calls: list[dict] = []

    def fake_post(url, json=None, timeout=None):
        calls.append({"url": url, "json": json})
        return httpx.Response(200, request=httpx.Request("POST", url))

    monkeypatch.setattr(hooks.httpx, "post", fake_post)
    monkeypatch.setattr(settings, "N8N_WEBHOOK_URL", "http://n8n.local/webhook/vidmind")
    monkeypatch.setattr(youtube, "fetch_metadata", lambda vid: {"title": "Spring", "channel": "c"})
    return calls


def test_ready_video_triggers_webhook(sent, monkeypatch):
    monkeypatch.setattr(
        youtube,
        "fetch_captions",
        lambda vid, languages=None: Captions(segments=SEGMENTS, language="en", is_generated=False),
    )
    with TestClient(app) as c:
        c.post("/api/videos", json={"url": "dQw4w9WgXcQ"})
    assert len(sent) == 1
    body = sent[0]["json"]
    assert body["event"] == "video.ready"
    assert body["video"]["title"] == "Spring"
    assert body["video"]["app_url"].endswith("/videos/1")
    assert body["insights"] is None
    json.dumps(body)


def test_failed_video_triggers_webhook(sent, monkeypatch):
    def boom(vid, languages=None):
        raise TranscriptsDisabled(vid)

    monkeypatch.setattr(youtube, "fetch_captions", boom)
    with TestClient(app) as c:
        c.post("/api/videos", json={"url": "dQw4w9WgXcQ"})
    assert sent[0]["json"]["event"] == "video.failed"
    assert sent[0]["json"]["video"]["error"]


def test_no_webhook_without_url(sent, monkeypatch):
    monkeypatch.setattr(settings, "N8N_WEBHOOK_URL", "")
    assert hooks.notify(1) is False
    assert sent == []


def test_webhook_errors_do_not_break_ingest(sent, monkeypatch):
    def down(url, json=None, timeout=None):
        raise httpx.ConnectError("n8n is down")

    monkeypatch.setattr(hooks.httpx, "post", down)
    monkeypatch.setattr(
        youtube,
        "fetch_captions",
        lambda vid, languages=None: Captions(segments=SEGMENTS, language="en", is_generated=False),
    )
    with TestClient(app) as c:
        video_id = c.post("/api/videos", json={"url": "dQw4w9WgXcQ"}).json()["id"]
        assert c.get(f"/api/videos/{video_id}").json()["status"] == "ready"
