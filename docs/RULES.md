# Project Rules

Rules I follow in this repo so the code stays clean and consistent.

## General

1. **Understand before committing.** Never commit code I can't explain line by line.
2. **Small steps.** One feature or fix per commit, one feature per branch.
3. **No secrets in git.** API keys only in `.env`. `.env` is in `.gitignore`. Only `.env.example` is committed.
4. **Every day ends with a commit** and an entry in `TRACKER.md`.
5. **Update `UPDATES.md`** whenever a user-visible feature lands.

## Python (backend)

- Python 3.11+, type hints on every function.
- Format and lint with `ruff` before committing.
- Names: `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_CASE` for constants.
- Routers only handle HTTP (parse request, return response). Logic lives in modules (`ingestion/`, `vectorstore/`, `agents/`, `llm/`).
- Agents and routes never import `openai` or `anthropic` directly — always `from app.llm.factory import get_llm`.
- Config only through `app/config.py` (`settings.X`), never `os.getenv` scattered around.
- Pydantic models for every request and response body.
- Raise `HTTPException` with a clear message; log the real error.
- Tests in `backend/tests/`, file names `test_*.py`. New logic → at least one test.

## React (frontend)

- TypeScript everywhere, no `any` unless there's a comment explaining why.
- Function components + hooks only.
- One component per file, `PascalCase.tsx`.
- All API calls go through `src/api/client.ts`.
- Styling with Tailwind utility classes; no inline style objects except for dynamic values.
- Keep pages thin; reusable UI goes to `src/components/`.

## AI / RAG

- Same embedding model for indexing and querying. Never mix models in one Chroma collection.
- Every answer must cite `[mm:ss]` timestamps; if the answer isn't in the context, say so.
- Temperature ≤ 0.3 for RAG answers.
- Log provider, model, tokens and latency for every LLM call.
- Change one thing at a time (chunk size, k, model) and re-run the eval.

## Git

- Branches: `feat/...`, `fix/...`, `docs/...`, `refactor/...`, `test/...`, `chore/...`
- Commit format (Conventional Commits):

| Prefix | Use for | Example |
|---|---|---|
| `feat:` | new feature | `feat: add chroma search endpoint` |
| `fix:` | bug fix | `fix: handle youtube shorts urls` |
| `docs:` | docs only | `docs: add architecture diagram` |
| `test:` | tests | `test: chunker overlap cases` |
| `refactor:` | no behaviour change | `refactor: move llm calls to provider layer` |
| `chore:` | setup, deps, config | `chore: add ruff config` |

- Write messages in present tense, lowercase, under ~60 characters.
- Merge to `main` through a PR, even when working alone (good habit, nice history).
