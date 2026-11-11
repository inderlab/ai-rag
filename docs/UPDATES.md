# Updates (Changelog)

All notable changes to VidMind AI. Newest first.
Format: `## [version] - YYYY-MM-DD` with **Added / Changed / Fixed / Removed**.

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
