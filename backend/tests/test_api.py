from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_transcript_rejects_bad_url():
    r = client.get("/api/transcript", params={"url": "https://vimeo.com/1"})
    assert r.status_code == 400


def test_llm_unknown_provider():
    r = client.post("/api/llm/test", json={"provider": "gemini"})
    assert r.status_code == 400
