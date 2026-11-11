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
   n8n ────────────► │    FastAPI backend    │ ◄───── │  MCP server   │ ◄── Claude Desktop
                     │ auth · videos · chat  │        └───────────────┘
                     └──┬─────────────┬──────┘
          background    │             │  LangGraph agents
          indexing      ▼             ▼
               ┌──────────────┐  ┌──────────────┐  ┌────────────────┐
               │  Ingestion   │─►│   ChromaDB   │  │ SQLite/Postgres│
               │ captions /   │  │ chunks +     │  │ users, videos, │
               │ Whisper,     │  │ embeddings + │  │ chats          │
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
| `app/ingestion/` | YouTube captions, Whisper, chunking, embeddings, indexing pipeline |
| `app/vectorstore/` | ChromaDB wrapper (add, search, delete) |
| `app/agents/` | LangGraph state, agents and graph |
| `app/db.py`, `app/models.py` | SQLAlchemy engine and tables |

## Data model

| Table | Columns |
|---|---|
| `users` | id, name, email, password_hash, role, created_at |
| `videos` | id, user_id, source (`UPLOAD`/`YOUTUBE`), youtube_id, file_path, status, error, title, summary, chapters (JSON), tags (JSON), created_at |
| `chats` | id, user_id, video_id, created_at |
| `messages` | id, chat_id, role, content, provider, model, tokens, latency_ms, created_at |

**ChromaDB collection `video_chunks`:** `id = {video_id}_{index}`, document = chunk text, metadata = `{video_id, user_id, start, end}`.

**Video status:** `QUEUED → FETCHING_TRANSCRIPT → INDEXING → GENERATING_INSIGHTS → READY` (or `FAILED`)

## Multi-agent graph

```
question → Router ─┬─ qa ──────────► Retriever → Answer → Verifier ─┬─ ok ──► END
                   │                                  ▲              └─ retry ┘ (once)
                   ├─ summary ─────► Summarizer ─────────────────────────────► END
                   ├─ search_library► Library Search ────────────────────────► END
                   └─ quiz ────────► Quiz/Notes ─────────────────────────────► END
```

## Key decisions

| Decision | Why | Alternative |
|---|---|---|
| ChromaDB | Python-native, simple, metadata filters, no extra server | pgvector (when moving to Postgres), Qdrant |
| `multilingual-e5-small` embeddings | Free, runs on CPU (8 GB Mac), Hindi support | OpenAI `text-embedding-3-small` |
| Provider layer for LLMs | Switch OpenAI ↔ Claude without touching agents; fallback | Calling SDKs directly |
| YouTube captions first | Fast, free, no audio download | Whisper on audio (uploads only) |
| FastAPI `BackgroundTasks` first | Simple for week 1 | Celery + Redis later |
| LangGraph | Clear graph of agents, conditional routing, retries | Single prompt, CrewAI |

_Update this file whenever a design decision changes._
