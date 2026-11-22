import json

import anyio
import httpx
import pytest
from mcp import Client
from mcp_server import server as mcp

VIDEO = {
    "id": 2,
    "youtube_id": "zjkBMFhNj_g",
    "title": "Intro to LLMs",
    "status": "ready",
    "duration": "59:49",
}
HIT = {
    "rank": 1,
    "video_id": 2,
    "title": "Intro to LLMs",
    "timestamp": "46:18",
    "url": "https://www.youtube.com/watch?v=zjkBMFhNj_g&t=2778s",
    "score": 0.86,
    "text": "jailbreak example",
}
CHAT = {
    "answer": "A jailbreak tricks the model [46:18].",
    "sources": [{"timestamp": "46:18", "title": "Intro to LLMs", "video_id": 2}],
    "steps": ["router:qa", "retriever:6", "answer", "verifier:ok"],
    "verified": True,
}
INSIGHTS = {
    "title": "Busy person's intro",
    "summary": "Two files.",
    "chapters": [{"start": "00:00", "title": "Intro"}],
    "tags": ["llm"],
    "key_points": ["140 GB"],
}


@pytest.fixture
def api(monkeypatch):
    seen: list[httpx.Request] = []
    state = {"insights": False}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        path = request.url.path.removeprefix("/api")
        if path == "/videos" and request.method == "GET":
            return httpx.Response(200, json=[VIDEO])
        if path == "/videos" and request.method == "POST":
            return httpx.Response(202, json={**VIDEO, "status": "pending"})
        if path == "/search":
            return httpx.Response(200, json={"results": [HIT]})
        if path == "/chat":
            return httpx.Response(200, json=CHAT)
        if path == "/videos/2/insights" and request.method == "GET":
            if state["insights"]:
                return httpx.Response(200, json=INSIGHTS)
            return httpx.Response(404, json={"detail": "No insights yet, POST to generate them"})
        if path == "/videos/2/insights" and request.method == "POST":
            state["insights"] = True
            return httpx.Response(200, json=INSIGHTS)
        return httpx.Response(404, json={"detail": "Video not found"})

    monkeypatch.setattr(mcp, "transport", httpx.MockTransport(handler))
    return seen


def call(name: str, args: dict) -> tuple[str, bool]:
    async def go():
        async with Client(mcp.server) as c:
            result = await c.call_tool(name, args)
            return result.content[0].text, bool(result.is_error)

    return anyio.run(go)


def test_lists_all_tools():
    async def go():
        async with Client(mcp.server) as c:
            return {t.name: t for t in (await c.list_tools()).tools}

    tools = anyio.run(go)
    assert set(tools) == {
        "list_videos",
        "search_videos",
        "ask_video",
        "get_video_summary",
        "ingest_youtube",
    }
    assert tools["search_videos"].annotations.read_only_hint is True
    assert tools["ingest_youtube"].annotations.read_only_hint is False


def test_search_videos(api):
    text, error = call("search_videos", {"query": "jailbreak", "k": 50})
    assert not error
    assert "[46:18] Intro to LLMs" in text
    assert api[0].url.params["k"] == "20"


def test_ask_video_sends_question(api):
    text, _ = call("ask_video", {"question": "jailbreak kya hai", "video_id": 2})
    assert "[46:18]" in text
    assert "verified: yes" in text
    assert json.loads(api[0].content)["video_id"] == 2


def test_summary_generates_when_missing(api):
    text, _ = call("get_video_summary", {"video_id": 2})
    assert text.startswith("# Busy person's intro")
    assert [r.method for r in api] == ["GET", "POST"]


def test_ingest_and_list(api):
    text, _ = call("ingest_youtube", {"url": "https://youtu.be/zjkBMFhNj_g"})
    assert "Video id 2" in text and "pending" in text
    text, _ = call("list_videos", {})
    assert "id 2: Intro to LLMs (ready, 59:49)" in text


def test_api_errors_become_tool_errors(api):
    text, error = call("get_video_summary", {"video_id": 99})
    assert error
    assert "Video not found" in text


def test_api_down(monkeypatch):
    def boom(request):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(mcp, "transport", httpx.MockTransport(boom))
    text, error = call("list_videos", {})
    assert error and "not reachable" in text


def test_api_key_header(api, monkeypatch):
    monkeypatch.setattr(mcp, "API_KEY", "secret")
    call("list_videos", {})
    assert api[0].headers["authorization"] == "Bearer secret"
