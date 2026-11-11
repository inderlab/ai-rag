# Feature Timeline — har din user ko kya naya milega

Ye file user ki nazar se hai: **har din ke end mein app mein kya naya chal raha hoga**, aur user (Rahul) usse kaise use karega.
Code ki details ke liye: [DAILY_BUILD_PLAN.md](DAILY_BUILD_PLAN.md).

## Ek nazar mein

| Day | Feature (user ko kya milta hai) | Kahan dikhega | Core tech |
|---|---|---|---|
| 0 ✅ | App khulta hai, API health, YouTube transcript preview, LLM test | Web + Swagger | FastAPI, React, Vite |
| 1 | ChatGPT vs Claude side-by-side compare | Swagger | LLM providers |
| 2 | Jawab word-by-word stream hota hai | Swagger / browser | Prompting, SSE |
| 3 | Video library: link add karo, status dekho, transcript save | Swagger | SQLite, background jobs |
| 4 | (Andar) text ka matlab samajhna | Script | **Embeddings** |
| 5 | (Andar) transcript ke smart tukde | Tests | **Chunking** |
| 6 | **Video ke andar matlab se search** | Swagger `/api/search` | **ChromaDB (vector DB)** |
| 7 | **Video se sawaal poochho, timestamp wala jawab** ⭐ | Swagger `/api/chat` | **RAG** |
| 8 | Auto title, summary, chapters, tags | Swagger | Structured outputs |
| 9 | App sawaal ka type samajhta hai (sawaal / summary / quiz) | Swagger | LangGraph agents |
| 10 | Quiz, poori library search, galat timestamp ki checking | Swagger | Multi-agent + verifier |
| 11 | **Poora web app**: library, player, chat, transcript tab, quiz, search ⭐ | Browser | React + Vite |
| 12 | Claude Desktop / Cursor se apni videos search karo | Claude Desktop | **MCP** |
| 13 | "Video ready" notification, channel se auto-add, quality score | Email/Telegram, n8n | n8n, eval |
| 14 | Live link, ek command se setup, demo video ⭐ | Internet | Docker, CI |

⭐ = milestone (LinkedIn post ka din)

---

## Day 0 — Starter (✅ ho gaya)

**Feature:** app khulta hai, API zinda hai, kisi bhi YouTube link ka transcript timestamps ke saath dikhta hai, aur LLM se test sawaal pooch sakte ho.

**User flow:**
1. Rahul `localhost:5173` kholta hai → header mein "● API ok · openai" dikhta hai.
2. **Transcript** page → YouTube link paste → "Get transcript".
3. Video embed + neeche `04:12  ab hum application.properties kholenge…` jaisi lines.
4. **LLM test** page → "RAG kya hai?" → dropdown se Claude choose → jawab + "answered by claude · 820 ms".

**Peeche:** `GET /api/transcript` → `extract_video_id` → captions → `fmt_ts`. `POST /api/llm/test` → `get_llm()` → provider.

---

## Day 1 — ChatGPT vs Claude compare

**Feature:** ek sawaal, dono models ke jawab side-by-side, time ke saath.

**User flow:**
1. Rahul Swagger (`/docs`) mein `POST /api/llm/compare` kholta hai.
2. Prompt: "Spring Boot kya hai, 2 line mein".
3. Response mein do jawab: OpenAI (1.2 s) aur Claude (0.9 s).

**Peeche:** dono providers ek ke baad ek call; jis ki key nahi, wo skip.
**Kyun:** baad mein eval mein dono ko compare karna hai; abhi se aadat.

---

## Day 2 — Streaming jawab

**Feature:** jawab ChatGPT ki tarah dheere-dheere type hota hua aata hai.

**User flow:**
1. Browser mein `localhost:8000/api/llm/stream?prompt=RAG samjhao` kholo.
2. Text ek saath nahi, shabd-shabd aata dikhta hai.

**Peeche:** `StreamingResponse` + SSE (`data: ...`). Prompt templates `prompts.py` mein.
**Kyun:** lambe jawab mein user ko intezaar na lage; Day 10–11 ke chat mein yahi lagega.

---

## Day 3 — Video library

**Feature:** video add karo, wo save hota hai, aur background mein transcript aata hai.

**User flow:**
1. `POST /api/videos` → `{"youtube_url": "https://youtu.be/..."}`.
2. Turant jawab: `status: QUEUED`.
3. 3 sec baad `GET /api/videos` → `status: READY`, transcript ke saath.
4. Galat link → "Not a valid YouTube URL". Captions na hon → `FAILED` + wajah.

**Peeche:** SQLite `videos` table, `BackgroundTasks`, status machine.
**Kyun:** baaki sab features isi video record par bante hain.

---

## Day 4 — Embeddings (andar ka kaam)

**Feature:** user ko abhi kuch naya nahi dikhta — app ab text ka **matlab** samajh sakta hai.

**Developer demo:**
- `python learn/day04_embeddings.py` → "database kaise connect karein" ke saath
  `datasource URL set karo = 0.86`, `डेटाबेस कनेक्शन = 0.81`, `mausam achha hai = 0.12`.

**Kyun:** Day 6 search aur Day 7 RAG isi par chalenge. Hindi aur English ek saath samajh aati hai.

---

## Day 5 — Chunking (andar ka kaam)

**Feature:** user ko abhi kuch naya nahi dikhta — transcript ab ~300 shabd ke tukdon mein, har tukde ka start/end time ke saath.

**Developer demo:** 45 min video → ~40 chunks; `Chunk 7: [04:12–05:01]`. Saare tests pass.

**Kyun:** chhote, matlab-bhare tukde = behtar search. Timestamps yahi se jawab tak pahunchenge.

---

## Day 6 — Matlab se search ⭐ (Vector DB)

**Feature:** video ke andar **words nahi, matlab** se search.

**User flow:**
1. Video add karo → status `INDEXING` → `READY`.
2. `GET /api/search?q=database kaise connect karein&video_id=...`
3. Result: `[04:12] application.properties, datasource URL…` (score 0.89), `[18:40] mysql dependency…`.
4. Video mein "connect" shabd nahi tha, phir bhi sahi jagah mili.

**Peeche:** chunks → embeddings → **ChromaDB** (likhna). Query → embedding → ChromaDB (padhna).
**Kyun:** Day 7 RAG ka "R" (Retrieve) yahi hai.

---

## Day 7 — Video se sawaal-jawab ⭐⭐ (RAG)

**Feature:** video se kuch bhi poochho, jawab **isi video se**, `[mm:ss]` timestamps ke saath. Jo video mein nahi, uske liye "This is not covered in the video."

**User flow:**
1. `POST /api/chat` → `{"video_id": "...", "question": "Isme database kaise connect kiya?"}`
2. Jawab: "pom.xml mein MySQL dependency add ki [18:40], phir `spring.datasource.url` set kiya [04:12]."
3. "Isme React bhi hai?" → "This is not covered in the video."

**Peeche:** search (top 6 chunks) → prompt mein chunks → LLM → citations nikaalna.
**Kyun:** ye project ka **dil** hai. Week 1 complete → GitHub push + LinkedIn post.

---

## Day 8 — Auto summary, chapters, tags

**Feature:** video READY hote hi title, 3–4 line summary, chapters (time ke saath) aur tags.

**User flow:**
1. Video add → status `GENERATING_INSIGHTS` → `READY`.
2. `GET /api/videos/{id}` → `chapters: [{00:00 Intro}, {04:10 Database setup}, {18:30 Dependencies}]`, `tags: ["spring boot", "jpa", "mysql"]`.

**Peeche:** structured outputs (Pydantic schema), OpenAI `parse` / Claude forced tool.
**Kyun:** video page par chapters list aur library cards par summary dikhegi.

---

## Day 9 — Smart routing (agents)

**Feature:** app samajhta hai user kya chahta hai.

**User flow:**
- "Isme JPA kaise use kiya?" → **qa** → RAG jawab
- "Is video ka summary do" → **summary**
- "Quiz banao" → **quiz** (Day 10 mein poora)

**Peeche:** LangGraph: Router agent → sahi raasta.
**Kyun:** ek chat box se kai kaam; har kaam ka alag specialist.

---

## Day 10 — Quiz, library search, verifier

**Feature:**
- **Quiz:** "Quiz banao" → 5 MCQs, sahi jawab + timestamp ke saath.
- **Library search:** "Meri kaunsi videos mein Docker hai?" → saari videos mein se matching moments.
- **Verifier:** jawab ka har timestamp check hota hai; galat ho to dobara.
- Hinglish/adhoore sawaal ("db wala part?") bhi samajh aate hain (query rewrite).
- `/api/chat/stream` — chat jawab bhi streaming.

**Peeche:** multi-agent graph: rewrite → retriever → answer → verifier; summarizer, quiz, library search.
**Kyun:** zyada features + zyada bharosemand jawab.

---

## Day 11 — Poora web app ⭐

**Feature:** sab kuch browser mein, Swagger ki zarurat nahi.

**User flow (poori kahani):**
1. **Library:** link paste → card "Processing…" → kuch sec baad title + summary + "READY".
2. Card click → **Video page**: left mein player + chapters, right mein tabs **Chat · Transcript · Quiz**.
3. **Chat:** "database kaise connect kiya?" → jawab type hota aata hai → `[04:12]` click → video 4:12 se chalta hai, transcript bhi wahin scroll.
4. **Transcript tab:** chalte video ke saath current line highlight; kisi line par click = wahan jump; search box.
5. **Quiz tab:** 5 MCQ, jawab do, galat par "dekho [18:40]".
6. Model dropdown: ChatGPT / Claude, har jawab ke neeche "answered by …".
7. **Search page:** "Docker" → saari videos ke moments → click → us video ke us second par.

**Peeche:** React pages + components, streaming fetch, `react-player` `seekTo`.
**Kyun:** yahi demo video aur screenshots mein jaayega.

---

## Day 12 — Claude Desktop / Cursor se access (MCP)

**Feature:** website khole bina, AI assistant ke andar se apni video library use karo.

**User flow:**
1. Rahul Claude Desktop mein: "Meri videos mein JWT kahan samjhaya hai?"
2. Claude `search_videos` tool chalata hai → "Spring Security Course [22:10]".
3. "Uska flow samjhao" → `ask_video` → RAG jawab timestamps ke saath.
4. "Ye video bhi add karo: <link>" → `ingest_youtube` → web library mein naya card.

**Peeche:** MCP server → aapka FastAPI → wahi RAG + ChromaDB.
**Kyun:** core app ke liye zaroori nahi; extra access path + strong resume point.

---

## Day 13 — Notifications, auto-add, quality score

**Feature:**
- Video READY/FAILED hone par **email/Telegram notification**.
- Kisi YouTube channel ko follow karo → naya video aate hi **apne aap library mein**.
- Developer ke liye: **"Retrieval accuracy 85%"** jaisa number.

**User flow:**
1. Rahul link add karke chala gaya → 1 min baad Telegram: "✅ Spring Boot Course ready".
2. Channel watcher on → raat ko naya video aaya → subah library mein ready.

**Peeche:** backend → n8n webhook; n8n RSS schedule → `POST /api/videos`; `eval/run_eval.py`.

---

## Day 14 — Live launch ⭐

**Feature:** app internet par live; koi bhi ek command se chala sakta hai.

**User flow:**
1. Recruiter LinkedIn post se live link kholta hai → demo try karta hai.
2. GitHub par README: GIF, architecture, eval table, OpenAI vs Claude comparison.
3. Developer: `git clone` → `docker compose up` → app chal gaya.

**Peeche:** Dockerfiles, Compose, GitHub Actions green, deploy.

---

## Milestones

| Day | Milestone | Kya share karna hai |
|---|---|---|
| 7 | RAG chal raha hai | Swagger screenshot: sawaal + timestamp jawab |
| 11 | Poora web app | 30 sec screen recording: chat → timestamp click → video jump |
| 12 | MCP demo | Claude Desktop mein tool call ka clip |
| 14 | Launch | Live link + GitHub + 2 min demo video |