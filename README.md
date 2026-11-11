# VidMind AI

Chat with any video. Upload a file or paste a YouTube link, then ask questions and get answers with clickable timestamps.

> Status: **in development** (Day 1 of 14). See [docs/TRACKER.md](docs/TRACKER.md).

## Features (planned)

- YouTube URL or video upload
- Timestamped transcript (captions or Whisper)
- RAG chat with `[mm:ss]` citations that seek the player
- Auto title, summary, chapters, tags and quiz
- Search across all your videos
- Multi-agent pipeline (router, retriever, answer, verifier, summarizer, quiz)
- Works with OpenAI or Claude (switch in `.env`)
- MCP server for Claude Desktop / Cursor
- n8n automations
- Hindi / Hinglish support

## Tech stack

**Backend:** Python, FastAPI, ChromaDB, LangGraph
**Frontend:** React, Vite, TypeScript, Tailwind CSS
**AI:** OpenAI / Anthropic Claude, sentence-transformers, Whisper
**Other:** MCP, n8n, Docker, GitHub Actions

## Project structure

```
vidmind-ai/
├── backend/        FastAPI app (API, ingestion, vector store, agents, LLM providers)
├── frontend/       React + Vite app
├── mcp_server/     MCP server (Day 12)
├── eval/           Retrieval evaluation (Day 13)
├── n8n/            Exported n8n workflows (Day 13)
├── learn/          Daily practice scripts
└── docs/           Architecture, rules, commands, tracker, changelog
```

## Quick start

```bash
# backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # add your API keys
uvicorn app.main:app --reload

# frontend (new terminal)
cd frontend
npm install
npm run dev
```

- API: http://localhost:8000 (Swagger docs at `/docs`)
- Web: http://localhost:5173

More commands in [docs/COMMANDS.md](docs/COMMANDS.md).

## Docs

| File | What's inside |
|---|---|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design and data flow |
| [RULES.md](docs/RULES.md) | Coding conventions and git rules |
| [COMMANDS.md](docs/COMMANDS.md) | Every command you need |
| [TRACKER.md](docs/TRACKER.md) | Day-by-day progress |
| [UPDATES.md](docs/UPDATES.md) | Changelog |
| [PROJECT_PLAN.md](docs/PROJECT_PLAN.md) | Full build plan with code |
| [LEARNING_PLAN.md](docs/LEARNING_PLAN.md) | 14-day learning plan |

## Author

**Inderjeet Kumar** · [LinkedIn](https://linkedin.com/in/inderjeet-kmr) · [GitHub](https://github.com/inderlab)
