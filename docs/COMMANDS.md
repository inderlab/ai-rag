# Commands

## First-time setup

```bash
# Python 3.11+ and Node 20+ needed
python3 --version
node --version

# git identity (shows on GitHub commits)
git config --global user.name  "Inderjeet Kumar"
git config --global user.email "inder74et@gmail.com"
```

## Backend (FastAPI)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                 # then fill in keys

uvicorn app.main:app --reload        # run dev server on :8000
pytest -q                            # run tests
ruff check .                         # lint
ruff format .                        # format
deactivate                           # leave venv
```

Useful URLs:
- http://localhost:8000/docs — Swagger UI (try endpoints here)
- http://localhost:8000/api/health
- http://localhost:8000/api/transcript?url=https://youtu.be/VIDEO_ID

Add a package:

```bash
pip install <package> && pip freeze | grep -i <package>   # then add that line to requirements.txt
```

## Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev          # dev server on :5173
npm run build        # production build to dist/
npm run preview      # preview the build
npm run lint         # type check
```

## Learning scripts

```bash
cd learn
source ../backend/.venv/bin/activate
python day01_llm_basics.py
```

## Git workflow

```bash
git checkout -b feat/<feature-name>      # new branch per feature
git add -p                               # review each change before staging
git commit -m "feat: add youtube transcript endpoint"
git push -u origin feat/<feature-name>
# open PR on GitHub → merge into main

git log --oneline --graph -15            # see history
git log --format='%an <%ae>' | head      # check author name
```

First push of a new repo:

```bash
git init
git add .
git commit -m "chore: project setup"
git branch -M main
git remote add origin https://github.com/inderlab/vidmind-ai.git
git push -u origin main
```

## Later (added as the project grows)

```bash
python -m mcp_server.server              # Day 12: run MCP server
python eval/run_eval.py --provider claude   # Day 13: retrieval eval
npx n8n                                  # Day 13: run n8n locally
docker compose up --build                # Day 14: everything in Docker
```
