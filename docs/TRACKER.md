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
| 5 | | Chunking | `chunker.py` + tests | ⬜ | | |
| 6 | | Vector DB (ChromaDB) | `chroma_store.py`, indexing pipeline, `/api/search` | ⬜ | | |
| 7 | | RAG | `/api/chat` with `[mm:ss]` citations | ⬜ | | |
| 8 | | Structured outputs + tools | Title, summary, chapters, tags | ⬜ | | |
| 9 | | Agents + LangGraph | Router + retriever + answer graph | ⬜ | | |
| 10 | | Multi-agent + verifier | All agents, verifier loop, SSE | ⬜ | | |
| 11 | | React + Vite | Library, video page, chat, quiz, model dropdown | ⬜ | | |
| 12 | | MCP | MCP server + Claude Desktop demo | ⬜ | | |
| 13 | | Eval + n8n | Eval script, n8n workflows | ⬜ | | |
| 14 | | Docker + CI + launch | Compose, README, demo video, deploy | ⬜ | | |

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

---

## Eval results (fill on Day 13)

| Run | Chunk size | k | Embedding | Provider | Hit rate @k | Avg latency |
|---|---|---|---|---|---|---|
| 1 | | | | | | |

## Bugs / TODO

- [ ]
