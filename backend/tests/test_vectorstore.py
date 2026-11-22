import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import db
from app.ingestion import youtube
from app.ingestion.chunker import Chunk
from app.ingestion.youtube import Captions
from app.main import app
from app.models import init_db
from app.vectorstore.chroma_store import ChromaStore, ModelMismatchError, get_store


def chunk(position: int, text_: str, start: float) -> Chunk:
    return Chunk(position, start, start + 10, text_, len(text_.split()), position, position)


def test_add_search_delete():
    store = get_store()
    store.add_chunks(1, [chunk(0, "spring boot database url", 0), chunk(1, "weather today", 10)])
    store.add_chunks(2, [chunk(0, "docker compose database", 0)])
    assert store.count() == 3
    assert store.count(1) == 2

    hits = store.search("database url", video_id=1, k=5)
    assert [h.position for h in hits][0] == 0
    assert all(h.video_id == 1 for h in hits)
    assert hits[0].score > hits[1].score

    library = store.search("database", k=5)
    assert {h.video_id for h in library} == {1, 2}

    store.delete_video(1)
    assert store.count() == 1
    assert store.search("database", video_id=1) == []


def test_add_chunks_replaces_old_chunks():
    store = get_store()
    store.add_chunks(1, [chunk(0, "a b", 0), chunk(1, "c d", 10), chunk(2, "e f", 20)])
    store.add_chunks(1, [chunk(0, "x y", 0)])
    assert store.count(1) == 1


def test_collection_remembers_embedding_model(tmp_path, monkeypatch):
    path = str(tmp_path / "other")
    ChromaStore(path, "model_check")
    from app.ingestion import embedder

    monkeypatch.setattr(embedder, "model_name", lambda: "another-model")
    with pytest.raises(ModelMismatchError):
        ChromaStore(path, "model_check")


SEGMENTS = [
    {"text": "welcome to spring boot", "start": 0.0, "end": 5.0},
    {"text": "set database url in properties", "start": 252.0, "end": 260.0},
    {"text": "thanks for watching", "start": 600.0, "end": 605.0},
]


@pytest.fixture
def client(tmp_path, monkeypatch):
    db.configure(f"sqlite:///{tmp_path / 'test.db'}")
    init_db()
    monkeypatch.setattr(
        youtube,
        "fetch_captions",
        lambda vid, languages=None: Captions(segments=SEGMENTS, language="en", is_generated=False),
    )
    monkeypatch.setattr(youtube, "fetch_metadata", lambda vid: {"title": "Spring", "channel": "c"})
    with TestClient(app) as c:
        yield c


def test_ingest_indexes_chunks(client):
    video = client.post("/api/videos", json={"url": "dQw4w9WgXcQ"}).json()
    data = client.get(f"/api/videos/{video['id']}").json()
    assert data["status"] == "ready"
    assert data["chunk_count"] == 1
    assert get_store().count(video["id"]) == 1


def test_search_route(client):
    video_id = client.post("/api/videos", json={"url": "dQw4w9WgXcQ"}).json()["id"]
    r = client.get("/api/search", params={"q": "database url", "video_id": video_id})
    data = r.json()
    assert r.status_code == 200
    hit = data["results"][0]
    assert hit["title"] == "Spring"
    assert hit["timestamp"] == "00:00"
    assert hit["url"].endswith("&t=0s")
    assert client.get("/api/search", params={"q": "x"}).status_code == 422
    assert client.get("/api/search", params={"q": "db", "video_id": 99}).status_code == 404


def test_vectorstore_info(client):
    client.post("/api/videos", json={"url": "dQw4w9WgXcQ"})
    data = client.get("/api/vectorstore/info").json()
    assert data["chunks"] == 1
    assert data["embedding_model"] == "fake-bow"
    assert data["distance"] == "cosine"


def test_delete_video_removes_vectors(client):
    video_id = client.post("/api/videos", json={"url": "dQw4w9WgXcQ"}).json()["id"]
    assert client.delete(f"/api/videos/{video_id}").status_code == 204
    assert get_store().count() == 0


def test_reindex_route(client):
    video_id = client.post("/api/videos", json={"url": "dQw4w9WgXcQ"}).json()["id"]
    get_store().delete_video(video_id)
    assert client.post(f"/api/videos/{video_id}/reindex").status_code == 202
    assert get_store().count(video_id) == 1
    assert client.post("/api/videos/99/reindex").status_code == 404


def test_indexing_failure_marks_video_failed(client, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("disk full")

    monkeypatch.setattr(ChromaStore, "add_chunks", boom)
    video_id = client.post("/api/videos", json={"url": "dQw4w9WgXcQ"}).json()["id"]
    data = client.get(f"/api/videos/{video_id}").json()
    assert data["status"] == "failed"
    assert "Indexing failed: disk full" in data["error"]


def test_old_database_gets_new_column(tmp_path):
    db.configure(f"sqlite:///{tmp_path / 'old.db'}")
    with db.engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE videos (id INTEGER PRIMARY KEY, source VARCHAR(20), "
                "youtube_id VARCHAR(11), url VARCHAR(500), title VARCHAR(300), "
                "channel VARCHAR(200), status VARCHAR(10), error TEXT, language VARCHAR(20), "
                "is_generated BOOLEAN, duration_seconds FLOAT, segment_count INTEGER, "
                "created_at DATETIME, updated_at DATETIME)"
            )
        )
        conn.execute(text("INSERT INTO videos (id, youtube_id, url) VALUES (1, 'abc', 'u')"))
    init_db()
    with db.engine.begin() as conn:
        assert conn.execute(text("SELECT chunk_count FROM videos")).scalar() == 0
