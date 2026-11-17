import hashlib
import math
import os

import pytest
from fastapi.testclient import TestClient

from app import db
from app.ingestion import embedder, youtube
from app.ingestion.youtube import Captions
from app.main import app
from app.models import init_db
from app.routers import embeddings as embeddings_router

DIM = 64


class FakeModel:
    name = "fake-bow"
    dimension = DIM

    def __init__(self):
        self.encoded: list[str] = []

    def encode(self, texts: list[str]) -> list[list[float]]:
        self.encoded.extend(texts)
        out = []
        for text in texts:
            vec = [0.0] * DIM
            for word in text.lower().split()[1:]:
                vec[int(hashlib.md5(word.encode()).hexdigest(), 16) % DIM] += 1.0
            norm = math.sqrt(sum(x * x for x in vec)) or 1.0
            out.append([x / norm for x in vec])
        return out


@pytest.fixture
def fake_model():
    model = FakeModel()
    embedder.set_model(model)
    embeddings_router.clear_cache()
    yield model
    embedder.set_model(None)
    embeddings_router.clear_cache()


@pytest.fixture
def client(tmp_path, monkeypatch, fake_model):
    db.configure(f"sqlite:///{tmp_path / 'test.db'}")
    init_db()
    segments = [
        {"text": "welcome to spring boot", "start": 0.0, "end": 5.0},
        {"text": "set database url in properties", "start": 252.0, "end": 260.0},
        {"text": "thanks for watching", "start": 600.0, "end": 605.0},
    ]
    monkeypatch.setattr(
        youtube,
        "fetch_captions",
        lambda vid, languages=None: Captions(segments=segments, language="en", is_generated=False),
    )
    monkeypatch.setattr(youtube, "fetch_metadata", lambda vid: {"title": "t", "channel": "c"})
    with TestClient(app) as c:
        yield c


def test_cosine_basics():
    assert embedder.cosine([1, 0], [1, 0]) == pytest.approx(1.0)
    assert embedder.cosine([1, 0], [0, 1]) == pytest.approx(0.0)
    assert embedder.cosine([1, 0], [-1, 0]) == pytest.approx(-1.0)
    assert embedder.cosine([0, 0], [1, 0]) == 0.0
    with pytest.raises(ValueError):
        embedder.cosine([1, 0], [1, 0, 0])


def test_prefix_and_whitespace():
    assert embedder.add_prefix("  DB   kaise\nconnect ", "query") == "query: DB kaise connect"


def test_embed_adds_prefix_per_kind(fake_model):
    embedder.embed(["a b"], kind="passage")
    embedder.embed_query("c d")
    assert fake_model.encoded == ["passage: a b", "query: c d"]
    assert embedder.embed([]) == []


def test_info_reports_model(client):
    data = client.get("/api/embeddings/info").json()
    assert data == {"model": "fake-bow", "loaded": True, "dimension": DIM}


def test_create_embeddings_returns_unit_vectors(client):
    r = client.post("/api/embeddings", json={"texts": ["hello world"], "full": True})
    item = r.json()["items"][0]
    assert r.json()["dimension"] == DIM
    assert len(item["preview"]) == 8
    assert len(item["vector"]) == DIM
    assert item["norm"] == pytest.approx(1.0)


def test_create_embeddings_hides_full_vector_by_default(client):
    item = client.post("/api/embeddings", json={"texts": ["x y"]}).json()["items"][0]
    assert item["vector"] is None


def test_similarity_ranks_best_first(client):
    r = client.post(
        "/api/embeddings/similarity",
        json={"query": "database url", "passages": ["weather is nice", "set the database url"]},
    )
    results = r.json()["results"]
    assert results[0]["text"] == "set the database url"
    assert results[0]["rank"] == 1
    assert results[0]["score"] > results[1]["score"]


def test_embed_rejects_too_many_texts(client):
    assert client.post("/api/embeddings", json={"texts": ["a"] * 65}).status_code == 422


def test_semantic_search_on_segments_uses_cache(client, fake_model):
    video_id = client.post("/api/videos", json={"url": "dQw4w9WgXcQ"}).json()["id"]

    first = client.post(
        f"/api/videos/{video_id}/semantic-search",
        json={"q": "database url", "k": 2, "unit": "segment"},
    )
    data = first.json()
    assert data["unit"] == "segment"
    assert data["cached"] is False
    assert data["items_embedded"] == 3
    assert data["results"][0]["timestamp"] == "04:12"
    assert data["results"][0]["keyword_match"] is True
    assert len(data["results"]) == 2

    second = client.post(
        f"/api/videos/{video_id}/semantic-search", json={"q": "spring boot", "unit": "segment"}
    )
    assert second.json()["cached"] is True
    assert second.json()["results"][0]["timestamp"] == "00:00"


def test_semantic_search_on_chunks_by_default(client):
    video_id = client.post("/api/videos", json={"url": "dQw4w9WgXcQ"}).json()["id"]
    r = client.post(
        f"/api/videos/{video_id}/semantic-search",
        json={"q": "database url", "max_words": 10, "overlap_words": 0},
    )
    data = r.json()
    assert data["unit"] == "chunk"
    assert data["items_embedded"] == 2
    assert data["results"][0]["text"] == "welcome to spring boot set database url in properties"
    assert data["results"][0]["end_timestamp"] == "04:20"


def test_semantic_search_rejects_big_overlap(client):
    video_id = client.post("/api/videos", json={"url": "dQw4w9WgXcQ"}).json()["id"]
    r = client.post(
        f"/api/videos/{video_id}/semantic-search",
        json={"q": "database", "max_words": 10, "overlap_words": 10},
    )
    assert r.status_code == 422


def test_semantic_search_unknown_video_is_404(client):
    r = client.post("/api/videos/999/semantic-search", json={"q": "hello"})
    assert r.status_code == 404


@pytest.mark.skipif(os.getenv("RUN_MODEL_TESTS") != "1", reason="set RUN_MODEL_TESTS=1")
def test_real_model_matches_meaning_across_languages():
    embedder.set_model(None)
    ranked = embedder.rank(
        "database kaise connect karein",
        [
            "aaj mausam bahut achha hai",
            "application.properties mein datasource URL set karo",
            "डेटाबेस कनेक्शन के लिए URL सेट करें",
        ],
    )
    assert ranked[-1][0] == 0
    assert embedder.get_model().dimension == 384
