# Launch kit

Day 14 ke bache hue kaam: demo video, deploy, LinkedIn post, resume. Sab kuch yahan ready hai, bas record, deploy aur post karna hai.

## 1. Demo video (2 minute)

Setup: backend + frontend chalao, ek ready YouTube talk aur ek chhota upload pehle se library mein rakho. Screen recorder: macOS pe `Cmd + Shift + 5`.

| Time | Screen | Bolna hai |
|---|---|---|
| 0:00-0:15 | Library page | "Lambi videos mein ek baat dhoondhna mushkil hai. VidMind se kisi bhi video se chat karo, aur har jawab timestamp ke saath aata hai." |
| 0:15-0:35 | YouTube link paste karo, status `processing → indexing → ready` | "Link do. Background mein captions, chunks, embeddings aur summary bante hain." |
| 0:35-1:00 | Video page, Hinglish sawaal poochho, tokens stream hote dikhao | "Main Hinglish mein poochh raha hoon. Jawab transcript se aata hai, aur steps mein router, retriever, answer aur verifier dikhte hain." |
| 1:00-1:15 | `[mm:ss]` pe click, player wahi pahunchta hai | "Timestamp pe click karo, video seedha us moment pe." |
| 1:15-1:30 | Chapters, quiz mode | "Auto chapters aur summary, aur ek click mein quiz." |
| 1:30-1:45 | Login, file upload, Whisper ke baad chat | "Apni file bhi upload kar sakte ho. Whisper transcript banata hai, aur upload sirf aapko dikhta hai." |
| 1:45-2:00 | Claude Desktop mein MCP tool call, phir README eval table | "MCP server se Claude Desktop bhi meri library search karta hai. 28 sawaalon ke eval pe 82% pehla result sahi aur 93-96% sahi citation." |

Video ko GIF bhi banao README ke liye:

```bash
ffmpeg -i demo.mov -vf "fps=10,scale=960:-1" -t 20 docs/images/demo.gif
```

## 2. Deploy

Sabse aasan: ek chhota Linux VM (2 vCPU, 4 GB RAM; embedding model aur Whisper ko RAM chahiye) jaise Hetzner, DigitalOcean, AWS Lightsail ya Oracle free tier.

```bash
sudo apt update && sudo apt install -y docker.io docker-compose-v2 git
git clone https://github.com/inderlab/ai-rag.git vidmind && cd vidmind
cp backend/.env.example backend/.env
nano backend/.env
docker compose up -d --build
```

`.env` mein production ke liye zaroori:

| Key | Value |
|---|---|
| `ANTHROPIC_API_KEY` | aapki key (sirf server pe, git mein kabhi nahi) |
| `JWT_SECRET` | `openssl rand -hex 32` ka output |
| `AUTH_REQUIRED` | `true` agar public URL hai, warna koi bhi aapki API key kharch kar sakta hai |
| `PUBLIC_APP_URL` | aapka domain, jaise `https://vidmind.example.com` |
| `CORS_ORIGINS` | wahi domain |

HTTPS ke liye VM pe Caddy sabse simple hai (certificate khud leta hai):

```
vidmind.example.com {
    reverse_proxy localhost:8080
}
```

Check: `curl https://vidmind.example.com/api/health` → `{"status":"ok", ...}`.

Free option (sirf demo): Render ya Railway pe backend Docker service + frontend static site. Free tier mein RAM kam hai aur service so jaati hai, isliye pehla sawaal 30-60 s le sakta hai.

## 3. LinkedIn post

Screenshot ya demo GIF ke saath post karo. Pehli line hi sab kuch hai, kyunki "see more" ke baad log kam padhte hain.

```
I built a "chat with any video" app in 14 days, and it answers in Hinglish.

Paste a YouTube link or upload your own recording, ask a question, and every answer comes with a [mm:ss] timestamp. Click it and the player jumps to that moment.

What's under the hood:
- RAG on the transcript with multilingual embeddings (e5-small) and ChromaDB
- A LangGraph multi-agent graph: router, retriever, summarizer, quiz, and a verifier that checks every timestamp and retries once
- Whisper for uploads, JWT login, and private uploads per user
- An MCP server, so Claude Desktop can search my video library
- FastAPI, React, Docker Compose, GitHub Actions

The part I'm proudest of is the eval. I wrote 28 questions with the exact time window that answers each one:
- 300-word chunks beat 150 and 600 (Hit@1 82%)
- Rewriting Hinglish questions took Hit@6 from 96% to 100%
- 93-96% of answers cite the right moment

One thing that didn't work: fusing results from the original and the rewritten query gave no gain, so I kept the simpler version.

Code: github.com/inderlab/ai-rag

If you're hiring for GenAI or backend roles, I'd love to talk.

#GenAI #RAG #LangGraph #Python #BuildInPublic
```

## 4. Resume

**VidMind AI** · Python, FastAPI, LangGraph, ChromaDB, React, Docker · [github.com/inderlab/ai-rag](https://github.com/inderlab/ai-rag)

- Built a multilingual "chat with video" RAG app with clickable `[mm:ss]` citations for YouTube links and uploaded files (FFmpeg + Whisper)
- Designed a LangGraph multi-agent graph (router, retriever, summarizer, quiz) with a citation verifier and retry loop; answers cite the right moment 93-96% of the time
- Created a 28-question retrieval eval (Hit@k, MRR); tuned chunk size (Hit@1 82%) and added query rewriting for Hinglish (Hit@6 96% → 100%)
- Added a provider layer for OpenAI and Claude with structured outputs, SSE token streaming, JWT auth with per-user private data, and an MCP server for Claude Desktop
- Shipped with Docker Compose, nginx, and GitHub Actions CI (ruff, 145 pytest tests, frontend and Docker builds)

## Checklist

- [ ] Demo video record kiya (2 min) aur GIF README mein daala
- [ ] Claude Desktop MCP wala hissa record kiya
- [ ] VM pe deploy kiya, `AUTH_REQUIRED=true` aur strong `JWT_SECRET` ke saath
- [ ] README mein live link daala
- [ ] LinkedIn post kiya
- [ ] Resume update kiya
- [ ] `docs/INTERVIEW_PREP.md` ke 9 topics bol ke practice kiye
