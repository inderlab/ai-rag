# Updates (Changelog)

All notable changes to VidMind AI. Newest first.
Format: `## [version] - YYYY-MM-DD` with **Added / Changed / Fixed / Removed**.

---

## [1.1.1] - 2026-11-24

### Added
- `docs/INTERVIEW_PREP.md`: final self-test with the 9 topics, project numbers and a 30 second pitch
- `docs/LAUNCH.md`: 2 minute demo script, deploy steps, LinkedIn post, resume bullets

### Fixed
- Search results for uploaded videos linked to a fake YouTube URL; they now link to `/videos/{id}?t=` in the app

---

## [1.1.0] - 2026-11-23

### Added
- Accounts: `/api/auth/register`, `/login`, `/me`, `/config` (JWT + bcrypt), optional `AUTH_REQUIRED`
- Video and audio upload: `/api/videos/upload`, FFmpeg + faster-whisper transcription, `/api/videos/{id}/media` with Range support
- Private uploads per user; YouTube videos stay shared; vector search is scoped per user
- Frontend: login / register page, upload box with progress, HTML5 player for uploads, user menu

### Fixed
- Anonymous requests could see private uploads in lists and library search

---

## [1.0.0] - 2026-11-22

### Added
- ChromaDB vector store, indexing step (`indexing` status), `/api/search`, reindex
- RAG chat with `[mm:ss]` citations, NOT_FOUND handling, with/without RAG compare
- Structured outputs in both providers; auto insights (title, summary, chapters, tags, key points)
- LangGraph multi-agent chat: router with query rewriting, retriever, library search, summarizer, quiz, citation verifier with retry
- `/api/chat/stream` (SSE with steps and tokens)
- React library and video pages: status polling, streaming chat, clickable timestamps, chapters, quiz, model dropdown
- MCP server with 5 tools
- Eval (28 questions, hit rate, MRR, citation accuracy) and n8n webhook + 2 workflows
- Docker Compose (backend, nginx frontend, optional n8n), `.env.example`, CI docker build

### Changed
- `/api/chat` now runs the agent graph; plain RAG moved to `/api/chat/rag`

### Fixed
- Indexing failed when two videos were added at once (init lock on store and model)
- YouTube errors now show the real cause line

## [0.2.0] - 2026-11-17

### Added
- LLM chat, streaming, provider compare, prompt styles (days 1-2)
- Video ingestion with SQLite and background jobs (day 3)
- Multilingual embeddings and semantic search (day 4), segment-aware chunking (day 5)

---

## [0.1.0] - 2026-11-10

### Added
- Project structure: `backend/`, `frontend/`, `docs/`, `learn/`, `mcp_server/`, `eval/`, `n8n/`
- FastAPI app with `/api/health`
- Settings loaded from `.env`
- LLM provider layer: OpenAI and Claude behind one interface, `/api/llm/test` endpoint
- YouTube URL parsing (watch, youtu.be, shorts, embed) and `/api/transcript` preview endpoint
- React + Vite + TypeScript + Tailwind frontend with health check and transcript preview page
- Docs: README, ARCHITECTURE, RULES, COMMANDS, TRACKER, UPDATES, NOTES
- GitHub Actions CI (backend tests + frontend build)

---

<!-- Template for next entries:

## [0.2.0] - YYYY-MM-DD

### Added
-

### Changed
-

### Fixed
-

-->
