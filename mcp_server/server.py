import os
from typing import Any

import httpx
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations

API_URL = os.getenv("VIDMIND_API_URL", "http://127.0.0.1:8000/api")
API_KEY = os.getenv("VIDMIND_API_KEY", "")
TIMEOUT = float(os.getenv("VIDMIND_TIMEOUT", "180"))

transport: httpx.BaseTransport | None = None

server = MCPServer(
    name="vidmind",
    log_level="WARNING",
    title="VidMind AI",
    instructions=(
        "Tools for the user's VidMind video library. Use list_videos to find video ids, "
        "search_videos to find moments by meaning, ask_video for answers with [mm:ss] "
        "citations, get_video_summary for title, summary and chapters, and ingest_youtube "
        "to add a new YouTube link. Always keep the [mm:ss] timestamps in your reply."
    ),
)

READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=False)


class VidMindError(ToolError):
    pass


def client() -> httpx.Client:
    headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}
    return httpx.Client(
        base_url=API_URL, timeout=TIMEOUT, headers=headers, transport=transport
    )


def call(method: str, path: str, **kwargs: Any) -> Any:
    try:
        with client() as c:
            r = c.request(method, path, **kwargs)
    except httpx.HTTPError as e:
        raise VidMindError(f"VidMind API is not reachable at {API_URL}: {e}") from e
    if r.status_code >= 400:
        try:
            detail = r.json().get("detail", r.text)
        except ValueError:
            detail = r.text
        raise VidMindError(f"VidMind API error {r.status_code}: {detail}")
    return r.json() if r.content else None


@server.tool(
    description="List videos in the library with id, title, status and length.",
    annotations=READ_ONLY,
)
def list_videos(status: str | None = None) -> str:
    videos = call("GET", "/videos", params={"status": status} if status else None)
    if not videos:
        return "The library is empty. Use ingest_youtube to add a video."
    return "\n".join(
        f"- id {v['id']}: {v['title'] or v['youtube_id']} ({v['status']}, {v['duration'] or '?'})"
        for v in videos
    )


@server.tool(
    description="Find the moments in the library (or one video) whose meaning matches the query.",
    annotations=READ_ONLY,
)
def search_videos(query: str, video_id: int | None = None, k: int = 6) -> str:
    params: dict[str, Any] = {"q": query, "k": max(1, min(k, 20))}
    if video_id is not None:
        params["video_id"] = video_id
    hits = call("GET", "/search", params=params)["results"]
    if not hits:
        return "No matching moments found."
    return "\n\n".join(
        f"{h['rank']}. [{h['timestamp']}] {h['title']} (video {h['video_id']}, "
        f"score {h['score']:.2f})\n{h['url']}\n{h['text'][:400]}"
        for h in hits
    )


@server.tool(
    description=(
        "Ask a question about one video (or the whole library when video_id is empty). "
        "The answer cites [mm:ss] timestamps from the transcript."
    ),
    annotations=READ_ONLY,
)
def ask_video(
    question: str, video_id: int | None = None, provider: str | None = None
) -> str:
    data = call(
        "POST",
        "/chat",
        json={"question": question, "video_id": video_id, "provider": provider},
    )
    lines = [data["answer"], ""]
    if data.get("sources"):
        lines.append("Sources:")
        lines += [
            f"- [{s['timestamp']}] {s['title'] or 'video ' + str(s['video_id'])}"
            for s in data["sources"][:5]
        ]
    lines.append(
        f"(agent path: {' > '.join(data['steps'])}; "
        f"citations verified: {'yes' if data['verified'] else 'no'})"
    )
    return "\n".join(lines)


@server.tool(
    description="Get the title, summary, chapters, tags and key points of a video.",
    annotations=READ_ONLY,
)
def get_video_summary(video_id: int) -> str:
    try:
        data = call("GET", f"/videos/{video_id}/insights")
    except VidMindError as e:
        if "404" not in str(e) or "No insights" not in str(e):
            raise
        data = call("POST", f"/videos/{video_id}/insights", json={})
    chapters = "\n".join(f"- [{c['start']}] {c['title']}" for c in data["chapters"])
    points = "\n".join(f"- {p}" for p in data.get("key_points", []))
    return (
        f"# {data['title']}\n\n{data['summary']}\n\nChapters:\n{chapters}\n\n"
        f"Key points:\n{points}\n\nTags: {', '.join(data['tags'])}"
    )


@server.tool(
    description=(
        "Add a YouTube video to the library. It is processed in the background; "
        "check list_videos until its status is ready."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=True),
)
def ingest_youtube(url: str) -> str:
    v = call("POST", "/videos", json={"url": url})
    return (
        f"Video id {v['id']} ({v['youtube_id']}) status: {v['status']}. "
        "Transcript, chunks and vectors are built in the background."
    )


def main() -> None:
    transport_name = os.getenv("MCP_TRANSPORT", "stdio")
    server.run(transport_name)


if __name__ == "__main__":
    main()
