# Progress Tracker

Start date: 2026-11-10 · Target: 14 days
Legend: ✅ done · 🔄 in progress · ⬜ not started · ⏸️ blocked

## Daily progress

| Day | Date | Topic (learn) | Build (project) | Status | Commits | Hours |
|---|---|---|---|---|---|---|
| 0 | 2026-11-10 | Setup | Folder structure, FastAPI + Vite skeleton, docs | ✅ | 1 | |
| 1 | 2026-11-11 | LLM basics + API | Health, config, LLM test call, chat, temperature compare | ✅ | 1 | |
| 2 | 2026-11-12 | Prompting + providers | Streaming (SSE), provider compare, prompt styles | ✅ | 1 | |
| 3 | 2026-11-13 | Transcript + Whisper | YouTube captions, Video + Segment tables, background job, `/api/videos` | ✅ | 1 | |
| 4 | 2026-11-16 | Embeddings | `embedder.py` (multilingual-e5-small, 384 dim), `/api/embeddings`, similarity, semantic search on a video | ✅ | 1 | |
| 5 | 2026-11-17 | Chunking | `chunker.py` (segment-aware, overlap, timestamps), `/api/chunks/preview`, `/api/videos/{id}/chunks`, compare sizes, chunk search | ✅ | 1 | |
| 6 | 2026-11-22 | Vector DB (ChromaDB) | `chroma_store.py`, indexing pipeline (`indexing` status), `/api/search`, `/api/vectorstore/info`, reindex | ✅ | 1 | |
| 7 | 2026-11-22 | RAG | `/api/chat` with `[mm:ss]` citations, `/api/chat/compare` (with vs without RAG) | ✅ | 1 | |
| 8 | 2026-11-22 | Structured outputs + tools | `structured()` in both providers, VideoInsights (title, summary, chapters, tags, key points), `/api/videos/{id}/insights`, tool-calling practice | ✅ | 1 | |
| 9 | 2026-11-22 | Agents + LangGraph | `agents/state.py`, `agents/router.py`, `agents/graph.py` (router → retriever → answer), `/api/agent/chat` with trace | ✅ | 1 | |
| 10 | 2026-11-22 | Multi-agent + verifier | summarizer, quiz, library search, verifier retry loop, query rewrite, `/api/chat` on the graph, `/api/chat/stream` (SSE) | ✅ | 1 | |
| 11 | 2026-11-22 | React + Vite | Library (status, search, library chat), video page (player, chapters, streaming chat, quiz), model dropdown | ✅ | 1 | |
| 12 | 2026-11-22 | MCP | `mcp_server/server.py` (5 tools over the API), stdio + HTTP, tests, Claude Desktop config | ✅ | 1 | |
| 13 | 2026-11-22 | Eval + n8n | `eval/run_eval.py` + 28 questions, n8n webhook + 2 workflows | ✅ | 1 | |
| 14 | 2026-11-22 | Docker + CI + launch | Dockerfiles, compose, CI (lint, tests, build, docker build), README, changelog | 🔄 | 1 | |

## Daily log

<!-- Copy this block every day -->

### Day 0 — 2026-11-10
- **Learned:**
- **Built:** project skeleton, docs, FastAPI + Vite setup
- **Problems / how I solved them:**
- **Tomorrow:** Day 1 — LLM basics, run `learn/day01_llm_basics.py`, test `/api/llm/test`

### Day 1 — 2026-11-11
- **Learned:** tokens, context window, temperature, roles, stateless API, hallucination
- **Built:** `/api/llm/providers`, `/api/llm/test` (token usage), `/api/llm/chat` (history), `/api/llm/temperature`
- **Problems / how I solved them:** first push was blocked by permissions, pushed after approval
- **Tomorrow:** Day 2 — prompting + streaming

### Day 2 — 2026-11-12
- **Learned:** prompt structure, zero-shot vs few-shot, adapter pattern, SSE streaming
- **Built:** `/api/llm/stream`, `/api/llm/compare`, `/api/llm/prompt-styles`, `app/llm/prompts.py`
- **Problems / how I solved them:** new Anthropic SDK (API `2026-10-21`) rejects `temperature`; Claude provider now uses `output_config.effort` instead, OpenAI still uses temperature
- **Tomorrow:** Day 3 — YouTube transcript + background job

### Day 3 — 2026-11-13
- **Learned:** ingestion, captions (human vs auto), timestamps, background jobs, status machine, 202/409
- **Built:** SQLite + SQLAlchemy (`videos`, `transcript_segments`), background ingest job, `/api/videos` (add, list, get, transcript with search, retry, delete)
- **Problems / how I solved them:** caption lines had line breaks inside, flattened to one line; jobs stuck after restart are marked failed on startup
- **Tomorrow:** Day 4 — embeddings

### Day 4 — 2026-11-16
- **Learned:** embeddings, cosine similarity, e5 `query:` / `passage:` prefixes, multilingual space, same-model rule
- **Built:** `app/ingestion/embedder.py`, `/api/embeddings/info`, `/api/embeddings`, `/api/embeddings/similarity`, `/api/videos/{id}/semantic-search` (in-memory, cached)
- **Problems / how I solved them:** model download ~470 MB and first load ~35 s, so it loads lazily on first use; tests use a fake model so they run without downloading
- **Result:** Hinglish query matched English + Hindi DB sentences; on a real video first search 606 ms, cached 18 ms
- **Tomorrow:** Day 5 — chunking (segments are too short for good search)

### Day 5 — 2026-11-17
- **Learned:** chunk size trade-off, overlap, metadata (start/end), segment-aware vs fixed word chunking
- **Built:** `app/ingestion/chunker.py`, `app/services/transcripts.py`, `/api/chunks/preview`, `/api/videos/{id}/chunks`, `/api/videos/{id}/chunks/compare`, `unit: chunk|segment` in semantic search (chunk is default)
- **Problems / how I solved them:** YouTube gave a temporary 502 and the saved error only showed "most likely caused by:", so `friendly_error` now shows the real cause line; retry worked
- **Result:** 487-word video → 6 / 2 / 1 chunks for 100 / 300 / 800 words; Hinglish query now finds the right chorus chunk; embedding 6 chunks 395 ms vs 61 segments 920 ms
- **Tomorrow:** Day 6 — ChromaDB, save chunk vectors once instead of embedding on every search

### Day 6 — 2026-11-22
- **Learned:** vector DB vs SQL, HNSW, collection / ids / documents / metadatas / where, distance = 1 - cosine, Chroma vs pgvector
- **Built:** `app/vectorstore/chroma_store.py` (`add_chunks`, `search`, `delete_video`, `count`, model check), indexing after transcript, `GET /api/search?q=&video_id=&k=`, `GET /api/vectorstore/info`, `POST /api/videos/{id}/reindex`, `chunk_count` column with auto-migration
- **Problems / how I solved them:** two videos added together made two threads open Chroma at once and indexing failed; added an init lock for the store and the model
- **Result:** 2 real videos, 51 chunks; library search finds the right minutes in a 1 hour talk; vectors survive restart
- **Tomorrow:** Day 7 — RAG chat with `[mm:ss]` citations

### Day 7 — 2026-11-22
- **Learned:** retrieve → augment → generate, grounding rules, NOT_FOUND, citations, k trade-off, RAG vs fine-tuning
- **Built:** `app/services/rag.py`, RAG prompts in `app/llm/prompts.py`, `POST /api/chat` (video or whole library, history, provider), `POST /api/chat/compare`, `learn/day07_rag.py`
- **Problems / how I solved them:** one compare call returned 502 without a reason in the log; chat routes now log the real exception
- **Result:** 10 questions on a real 1 hour talk: 9 answered with correct timestamps, out-of-video question → NOT_FOUND
- **Tomorrow:** Day 8 — structured outputs (title, summary, chapters, tags) and tool calling

### Day 8 — 2026-11-22
- **Learned:** structured outputs (Pydantic schema), tool calling loop, `tool_result`, parallel tool calls, strict tools, forced tool_choice not allowed on newer Claude models
- **Built:** `LLMProvider.structured()` (Claude `messages.parse`, OpenAI `chat.completions.parse`), `app/services/insights.py` (30 s markers, map-reduce for long videos, cleanup), `video_insights` table, auto insights after indexing, `GET/POST /api/videos/{id}/insights`, `learn/day08_tools.py`
- **Problems / how I solved them:** chapters only matched chunk starts (2 chapters for a 3 min song); now the transcript has a marker every ~30 s
- **Result:** 14 sensible chapters for the 1 hour talk, 7 for the song; tool demo shows 1 call, 2 parallel calls, and no call when not needed
- **Tomorrow:** Day 9 — LangGraph basics: router + retriever + answer graph

### Day 9 — 2026-11-22
- **Learned:** agent, LangGraph state / nodes / edges / conditional edges, reducers (`operator.add`)
- **Built:** `AgentState`, router agent (structured `RouteDecision`), graph router → retriever → answer, `POST /api/agent/chat` (intent, reason, steps, tokens), `learn/day09_graph.py`
- **Problems / how I solved them:** a router answer of `qa` with no open video can't retrieve one video, so it is turned into `search_library`
- **Result:** 4/4 live questions routed correctly (qa, summary, quiz, search_library)
- **Tomorrow:** Day 10 — summarizer, quiz, library search, verifier loop, SSE streaming

### Day 10 — 2026-11-22
- **Learned:** one job per agent, verifier with retry, query rewriting, streaming tokens out of a LangGraph node
- **Built:** `agents/specialists.py` (summarizer, quiz), `agents/verifier.py`, full graph in `agents/graph.py`, router `search_query`, `POST /api/chat` (agent), `POST /api/chat/stream` (SSE: start/step/token/retry/done/error), `POST /api/chat/rag` (plain RAG), `learn/day10_agents.py`
- **Problems / how I solved them:** single-video answers added an extra "Video: ..." line, so titles and the library note are only sent for library search; stripped citations left double spaces, fixed
- **Result:** verifier catches a fake `[12:00]`; warm stream first token 4.2 s, done 5.2 s; summary / quiz / library paths work live
- **Tomorrow:** Day 11 — React frontend

### Day 11 — 2026-11-22
- **Learned:** SSE over `fetch` for POST, YouTube IFrame API `seekTo`, polling only while busy, forwardRef
- **Built:** `api/client.ts` (types + `streamChat`), `LibraryPage`, `VideoPage`, `ChatPanel`, `RichText` (clickable `[mm:ss]`), `QuizView`, `InsightsPanel`, `YouTubePlayer`, `StatusBadge`, `ProviderSelect`
- **Problems / how I solved them:** `EventSource` can't POST, so the stream is read with `fetch` + reader; login and upload are not built yet because the backend has no auth or Whisper path
- **Result:** `npm run build` clean; screenshots of both pages look right; frontend stream parser tested against the live server
- **Tomorrow:** Day 12 — MCP server

### Day 12 — 2026-11-22
- **Learned:** MCP vs function calling, tools / resources / prompts, stdio vs streamable HTTP, tool annotations, auth options
- **Built:** `mcp_server/server.py` (`list_videos`, `search_videos`, `ask_video`, `get_video_summary`, `ingest_youtube`), `mcp_server/README.md` with Claude Desktop config, `tests/test_mcp_server.py`, `learn/day12_mcp_add.py`
- **Problems / how I solved them:** mcp 2.x renamed FastMCP to MCPServer; plain exceptions hid the real error, now `ToolError`; tool descriptions moved from docstrings to `description=`
- **Result:** server works as a real stdio subprocess against the live API; 8 tests pass
- **Still to do by me:** add it to Claude Desktop and screen-record the demo
- **Tomorrow:** Day 13 — eval + n8n

### Day 13 — 2026-11-22
- **Learned:** hit rate @k, MRR, ground-truth windows, change one thing at a time, LLM run-to-run variance, n8n webhook / schedule / RSS / HTTP nodes
- **Built:** `eval/questions.json` (28 questions with time windows), `eval/run_eval.py` (chunk sizes, k, language split, query rewrite + RRF, answer citation check), `app/services/hooks.py` (`N8N_WEBHOOK_URL`, video.ready / video.failed), `n8n/video_ready_notification.json`, `n8n/youtube_channel_watcher.json`
- **Problems / how I solved them:** query rewriting looked worse at Hit@1, but Hit@6 (what RAG uses) went to 100%; fusion of both queries did not help, so the app keeps rewriting. Webhook failures are only logged so ingest never breaks
- **Result:** 300 words is best (Hit@1 82%, MRR 0.89); answers cite the right moment 93-96%; webhook tested live with a local receiver
- **Still to do by me:** import the two workflows into n8n and connect Telegram
- **Tomorrow:** Day 14 — Docker, CI, README, launch

### Day 14 — 2026-11-22
- **Learned:** multi-stage Docker builds, nginx as SPA + API proxy (buffering off for SSE), compose volumes and profiles, CI caching
- **Built:** `backend/Dockerfile` (CPU torch, non-root, healthcheck), `frontend/Dockerfile` + `nginx.conf`, `docker-compose.yml` (backend, frontend, optional n8n), `backend/.env.example`, CI with ruff format check + docker build, new README with screenshots and eval table, ARCHITECTURE / COMMANDS / UPDATES updated
- **Problems / how I solved them:** Docker is not installed on this laptop, so the images are built by the new CI `docker` job
- **Still to do by me:** demo video (2 min), deploy, LinkedIn post, add the project to my resume, run the OpenAI column of the eval when I have a key

---

## Eval results (fill on Day 13)

28 questions on the 1 hour LLM talk, full tables in `eval/README.md`.

| Run | Chunk size | k | Embedding | Provider | Hit rate @k | Avg latency |
|---|---|---|---|---|---|---|
| 1 | 150 / overlap 25 | 1 / 3 / 6 | multilingual-e5-small | - | 79% / 93% / 100%, MRR 0.86 | index 1.2 s |
| 2 | **300 / overlap 50** | 1 / 3 / 6 | multilingual-e5-small | - | **82% / 96% / 96%, MRR 0.89** | index 0.7 s |
| 3 | 600 / overlap 100 | 1 / 3 / 6 | multilingual-e5-small | - | 68% / 86% / 93%, MRR 0.77 | index 0.5 s |
| 4 | 300 + query rewrite | 6 | multilingual-e5-small | claude (router) | 100% (Hinglish 83% → 100%) | +1-2 s router |
| 5 | 300, answers | 6 | multilingual-e5-small | claude-haiku-5-5 | right citation 93-96% | 2.3 s / answer |

## Bugs / TODO

- [ ]
