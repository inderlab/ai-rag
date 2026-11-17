import pytest
from fastapi.testclient import TestClient

from app import db
from app.ingestion import youtube
from app.ingestion.chunker import chunk_segments, chunk_words, shared_segments, stats
from app.ingestion.youtube import Captions
from app.main import app
from app.models import init_db


def make_segments(n: int, words: int = 5, length: float = 4.0) -> list[dict]:
    return [
        {
            "text": " ".join(f"s{i}w{j}" for j in range(words)),
            "start": i * length,
            "end": (i + 1) * length,
        }
        for i in range(n)
    ]


def test_empty_input_gives_no_chunks():
    assert chunk_segments([]) == []
    assert chunk_segments([{"text": "   ", "start": 0, "end": 1}]) == []
    assert chunk_words("") == []


def test_chunks_respect_max_words():
    chunks = chunk_segments(make_segments(20), max_words=20, overlap_words=5)
    assert all(c.word_count <= 20 for c in chunks)
    assert chunks[0].word_count == 20


def test_overlap_repeats_previous_segments():
    chunks = chunk_segments(make_segments(20), max_words=20, overlap_words=5)
    first, second = chunks[0], chunks[1]
    assert first.last_segment == 3
    assert second.first_segment == 3
    assert shared_segments(first, second) == 1
    assert second.text.startswith("s3w0")
    assert first.text.endswith("s3w4")


def test_no_overlap_when_zero():
    chunks = chunk_segments(make_segments(20), max_words=20, overlap_words=0)
    assert len(chunks) == 5
    assert all(shared_segments(a, b) == 0 for a, b in zip(chunks, chunks[1:], strict=False))
    assert sum(c.word_count for c in chunks) == 100


def test_timestamps_keep_going_up():
    chunks = chunk_segments(make_segments(50), max_words=30, overlap_words=10)
    assert chunks[0].start == 0.0
    assert chunks[-1].end == 200.0
    for a, b in zip(chunks, chunks[1:], strict=False):
        assert b.start > a.start
        assert b.end > a.end
        assert b.start <= a.end
    assert [c.position for c in chunks] == list(range(len(chunks)))


def test_every_segment_is_covered():
    segments = make_segments(37)
    chunks = chunk_segments(segments, max_words=23, overlap_words=7)
    covered = {i for c in chunks for i in range(c.first_segment, c.last_segment + 1)}
    assert covered == set(range(37))


def test_long_segment_is_split_with_time_spread():
    segments = [{"text": " ".join(f"w{i}" for i in range(25)), "start": 0.0, "end": 25.0}]
    chunks = chunk_segments(segments, max_words=10, overlap_words=0)
    assert [c.word_count for c in chunks] == [10, 10, 5]
    assert [(c.start, c.end) for c in chunks] == [(0.0, 10.0), (10.0, 20.0), (20.0, 25.0)]


def test_bigger_chunks_mean_fewer_chunks():
    segments = make_segments(100)
    counts = [len(chunk_segments(segments, size, size // 5)) for size in (25, 100, 600)]
    assert counts[0] > counts[1] > counts[2] == 1


def test_bad_sizes_raise():
    with pytest.raises(ValueError):
        chunk_segments(make_segments(3), max_words=0)
    with pytest.raises(ValueError):
        chunk_segments(make_segments(3), max_words=10, overlap_words=10)


def test_chunk_words_overlap():
    text = " ".join(str(i) for i in range(10))
    assert chunk_words(text, max_words=4, overlap_words=1) == ["0 1 2 3", "3 4 5 6", "6 7 8 9"]
    assert chunk_words("a b c", max_words=4, overlap_words=1) == ["a b c"]


def test_stats():
    chunks = chunk_segments(make_segments(10), max_words=20, overlap_words=0)
    assert stats(chunks) == {"count": 3, "avg_words": 16.7, "min_words": 10, "max_words": 20}
    assert stats([])["count"] == 0


@pytest.fixture
def client(tmp_path, monkeypatch):
    db.configure(f"sqlite:///{tmp_path / 'test.db'}")
    init_db()
    segments = make_segments(60, words=10, length=5.0)
    monkeypatch.setattr(
        youtube,
        "fetch_captions",
        lambda vid, languages=None: Captions(segments=segments, language="en", is_generated=False),
    )
    monkeypatch.setattr(youtube, "fetch_metadata", lambda vid: {"title": "t", "channel": "c"})
    with TestClient(app) as c:
        yield c


def add_video(client) -> int:
    return client.post("/api/videos", json={"url": "dQw4w9WgXcQ"}).json()["id"]


def test_preview_route():
    with TestClient(app) as c:
        r = c.post(
            "/api/chunks/preview",
            json={"text": "a b c d e f g", "max_words": 3, "overlap_words": 1},
        )
    data = r.json()
    assert data["count"] == 3
    assert [ch["text"] for ch in data["chunks"]] == ["a b c", "c d e", "e f g"]


def test_preview_rejects_big_overlap():
    with TestClient(app) as c:
        r = c.post("/api/chunks/preview", json={"text": "a b", "max_words": 3, "overlap_words": 3})
    assert r.status_code == 422


def test_video_chunks_route(client):
    video_id = add_video(client)
    data = client.get(f"/api/videos/{video_id}/chunks?max_words=100&overlap_words=20").json()
    assert data["segment_count"] == 60
    assert data["stats"]["max_words"] <= 100
    first, second = data["chunks"][0], data["chunks"][1]
    assert first["timestamp"] == "00:00"
    assert first["end_timestamp"] == "00:50"
    assert second["shared_with_previous"] == 2
    assert second["timestamp"] == "00:40"


def test_video_chunks_compare_route(client):
    video_id = add_video(client)
    data = client.get(f"/api/videos/{video_id}/chunks/compare?sizes=50,200,800").json()
    counts = [s["stats"]["count"] for s in data["sizes"]]
    assert counts[0] > counts[1] > counts[2] == 1
    assert data["sizes"][2]["first_chunk"] == "00:00 - 05:00"


def test_video_chunks_bad_requests(client):
    video_id = add_video(client)
    assert client.get("/api/videos/999/chunks").status_code == 404
    assert (
        client.get(f"/api/videos/{video_id}/chunks?max_words=20&overlap_words=20").status_code
        == 422
    )
    assert client.get(f"/api/videos/{video_id}/chunks/compare?sizes=5").status_code == 422
    assert client.get(f"/api/videos/{video_id}/chunks/compare?sizes=abc").status_code == 422
