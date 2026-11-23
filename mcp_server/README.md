# VidMind MCP server

A thin MCP server over the VidMind HTTP API, so Claude Desktop, Cursor or any MCP client can use your video library.

| Tool | What it does | API call |
|---|---|---|
| `list_videos` | Videos with id, title, status, length | `GET /api/videos` |
| `search_videos` | Moments that match a query, with `[mm:ss]` and a link | `GET /api/search` |
| `ask_video` | Answer from one video or the whole library, with citations | `POST /api/chat` |
| `get_video_summary` | Title, summary, chapters, tags, key points | `GET/POST /api/videos/{id}/insights` |
| `ingest_youtube` | Add a YouTube link | `POST /api/videos` |

## Run

The backend must be running first (`uvicorn app.main:app` in `backend/`).

```bash
cd backend && source .venv/bin/activate
pip install -r ../mcp_server/requirements.txt
python ../mcp_server/server.py                         # stdio, for Claude Desktop
MCP_TRANSPORT=streamable-http python ../mcp_server/server.py   # HTTP, for remote clients
```

Settings (environment variables):

| Name | Default |
|---|---|
| `VIDMIND_API_URL` | `http://127.0.0.1:8000/api` |
| `VIDMIND_API_KEY` | empty; put a login token here (from `POST /api/auth/login`) when the backend runs with `AUTH_REQUIRED=true` or to include your private uploads |
| `VIDMIND_TIMEOUT` | `180` seconds |
| `MCP_TRANSPORT` | `stdio` |

## Claude Desktop

Settings → Developer → Edit Config, then add (use your own absolute paths):

```json
{
  "mcpServers": {
    "vidmind": {
      "command": "/ABSOLUTE/PATH/vidmind-ai/backend/.venv/bin/python",
      "args": ["/ABSOLUTE/PATH/vidmind-ai/mcp_server/server.py"],
      "env": { "VIDMIND_API_URL": "http://127.0.0.1:8000/api" }
    }
  }
}
```

Restart Claude Desktop and ask: *"Search my VidMind library for jailbreak attacks and summarise what the video says."*

## Test

```bash
cd backend && pytest tests/test_mcp_server.py
```
