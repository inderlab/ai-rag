# VidMind AI — Video Content AI Assistant

**Stack:** Python (FastAPI) · ChromaDB · LangGraph multi-agent · MCP (Python) · React + Vite · n8n · Docker
**Timeline:** 7 days (1 week)
**Goal:** A portfolio project for GitHub and resume (Backend / AI Engineer roles)

---

## 1. What the app does

A user uploads a video **or pastes a YouTube URL**. The app:

1. Builds a timestamped transcript (YouTube captions, or Whisper for uploads).
2. Splits it into chunks, creates embeddings and stores them in **ChromaDB**.
3. Auto-generates a **title, summary, chapters, tags and quiz/notes** (structured outputs).
4. Lets the user **chat with the video** — every answer cites clickable timestamps like `[04:12]` that seek the player.
5. Lets the user **search across all their videos** at once.
6. Exposes the library through an **MCP server**, so Claude Desktop / Cursor can search and ask your videos.
7. Uses **n8n** to send a "video ready" notification and auto-ingest new uploads from a YouTube channel.

**Differentiators (vs existing "chat with YouTube" tools):**
- Upload **and** YouTube, multi-video library search (not just one video)
- **Hindi / Hinglish support** (multilingual Whisper + multilingual embeddings)
- **Multi-agent** pipeline with an answer-verifier agent (citation check)
- **Evaluation script** with real retrieval accuracy numbers
- Production touches: background jobs, Docker Compose, CI, clean README

---

## 2. Architecture

```
                    ┌──────────────────────┐
                    │  React + Vite (TS)   │  upload, YouTube URL, player, chat
                    └──────────┬───────────┘
                               │ REST + SSE (streaming)
                    ┌──────────▼───────────┐        ┌─────────────────┐
  n8n  ───────────► │   FastAPI backend    │ ◄───── │  MCP server     │ ◄── Claude Desktop
  (webhooks, cron)  │  auth, videos, chat  │        │  (Python, FastMCP)│
                    └───┬──────────┬───────┘        └─────────────────┘
                        │          │
             background │          │ LangGraph agents
                  jobs  │          │ (router → retriever → answer → verifier)
                        ▼          ▼
            ┌────────────────┐   ┌────────────────┐   ┌─────────────────┐
            │ Ingestion      │──►│   ChromaDB     │   │  SQLite/Postgres│
            │ captions /     │   │  chunks +      │   │  users, videos, │
            │ Whisper, chunk,│   │  embeddings +  │   │  chats, status  │
            │ embed          │   │  metadata      │   └─────────────────┘
            └────────────────┘   └────────────────┘
                     │
                     ▼
              OpenAI / local models (Whisper, embeddings, GPT)
```

**Two halves:**
- **Indexing** (once per video, background): URL/upload → transcript → chunks → embeddings → ChromaDB
- **Querying** (every message): question → agents → ChromaDB search → LLM → answer + `[mm:ss]`

---

## 3. Tech stack

| Layer | Tool | Why |
|---|---|---|
| Frontend | React 18 + Vite + TypeScript + Tailwind | Fast dev server, modern setup |
| Video player | `react-player` | Plays YouTube and MP4, supports `seekTo(seconds)` |
| Backend | FastAPI + Uvicorn | Async, auto Swagger docs at `/docs` |
| ORM / DB | SQLAlchemy + SQLite (dev) / PostgreSQL (prod) | Users, videos, chats, job status |
| Auth | JWT (`python-jose`) + `passlib[bcrypt]` | Simple, standard |
| Background jobs | FastAPI `BackgroundTasks` (Day 1–5) → Celery + Redis (stretch) | Keep week-1 simple |
| Vector DB | **ChromaDB** (persistent client) | Easy, Python-native, metadata filters |
| Embeddings | OpenAI `text-embedding-3-small` **or** `intfloat/multilingual-e5-small` (free, local, Hindi support) | Choose by budget |
| Transcript | `youtube-transcript-api`; `faster-whisper` (local) or OpenAI Whisper API | Captions first, Whisper fallback |
| Audio | FFmpeg | Extract audio from uploads |
| LLM | **Pluggable provider layer:** OpenAI (ChatGPT models) **or** Anthropic Claude (`claude-haiku-5-5` / `claude-sonnet-5-5`), switched by `LLM_PROVIDER` in `.env`; optional local models via Ollama | One interface, any model — see section 5.6 |
| Multi-agent | **LangGraph** | Graph of agents with shared state |
| MCP | `mcp` Python SDK (`FastMCP`) | Expose tools to AI assistants |
| Automation | n8n | Webhooks, schedules, notifications |
| DevOps | Docker Compose, GitHub Actions, pytest | One-command setup, CI |

**YouTube note:** use captions (`youtube-transcript-api`) as the main path. Downloading YouTube audio with `yt-dlp` is against YouTube's terms for most videos — keep that only for videos you own, and mention it in the README.

---

## 4. Multi-agent design (LangGraph)

```
              ┌──────────────┐
 question ──► │ Router Agent │  decides: qa / summary / search_library / quiz
              └──────┬───────┘
         ┌───────────┼──────────────┬───────────────┐
         ▼           ▼              ▼               ▼
  ┌────────────┐ ┌─────────────┐ ┌──────────────┐ ┌───────────┐
  │ Retriever  │ │ Summarizer  │ │ Library      │ │ Quiz/Notes│
  │ Agent      │ │ Agent       │ │ Search Agent │ │ Agent     │
  └─────┬──────┘ └──────┬──────┘ └──────┬───────┘ └─────┬─────┘
        ▼               │               │               │
  ┌────────────┐        │               │               │
  │ Answer     │        │               │               │
  │ Agent      │        │               │               │
  └─────┬──────┘        │               │               │
        ▼               ▼               ▼               ▼
  ┌──────────────────────────────────────────────────────────┐
  │ Verifier Agent — checks every [mm:ss] exists in the      │
  │ retrieved chunks; if not, asks Answer Agent to retry once │
  └──────────────────────────────────────────────────────────┘
```

| Agent | Input | Output | Notes |
|---|---|---|---|
| **Router** | question, video_id | intent (`qa`, `summary`, `search_library`, `quiz`) | Structured output with a Pydantic schema |
| **Retriever** | question, video_id | top-k chunks with timestamps | Query rewriting (Hinglish → clean query), ChromaDB search with `where={"video_id": ...}` |
| **Answer** | question + chunks | answer with `[mm:ss]` citations | "Answer only from context; if not found, say so" |
| **Summarizer** | video_id | summary, chapters | Map-reduce for long videos |
| **Library Search** | question | matching videos + timestamps | ChromaDB search without video filter |
| **Quiz/Notes** | video_id | 5 MCQs + study notes | Structured JSON |
| **Verifier** | answer + chunks | pass / retry | Regex for `[mm:ss]`, check each falls inside a retrieved chunk's range |

**Shared state:**

```python
from typing import TypedDict, Literal

class AgentState(TypedDict, total=False):
    question: str
    video_id: str | None
    intent: Literal["qa", "summary", "search_library", "quiz"]
    chunks: list[dict]          # {text, start, end, video_id, score}
    answer: str
    citations: list[float]
    retries: int
```

**Graph wiring (sketch):**

```python
from langgraph.graph import StateGraph, END

graph = StateGraph(AgentState)
graph.add_node("router", router_node)
graph.add_node("retriever", retriever_node)
graph.add_node("answer", answer_node)
graph.add_node("summarizer", summarizer_node)
graph.add_node("library_search", library_search_node)
graph.add_node("quiz", quiz_node)
graph.add_node("verifier", verifier_node)

graph.set_entry_point("router")
graph.add_conditional_edges("router", lambda s: s["intent"], {
    "qa": "retriever",
    "summary": "summarizer",
    "search_library": "library_search",
    "quiz": "quiz",
})
graph.add_edge("retriever", "answer")
graph.add_edge("answer", "verifier")
graph.add_conditional_edges("verifier",
    lambda s: "retry" if s.get("retries", 0) == 1 and not s.get("citations") else "done",
    {"retry": "answer", "done": END})
for node in ["summarizer", "library_search", "quiz"]:
    graph.add_edge(node, END)

agent_app = graph.compile()
```

---

## 5. Core pipeline (how RAG + embeddings + ChromaDB work)

### 5.1 Transcript

```python
from youtube_transcript_api import YouTubeTranscriptApi

def youtube_segments(video_id: str, langs=("en", "hi")) -> list[dict]:
    rows = YouTubeTranscriptApi().fetch(video_id, languages=list(langs))
    return [{"text": r.text, "start": r.start, "end": r.start + r.duration} for r in rows]
```

For uploads: `ffmpeg -i input.mp4 -vn -ac 1 -ar 16000 audio.wav`, then `faster-whisper` → segments with `start` / `end`.
(Check the current `youtube-transcript-api` docs — its API changed between versions.)

### 5.2 Chunking with timestamps

Whisper/caption segments are 2–10 s long — too small. Merge them:

```python
def build_chunks(segments, max_words=300, overlap=2):
    chunks, buf = [], []
    for seg in segments:
        buf.append(seg)
        if sum(len(s["text"].split()) for s in buf) >= max_words:
            chunks.append(_pack(buf))
            buf = buf[-overlap:]          # overlap keeps context across the cut
    if buf:
        chunks.append(_pack(buf))
    return chunks

def _pack(segs):
    return {"text": " ".join(s["text"] for s in segs),
            "start": segs[0]["start"], "end": segs[-1]["end"]}
```

### 5.3 Embeddings + ChromaDB

```python
import chromadb
from chromadb.utils import embedding_functions

client = chromadb.PersistentClient(path="./data/chroma")

embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="intfloat/multilingual-e5-small"   # free, local, supports Hindi
)
# or: embedding_functions.OpenAIEmbeddingFunction(api_key=..., model_name="text-embedding-3-small")

collection = client.get_or_create_collection(
    name="video_chunks",
    embedding_function=embed_fn,
    metadata={"hnsw:space": "cosine"},
)

def index_video(video_id: str, user_id: str, chunks: list[dict]):
    collection.add(
        ids=[f"{video_id}_{i}" for i in range(len(chunks))],
        documents=[c["text"] for c in chunks],
        metadatas=[{"video_id": video_id, "user_id": user_id,
                    "start": c["start"], "end": c["end"]} for c in chunks],
    )

def search(question: str, video_id: str | None, user_id: str, k: int = 6):
    where = {"$and": [{"user_id": user_id}, {"video_id": video_id}]} if video_id else {"user_id": user_id}
    res = collection.query(query_texts=[question], n_results=k, where=where)
    return [{"text": d, **m, "score": 1 - dist}
            for d, m, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0])]
```

### 5.4 Answer prompt (RAG)

```text
You answer questions about a video using ONLY the transcript chunks below.
Cite the timestamp of every fact in [mm:ss] format.
If the answer is not in the chunks, say: "This is not covered in the video."
Reply in the same language as the question (Hindi, Hinglish or English).

Chunks:
[04:12-05:01] ...
[05:01-05:48] ...

Question: {question}
```

### 5.5 Structured outputs (title, summary, chapters, tags)

```python
from pydantic import BaseModel

class Chapter(BaseModel):
    start: float
    title: str

class VideoInsights(BaseModel):
    title: str
    summary: str
    chapters: list[Chapter]
    tags: list[str]
    language: str

resp = openai_client.beta.chat.completions.parse(
    model="gpt-4o-mini",
    messages=[{"role": "system", "content": "Create insights for this transcript."},
              {"role": "user", "content": transcript_text}],
    response_format=VideoInsights,
)
insights = resp.choices[0].message.parsed
```

### 5.6 LLM provider layer — OpenAI (ChatGPT) or Claude

All agents call **one interface**, never an SDK directly. Switching from ChatGPT to Claude is a one-line `.env` change, and the user can also pick the model per chat from the UI. This is a strong design point to talk about in interviews (adapter / strategy pattern).

```bash
# .env
LLM_PROVIDER=claude            # openai | claude | ollama
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini       # check OpenAI's models page for current names
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-haiku-5-5  # cheap + fast; use claude-sonnet-5-5 for higher quality
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=llama3.1
```

```bash
pip install openai anthropic
```

```python
# backend/app/llm/base.py
from abc import ABC, abstractmethod
from typing import Iterator, Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

class LLMProvider(ABC):
    name: str

    @abstractmethod
    def chat(self, system: str, messages: list[dict], temperature: float = 0.2) -> str: ...

    @abstractmethod
    def stream(self, system: str, messages: list[dict]) -> Iterator[str]: ...

    @abstractmethod
    def structured(self, system: str, user: str, schema: Type[T]) -> T: ...
```

```python
# backend/app/llm/openai_provider.py
from openai import OpenAI
from .base import LLMProvider

class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str, base_url: str | None = None):
        # base_url lets the same class talk to Ollama or any OpenAI-compatible server
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def chat(self, system, messages, temperature=0.2):
        r = self.client.chat.completions.create(
            model=self.model, temperature=temperature,
            messages=[{"role": "system", "content": system}, *messages])
        return r.choices[0].message.content

    def stream(self, system, messages):
        s = self.client.chat.completions.create(
            model=self.model, stream=True,
            messages=[{"role": "system", "content": system}, *messages])
        for chunk in s:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta

    def structured(self, system, user, schema):
        r = self.client.beta.chat.completions.parse(
            model=self.model, response_format=schema,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
        return r.choices[0].message.parsed
```

```python
# backend/app/llm/claude_provider.py
import anthropic
from .base import LLMProvider

class ClaudeProvider(LLMProvider):
    name = "claude"

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def chat(self, system, messages, temperature=0.2):
        r = self.client.messages.create(
            model=self.model, max_tokens=1500, temperature=temperature,
            system=system, messages=messages)          # system is a separate field in Claude's API
        return "".join(b.text for b in r.content if b.type == "text")

    def stream(self, system, messages):
        with self.client.messages.stream(
            model=self.model, max_tokens=1500, system=system, messages=messages
        ) as s:
            for text in s.text_stream:
                yield text

    def structured(self, system, user, schema):
        # Reliable JSON from Claude: force a tool call whose input schema is the Pydantic model
        tool = {"name": "save_result", "description": "Return the result",
                "input_schema": schema.model_json_schema()}
        r = self.client.messages.create(
            model=self.model, max_tokens=2000, system=system,
            tools=[tool], tool_choice={"type": "tool", "name": "save_result"},
            messages=[{"role": "user", "content": user}])
        block = next(b for b in r.content if b.type == "tool_use")
        return schema.model_validate(block.input)
```

```python
# backend/app/llm/factory.py
from functools import lru_cache
from app.config import settings
from .openai_provider import OpenAIProvider
from .claude_provider import ClaudeProvider

@lru_cache
def get_llm(provider: str | None = None):
    p = (provider or settings.LLM_PROVIDER).lower()
    if p == "openai":
        return OpenAIProvider(settings.OPENAI_API_KEY, settings.OPENAI_MODEL)
    if p == "claude":
        return ClaudeProvider(settings.ANTHROPIC_API_KEY, settings.CLAUDE_MODEL)
    if p == "ollama":
        return OpenAIProvider("ollama", settings.OLLAMA_MODEL, base_url=settings.OLLAMA_BASE_URL)
    raise ValueError(f"Unknown LLM provider: {p}")
```

**Using it in an agent:**

```python
def answer_node(state: AgentState) -> AgentState:
    llm = get_llm(state.get("provider"))          # per-chat choice from the UI, else .env default
    context = "\n".join(f"[{fmt(c['start'])}-{fmt(c['end'])}] {c['text']}" for c in state["chunks"])
    text = llm.chat(SYSTEM_PROMPT, [{"role": "user", "content": f"Chunks:\n{context}\n\nQuestion: {state['question']}"}])
    return {**state, "answer": text}
```

Add `provider: str | None` to `AgentState`, and accept `"provider": "openai" | "claude"` in `POST /api/chat`.

**Important notes**
- **Embeddings stay separate from the chat LLM.** Claude has no embeddings endpoint, so keep embeddings on `multilingual-e5-small` (local, free) or OpenAI embeddings. Never mix embedding models inside one ChromaDB collection — vectors from different models are not comparable.
- **Message format differences** (handled inside the providers): OpenAI puts the system prompt inside `messages`; Claude takes `system=` separately and needs `max_tokens`.
- **Cost and fallback:** wrap calls with a retry (e.g. `tenacity`), and if one provider fails or rate-limits, fall back to the other. Log `provider`, `model`, tokens and latency per message in the `messages` table — then show a small "answered by Claude / GPT" badge and compare them in your eval.
- **Comparison idea for the README:** run `eval/run_eval.py --provider openai` and `--provider claude` on the same 20 questions and publish both scores and average latency/cost. That table makes the project stand out.

**Frontend:** a small model dropdown in the chat panel (`ChatGPT (OpenAI)` / `Claude`), sent as `provider` with each message, with the badge shown under each answer.

---

## 6. MCP server (Python, FastMCP)

```python
# mcp_server/server.py
from mcp.server.fastmcp import FastMCP
import httpx, os

API = os.getenv("VIDMIND_API", "http://localhost:8000")
HEADERS = {"X-API-Key": os.getenv("VIDMIND_API_KEY", "")}
mcp = FastMCP("vidmind")

@mcp.tool()
async def search_videos(query: str, limit: int = 5) -> list[dict]:
    """Search all indexed videos and return matching moments with timestamps."""
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{API}/api/search", params={"q": query, "k": limit}, headers=HEADERS)
        return r.json()

@mcp.tool()
async def ask_video(video_id: str, question: str) -> str:
    """Ask a question about one video. Answer includes [mm:ss] citations."""
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(f"{API}/api/chat", json={"video_id": video_id, "question": question}, headers=HEADERS)
        return r.json()["answer"]

@mcp.tool()
async def get_video_summary(video_id: str) -> dict:
    """Return title, summary, chapters and tags for a video."""
    async with httpx.AsyncClient() as c:
        return (await c.get(f"{API}/api/videos/{video_id}", headers=HEADERS)).json()

@mcp.tool()
async def ingest_youtube(url: str) -> dict:
    """Queue a YouTube video for indexing."""
    async with httpx.AsyncClient() as c:
        return (await c.post(f"{API}/api/videos", json={"youtube_url": url}, headers=HEADERS)).json()

if __name__ == "__main__":
    mcp.run()
```

**Claude Desktop config** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "vidmind": {
      "command": "python",
      "args": ["/absolute/path/to/mcp_server/server.py"],
      "env": { "VIDMIND_API": "http://localhost:8000", "VIDMIND_API_KEY": "your-key" }
    }
  }
}
```

---

## 7. n8n workflows

1. **Video ready** — backend calls `POST {N8N_URL}/webhook/video-ready` with `{video_id, title, status}` → send Email / Telegram / Slack.
2. **YouTube channel watcher** — Schedule (every hour) → RSS Read `https://www.youtube.com/feeds/videos.xml?channel_id=XXX` → if new → HTTP Request `POST /api/videos`.
3. **Weekly digest** — every Monday → `GET /api/stats` → OpenAI node writes a short digest → Email.

Export each workflow as JSON into `n8n/`.

---

## 8. API endpoints (FastAPI)

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/auth/register`, `/api/auth/login` | JWT auth |
| POST | `/api/videos` | Create from `youtube_url` or uploaded file; starts background indexing |
| POST | `/api/videos/upload` | Multipart upload (MP4) |
| GET | `/api/videos` | List user's videos with status |
| GET | `/api/videos/{id}` | Detail: status, title, summary, chapters, tags |
| DELETE | `/api/videos/{id}` | Delete video + its ChromaDB chunks |
| POST | `/api/chat` | Run the agent graph; returns answer + citations |
| GET | `/api/chat/stream` | Same, streamed with SSE |
| GET | `/api/search?q=` | Library-wide semantic search |
| GET | `/api/videos/{id}/quiz` | Quiz + notes |
| GET | `/api/stats` | Counts for dashboard / n8n |

**Video status flow:** `QUEUED → FETCHING_TRANSCRIPT → INDEXING → GENERATING_INSIGHTS → READY` (or `FAILED` + error)

---

## 9. Folder structure

```text
vidmind-ai/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, routers
│   │   ├── config.py            # pydantic-settings, .env
│   │   ├── db.py                # SQLAlchemy engine/session
│   │   ├── models.py            # User, Video, Chat, Message
│   │   ├── schemas.py           # Pydantic request/response models
│   │   ├── auth.py              # JWT, password hashing
│   │   ├── routers/             # auth.py, videos.py, chat.py, search.py
│   │   ├── ingestion/           # youtube.py, whisper.py, chunker.py, pipeline.py
│   │   ├── vectorstore/         # chroma_store.py
│   │   ├── agents/              # state.py, router.py, retriever.py, answer.py,
│   │   │                        # summarizer.py, quiz.py, verifier.py, graph.py
│   │   └── llm/                 # base.py, openai_provider.py, claude_provider.py, factory.py
│   ├── tests/                   # test_chunker.py, test_search.py, test_api.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                    # React + Vite + TS
│   ├── src/
│   │   ├── api/client.ts        # axios instance + JWT
│   │   ├── pages/               # Login, Library, VideoPage, Search
│   │   ├── components/          # UploadBox, UrlInput, Player, ChatPanel,
│   │   │                        # TimestampLink, Chapters, StatusBadge
│   │   └── hooks/               # useVideo, useChatStream
│   ├── vite.config.ts
│   └── Dockerfile
├── mcp_server/server.py
├── n8n/*.json
├── eval/
│   ├── questions.json           # [{video_id, question, expected_start}]
│   └── run_eval.py              # hit rate @ k
├── docker-compose.yml           # backend, frontend, n8n (+ redis, postgres optional)
├── .github/workflows/ci.yml     # lint + pytest + frontend build
├── .env.example
└── README.md
```

---

## 10. Frontend key piece (timestamp → seek)

```tsx
// components/ChatMessage.tsx
const TS = /\[(\d{1,2}):(\d{2})\]/g;

export function ChatMessage({ text, onSeek }: { text: string; onSeek: (s: number) => void }) {
  const parts = text.split(TS);
  // split with capture groups gives: [text, mm, ss, text, mm, ss, ...]
  const out = [];
  for (let i = 0; i < parts.length; i++) {
    if (i % 3 === 0) out.push(<span key={i}>{parts[i]}</span>);
    else if (i % 3 === 1) {
      const sec = Number(parts[i]) * 60 + Number(parts[i + 1]);
      out.push(
        <button key={i} onClick={() => onSeek(sec)} className="text-blue-600 underline mx-1">
          [{parts[i]}:{parts[i + 1]}]
        </button>
      );
    }
  }
  return <p>{out}</p>;
}

// In VideoPage: playerRef.current?.seekTo(sec, "seconds")
```

---

## 11. 7-day plan

Each day ends with something that runs and a few commits.

### Day 1 — Setup + YouTube transcript
- [ ] Create repo, folder structure, `.env.example`, `requirements.txt`
- [ ] FastAPI skeleton, SQLite + SQLAlchemy models (`User`, `Video`)
- [ ] JWT register/login
- [ ] `youtube.py`: extract video ID from any URL format (`youtu.be`, `watch?v=`, `shorts/`), fetch captions
- [ ] `POST /api/videos` with `youtube_url` → saves video, fetches transcript in background
- **Done when:** paste a URL in Swagger `/docs` → transcript saved

### Day 2 — Chunking + embeddings + ChromaDB
- [ ] `chunker.py` with timestamps + overlap; unit tests
- [ ] `chroma_store.py`: add, search, delete by `video_id`
- [ ] Indexing pipeline with status updates
- [ ] `GET /api/search?q=` for quick testing
- **Done when:** a search returns the right chunks with start/end times

### Day 3 — RAG chat + structured outputs + uploads
- [ ] LLM provider layer (`base.py`, `openai_provider.py`, `claude_provider.py`, `factory.py`) — test both with one prompt
- [ ] RAG answer with `[mm:ss]` citations through `get_llm()`
- [ ] `POST /api/chat` (single agent for now)
- [ ] `VideoInsights` structured output → title, summary, chapters, tags saved on video
- [ ] Upload endpoint + FFmpeg + faster-whisper fallback
- **Done when:** ask 5 questions on a video, answers cite correct timestamps

### Day 4 — Multi-agent with LangGraph
- [ ] `AgentState`, Router (structured intent), Retriever (with query rewrite), Answer, Verifier
- [ ] Summarizer, Library Search, Quiz/Notes agents
- [ ] Replace single-agent chat with `agent_app.invoke(...)`
- [ ] SSE streaming endpoint
- **Done when:** "summarize this", "make a quiz", "which of my videos mention Docker" each route to the right agent

### Day 5 — React + Vite frontend
- [ ] `npm create vite@latest frontend -- --template react-ts`, Tailwind, React Router, axios
- [ ] Login, Library (cards + status badges, polling), Add video (URL + upload)
- [ ] Video page: `react-player`, chapters list, chat panel with clickable timestamps, quiz tab
- [ ] Model dropdown in chat (ChatGPT / Claude) + "answered by" badge
- [ ] Global search page
- **Done when:** full flow works in the browser

### Day 6 — MCP + n8n + evaluation
- [ ] MCP server with 4 tools; connect Claude Desktop; screen-record it
- [ ] n8n: video-ready notification + YouTube channel watcher; export JSON
- [ ] `eval/questions.json` (20 questions with expected timestamps) + `run_eval.py` → hit rate @6
- [ ] Tune chunk size / k based on eval; note before/after numbers
- **Done when:** eval prints a number you can put on your resume

### Day 7 — Docker, CI, README, launch
- [ ] Dockerfiles + `docker-compose.yml` (backend, frontend, n8n)
- [ ] GitHub Actions: `ruff` + `pytest` + `npm run build`
- [ ] README: problem, features, architecture diagram, setup, screenshots/GIF, eval results, limitations, what's next
- [ ] Record a 2-minute demo video; deploy (Render / Railway / EC2)
- [ ] Pin repo on GitHub, LinkedIn post
- **Done when:** a stranger can clone and run it with `docker compose up`

---

## 12. Git: commits under your own name

Set your identity once (this is what shows on GitHub):

```bash
git config --global user.name  "Inderjeet Kumar"
git config --global user.email "inder74et@gmail.com"   # the email linked to your GitHub
git log --format='%an <%ae>' | head                    # verify author
```

Good practice that also makes the repo look like real engineering work:
- **Commit small and often, every day** (a 7-day history with 30–50 commits looks natural; one giant "initial commit" does not).
- Write commit messages yourself, in a consistent style:
  `feat: add youtube transcript fetch`, `fix: handle shorts URLs`, `test: chunker overlap cases`, `refactor: move chroma logic to store`
- Use a branch per feature (`feat/agents`, `feat/frontend`) and merge with PRs into `main`.
- Never commit `.env` or API keys — add them to `.gitignore` from Day 1.

**Most important:** read and understand every file before you commit it — rename things your way, simplify where you can, and add comments in your own words. In interviews you will be asked *why* you chose ChromaDB, how chunk overlap works, how the verifier agent decides to retry. If you can explain and change the code confidently, it is your project.

---

## 13. Resume entry (add after it is live)

**VidMind AI — Multi-Agent Video Content Assistant** | github.com/inderlab/vidmind-ai
*Python, FastAPI, LangGraph, ChromaDB, OpenAI, Claude API, Whisper, MCP, n8n, React, Vite, Docker*

- Built a RAG platform where users upload videos or paste YouTube URLs and chat with them; answers cite clickable timestamps that seek the player.
- Designed a LangGraph multi-agent pipeline (router, retriever, answer, summarizer, quiz and verifier agents) with a citation-check retry loop to reduce hallucinations.
- Built a pluggable LLM layer (OpenAI and Anthropic Claude behind one interface, with fallback) and compared both providers on the same eval set.
- Implemented timestamp-aware chunking, multilingual embeddings and ChromaDB metadata-filtered search, supporting Hindi and Hinglish content.
- Built a Python MCP server exposing video search and Q&A to Claude Desktop, and n8n workflows for notifications and auto-ingesting new channel uploads.
- Measured retrieval quality with a [N]-question eval set (hit rate @6: [X]% → [Y]% after tuning). *Fill in your real numbers.*

---

## 14. Interview questions to prepare

1. Why ChromaDB? When would you move to pgvector, Qdrant or Pinecone?
2. How does chunk size and overlap affect answer quality?
3. What does cosine similarity measure? What is an HNSW index?
4. Why a multi-agent graph instead of one big prompt? What does the verifier check?
5. How do you prevent hallucinations? (Context-only prompt, citations, verifier, "not covered" fallback.)
6. How do you handle a 2-hour video? (Background job, chunked Whisper, map-reduce summary, progress status.)
7. What is MCP and how is it different from normal function calling?
8. How did you evaluate retrieval, and what did you change after the first run?
9. How would you scale to 10,000 videos and many users? (Celery workers, separate vector DB service, per-user filters, caching.)
10. How do multilingual embeddings handle a Hinglish question against a Hindi transcript?

---

## 15. Stretch goals (after week 1)

- Celery + Redis for real job queue with retries
- PostgreSQL + pgvector version for comparison (good blog post)
- Hybrid search (BM25 + vectors) with reranking
- Speaker diarization ("who said what")
- Video frame captions (vision model) for content not in speech
- Shareable public chat link per video
