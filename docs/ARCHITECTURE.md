# Architecture

## Overview

VidMind AI has two flows:

- **Indexing** (once per video, in the background): video → transcript → chunks → embeddings → ChromaDB
- **Querying** (every chat message): question → agents → ChromaDB search → LLM → answer with `[mm:ss]`

```
                     ┌───────────────────────┐
                     │  React + Vite (TS)    │  upload / YouTube URL, player, chat
                     └───────────┬───────────┘
                                 │ REST + SSE
                     ┌───────────▼───────────┐        ┌───────────────┐
   n8n ◄──────────► │    FastAPI backend    │ ◄───── │  MCP server   │ ◄── Claude Desktop
                     │ videos · chat · search│        └───────────────┘
                     └──┬─────────────┬──────┘
          background    │             │  LangGraph agents
          indexing      ▼             ▼
               ┌──────────────┐  ┌──────────────┐  ┌────────────────┐
               │  Ingestion   │─►│   ChromaDB   │  │ SQLite/Postgres│
               │ captions,    │  │ chunks +     │  │ videos,        │
               │              │  │ embeddings + │  │ segments,      │
               │ chunk, embed │  │ metadata     │  └────────────────┘
               └──────────────┘  └──────────────┘
                        │
                        ▼
               LLM providers: OpenAI | Claude | (Ollama)
```

## Backend modules

| Module | Responsibility |
|---|---|
| `app/main.py` | FastAPI app, CORS, router registration |
| `app/config.py` | Settings from `.env` (pydantic-settings) |
| `app/routers/` | HTTP endpoints only |
| `app/llm/` | Provider layer: `LLMProvider` interface, OpenAI + Claude implementations, `get_llm()` factory |
| `app/ingestion/` | YouTube captions, chunking, embeddings |
| `app/services/` | Ingest + indexing job, RAG, insights, transcripts helpers, n8n webhook |
| `app/vectorstore/` | ChromaDB wrapper (add, search, delete) |
| `app/agents/` | LangGraph state, agents and graph |
| `app/db.py`, `app/models.py` | SQLAlchemy engine and tables |

## Data model

| Table | Columns |
|---|---|
| `videos` | id, source, youtube_id, url, title, channel, status, error, language, is_generated, duration_seconds, segment_count, chunk_count, created_at, updated_at |
| `transcript_segments` | id, video_id, position, start, end, text |
| `video_insights` | id, video_id, title, summary, chapters (JSON), tags (JSON), key_points (JSON), provider, model, tokens, created_at |

New columns are added on startup by `add_missing_columns()` (simple SQLite migration).

**ChromaDB collection `vidmind_chunks`** (cosine): `id = {video_id}:{position}`, document = chunk text, embedding = e5 `passage:` vector, metadata = `{video_id, position, start, end, first_segment, last_segment, title}`. The collection stores the embedding model name and the app refuses to mix models.

**Video status:** `pending → processing → indexing → ready` (or `failed`). Jobs that were running when the server stopped are marked failed on startup.

## Multi-agent graph

```
question → Router (intent + search_query) ─┬─ qa ─────────────► Retriever ──────┐
                                           ├─ search_library ─► Library Search ─┴► Answer → Verifier ─┬─ ok ─► END
                                           │                                          ▲               └─ retry (once)
                                           ├─ summary ────────► Summarizer (saved insights) ─────────────────► END
                                           └─ quiz ───────────► Quiz (structured MCQs) ──────────────────────► END
```

- Router: structured output `RouteDecision {intent, reason, search_query}`. No open video → `search_library`.
- Verifier: code, not an LLM. Every `[mm:ss]` must fall inside a retrieved chunk (±2 s). Missing or wrong citations → one retry with feedback, then wrong timestamps are removed.
- Streaming: answer tokens are sent from inside the node with LangGraph's stream writer.

## Key decisions

| Decision | Why | Alternative |
|---|---|---|
| ChromaDB | Python-native, simple, metadata filters, no extra server | pgvector (when moving to Postgres), Qdrant |
| `multilingual-e5-small` embeddings | Free, runs on CPU (8 GB Mac), Hindi support | OpenAI `text-embedding-3-small` |
| Provider layer for LLMs | Switch OpenAI ↔ Claude without touching agents; fallback | Calling SDKs directly |
| YouTube captions first | Fast, free, no audio download | Whisper on audio (uploads only) |
| FastAPI `BackgroundTasks` first | Simple, enough for one server | Celery + Redis later |
| Verifier in code, not LLM | Cheap, exact, testable | LLM-as-judge |
| 300-word chunks, 50 overlap | Best Hit@1 and MRR in the eval | 150 (more chunks), 600 (topics mix) |
| LangGraph | Clear graph of agents, conditional routing, retries | Single prompt, CrewAI |

_Update this file whenever a design decision changes._
