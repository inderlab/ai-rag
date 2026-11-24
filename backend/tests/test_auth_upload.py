import pytest
from fastapi.testclient import TestClient

from app import db
from app.auth import create_token, hash_password, verify_password
from app.config import settings
from app.ingestion import whisper, youtube
from app.ingestion.whisper import AudioError, Transcript
from app.ingestion.youtube import Captions
from app.main import app
from app.models import User, init_db
from app.vectorstore.chroma_store import get_store

YT_SEGMENTS = [{"text": "public spring boot talk about database url", "start": 0.0, "end": 5.0}]
UPLOAD_SEGMENTS = [
    {"text": "welcome to this short lesson on docker", "start": 0.0, "end": 2.4},
    {"text": "use volumes so your data survives a restart", "start": 17.5, "end": 21.6},
]


class FakeWhisper:
    name = "fake-whisper"

    def __init__(self):
        self.files = []
        self.fail: Exception | None = None

    def transcribe(self, path):
        self.files.append(path)
        if self.fail:
            raise self.fail
        return Transcript(segments=list(UPLOAD_SEGMENTS), language="en", duration=21.6)


@pytest.fixture
def stt():
    fake = FakeWhisper()
    whisper.set_transcriber(fake)
    yield fake
    whisper.set_transcriber(None)


@pytest.fixture
def client(tmp_path, monkeypatch, stt):
    db.configure(f"sqlite:///{tmp_path / 'test.db'}")
    init_db()
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setattr(
        youtube,
        "fetch_captions",
        lambda vid, languages=None: Captions(
            segments=YT_SEGMENTS, language="en", is_generated=False
        ),
    )
    monkeypatch.setattr(youtube, "fetch_metadata", lambda vid: {"title": "Public", "channel": "c"})
    with TestClient(app) as c:
        yield c


def register(client, email: str, name: str = "Test") -> dict:
    r = client.post(
        "/api/auth/register", json={"name": name, "email": email, "password": "secret-123"}
    )
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def upload(client, headers=None, name="lesson.mp4", data=b"fake-mp4-bytes", title=None):
    form = {"title": title} if title else None
    return client.post(
        "/api/videos/upload",
        files={"file": (name, data, "video/mp4")},
        data=form,
        headers=headers or {},
    )


def test_password_hashing():
    hashed = hash_password("secret-123")
    assert hashed != "secret-123"
    assert verify_password("secret-123", hashed)
    assert not verify_password("wrong", hashed)
    assert not verify_password("x", "not-a-hash")


def test_register_login_me(client):
    headers = register(client, "Inder@Example.com", "Inder")
    me = client.get("/api/auth/me", headers=headers).json()
    assert me["email"] == "inder@example.com"
    login = client.post(
        "/api/auth/login", json={"email": "inder@example.com", "password": "secret-123"}
    )
    assert login.status_code == 200
    assert login.json()["user"]["name"] == "Inder"


def test_auth_errors(client):
    register(client, "a@example.com")
    dup = client.post(
        "/api/auth/register", json={"name": "x", "email": "a@example.com", "password": "secret-123"}
    )
    assert dup.status_code == 409
    bad = client.post("/api/auth/login", json={"email": "a@example.com", "password": "nope-nope"})
    assert bad.status_code == 401
    short = client.post(
        "/api/auth/register", json={"name": "x", "email": "b@example.com", "password": "123"}
    )
    assert short.status_code == 422
    assert client.get("/api/auth/me").status_code == 401
    garbage = client.get("/api/auth/me", headers={"Authorization": "Bearer abc.def.ghi"})
    assert garbage.status_code == 401


def test_short_secret_is_replaced(monkeypatch):
    from app import auth

    auth.secret.cache_clear()
    monkeypatch.setattr(settings, "JWT_SECRET", "short")
    assert len(auth.secret()) >= 32
    auth.secret.cache_clear()
    monkeypatch.setattr(settings, "JWT_SECRET", "x" * 40)
    assert auth.secret() == "x" * 40
    auth.secret.cache_clear()


def test_expired_token(client):
    register(client, "old@example.com")
    with db.SessionLocal() as s:
        user = s.query(User).filter_by(email="old@example.com").one()
        token = create_token(user, minutes=-1)
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_auth_required_mode(client, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_REQUIRED", True)
    assert client.get("/api/auth/config").json() == {"auth_required": True}
    assert client.get("/api/videos").status_code == 401
    headers = register(client, "c@example.com")
    assert client.get("/api/videos", headers=headers).status_code == 200
    assert client.get("/api/health").status_code == 200


def test_upload_is_transcribed_and_indexed(client, stt):
    headers = register(client, "u@example.com", "Uma")
    r = upload(client, headers, title="Docker lesson")
    assert r.status_code == 202
    video = client.get(f"/api/videos/{r.json()['id']}", headers=headers).json()
    assert video["status"] == "ready"
    assert video["source"] == "upload"
    assert video["private"] is True
    assert video["title"] == "Docker lesson"
    assert video["channel"] == "Uma"
    assert video["duration"] == "00:21"
    assert video["media_url"] == f"/api/videos/{video['id']}/media"
    assert video["thumbnail_url"] == ""
    assert len(stt.files) == 1
    hits = get_store().search("docker volumes", video_id=video["id"])
    assert hits and hits[0].text.startswith("welcome to this short lesson")


def test_uploads_are_private(client):
    alice = register(client, "alice@example.com", "Alice")
    bob = register(client, "bob@example.com", "Bob")
    mine = upload(client, alice).json()["id"]
    public = client.post("/api/videos", json={"url": "dQw4w9WgXcQ"}, headers=alice).json()["id"]

    alice_ids = {v["id"] for v in client.get("/api/videos", headers=alice).json()}
    bob_ids = {v["id"] for v in client.get("/api/videos", headers=bob).json()}
    assert alice_ids == {mine, public}
    assert bob_ids == {public}
    assert client.get(f"/api/videos/{mine}", headers=bob).status_code == 404
    assert client.delete(f"/api/videos/{mine}", headers=bob).status_code == 404
    assert client.get(f"/api/videos/{mine}/media", headers=bob).status_code == 404

    alice_search = client.get("/api/search", params={"q": "docker lesson"}, headers=alice).json()
    bob_search = client.get("/api/search", params={"q": "docker lesson"}, headers=bob).json()
    assert mine in {h["video_id"] for h in alice_search["results"]}
    upload_hit = next(h for h in alice_search["results"] if h["video_id"] == mine)
    assert upload_hit["url"].startswith(f"http://localhost:5173/videos/{mine}?t=")
    assert "youtube.com" not in upload_hit["url"]
    public_hit = next(h for h in alice_search["results"] if h["video_id"] == public)
    assert public_hit["url"].startswith("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=")
    assert mine not in {h["video_id"] for h in bob_search["results"]}
    assert public in {h["video_id"] for h in bob_search["results"]}


def test_media_route_streams_file_with_ranges(client):
    headers = register(client, "m@example.com")
    data = bytes(range(256)) * 40
    video_id = upload(client, headers, data=data).json()["id"]
    r = client.get(f"/api/videos/{video_id}/media", headers=headers)
    assert r.status_code == 200
    assert r.content == data
    assert r.headers["content-type"] == "video/mp4"
    part = client.get(f"/api/videos/{video_id}/media", headers={**headers, "Range": "bytes=0-99"})
    assert part.status_code == 206
    assert len(part.content) == 100
    token = headers["Authorization"].split()[1]
    assert client.get(f"/api/videos/{video_id}/media?token={token}").status_code == 200


def test_upload_validation(client, monkeypatch):
    assert upload(client, name="notes.pdf").status_code == 415
    assert upload(client, data=b"").status_code == 400
    monkeypatch.setattr(settings, "UPLOAD_MAX_MB", 0)
    assert upload(client).status_code == 413


def test_upload_without_speech_or_audio_fails_cleanly(client, stt):
    stt.fail = AudioError("Could not read audio from the file: Invalid data found")
    video_id = upload(client).json()["id"]
    v = client.get(f"/api/videos/{video_id}").json()
    assert v["status"] == "failed"
    assert v["error"].startswith("Could not read audio")


def test_delete_removes_upload_file(client, tmp_path):
    video_id = upload(client).json()["id"]
    files = list((tmp_path / "uploads").iterdir())
    assert len(files) == 1
    assert client.delete(f"/api/videos/{video_id}").status_code == 204
    assert not files[0].exists()


def test_load_audio_reports_bad_files(tmp_path):
    bad = tmp_path / "broken.mp4"
    bad.write_bytes(b"not a real video")
    try:
        whisper.ffmpeg_bin()
    except AudioError:
        pytest.skip("ffmpeg not installed")
    with pytest.raises(AudioError):
        whisper.load_audio(bad)


def test_anonymous_cannot_see_private_uploads(client):
    alice = register(client, "anon-test@example.com")
    private = upload(client, alice, title="Secret plan").json()["id"]
    shared = client.post("/api/videos", json={"url": "dQw4w9WgXcQ"}).json()["id"]
    assert {v["id"] for v in client.get("/api/videos").json()} == {shared}
    assert client.get(f"/api/videos/{private}").status_code == 404
    hits = client.get("/api/search", params={"q": "docker lesson"}).json()["results"]
    assert private not in {h["video_id"] for h in hits}
    assert client.get(f"/api/videos/{private}/media").status_code == 404


def test_old_chunks_get_user_id_backfilled(tmp_path):
    from app.vectorstore.chroma_store import ChromaStore

    store = ChromaStore(str(tmp_path / "old"), "old_chunks")
    store.collection.add(
        ids=["9:0"],
        embeddings=[[1.0] + [0.0] * 63],
        documents=["legacy chunk"],
        metadatas=[{"video_id": 9, "position": 0, "start": 0.0, "end": 5.0, "title": ""}],
    )
    assert store.search("legacy", user_id=0) == []
    reopened = ChromaStore(str(tmp_path / "old"), "old_chunks")
    assert reopened.backfill_user_ids() == 0
    assert [h.video_id for h in reopened.search("legacy", user_id=0)] == [9]
