# VidMind AI — Seekho aur Banao (14-Day Learning Plan)

**Idea:** roz **ek topic** seekho, usi din ka **chhota exercise** karo, aur phir wahi cheez **project mein lagao**.
14 din ke end tak aapko LLM, embeddings, vector DB, RAG, agents, MCP sab samajh aa jaayega, aur VidMind AI GitHub par live hoga.

**Roz ka format (2–3 ghante):**

| Part | Time | Kya karna hai |
|---|---|---|
| 📖 Samjho | 30–45 min | Concept padho / video dekho |
| 🧪 Practice | 30–45 min | Ek chhota script `learn/dayXX.py` mein |
| 🛠️ Project | 60–90 min | VidMind AI mein woh feature banao |
| ✅ Check | 10 min | Self-check sawaal bina dekhe jawab do, notes `NOTES.md` mein likho |

**Setup (Day 0, 30 min):** Python 3.11+, VS Code, Node 20, Git. Ek folder `vidmind-ai/` banao, usme `learn/` aur `backend/` folders. OpenAI ya Anthropic API key lo (dono ka chhota credit kaafi hai). Har din ke end mein commit karo.

---

## Week 1 — Foundations: LLM → Embeddings → Vector DB → RAG

### Day 1 — LLM kya hai aur API se kaise baat karte hain

📖 **Samjho**
- LLM (Large Language Model) ek model hai jo **agla token predict** karta hai. Token = shabd ka tukda (lagbhag 4 English characters; Hindi mein zyada tokens lagte hain).
- **Context window** = model ek baar mein kitne tokens dekh sakta hai (prompt + jawab).
- **Temperature**: 0 = same, predictable jawab; 1 = zyada creative. RAG ke liye 0–0.3 rakhte hain.
- **Roles**: `system` (rules), `user` (sawaal), `assistant` (model ka jawab). Model ko pichli baatein yaad nahi rehti — har call mein history khud bhejni padti hai.
- **Hallucination**: model confident hokar galat bata sakta hai, kyunki woh "sach" nahi, "likely next words" deta hai. **Isi problem ko RAG solve karta hai.**

🧪 **Practice** — `learn/day01.py`
```python
from openai import OpenAI          # ya: import anthropic
client = OpenAI()
for t in [0, 1]:
    r = client.chat.completions.create(
        model="gpt-4o-mini", temperature=t,
        messages=[{"role": "system", "content": "You are a helpful teacher. Answer in Hinglish."},
                  {"role": "user", "content": "Spring Boot kya hai, 2 line mein?"}])
    print(t, r.choices[0].message.content, r.usage)
```
Ek hi sawaal 3 baar temperature 0 aur 1 par chalao, farak note karo. `usage` mein tokens dekho.

🛠️ **Project:** repo banao, `backend/app/main.py` mein FastAPI "hello" endpoint, `.env` + `.gitignore`.

✅ **Check:** Token kya hai? Temperature RAG mein kam kyun rakhte hain? Model ko pichli chat yaad kyun nahi rehti?

📚 Andrej Karpathy — "Intro to Large Language Models" (YouTube) · OpenAI / Anthropic docs ka "Quickstart"

---

### Day 2 — Prompt engineering + OpenAI vs Claude (provider layer)

📖 **Samjho**
- Achha prompt = **role + task + context + format + examples**.
- **Few-shot**: 1–2 example dene se output ka format pakka hota hai.
- OpenAI aur Claude ka API thoda alag hai: Claude mein `system` alag field hai aur `max_tokens` zaroori hai.
- **Adapter pattern**: ek common interface (`chat()`, `stream()`), andar alag-alag provider. Code ka baaki hissa provider ke baare mein kuch nahi jaanta.

🧪 **Practice** — same prompt OpenAI aur Claude dono par chalao, jawab aur speed compare karo. Phir ek bura prompt ("summary do") vs achha prompt ("3 bullet, har bullet 15 shabd se kam, Hinglish mein") compare karo.

🛠️ **Project:** `backend/app/llm/` — `base.py`, `openai_provider.py`, `claude_provider.py`, `factory.py` (Plan file ka section 5.6). Streaming bhi try karo.

✅ **Check:** Few-shot kya hai? Provider layer banane ka fayda kya hai? Claude aur OpenAI API mein 2 farak batao.

📚 Anthropic "Prompt engineering overview" · OpenAI "Prompt engineering guide"

---

### Day 3 — Data lana: YouTube transcript, Whisper, timestamps

📖 **Samjho**
- RAG ka pehla kadam: **apna data** lana. Yahan data = video ka transcript.
- YouTube captions mein har line ke saath `start` aur `duration` hota hai.
- Upload ke liye: FFmpeg se audio nikalo → **Whisper** (speech-to-text) → segments with `start`/`end`.
- Timestamps ko shuru se saath rakhna zaroori hai — wahi baad mein `[04:12]` banenge.

🧪 **Practice** — `learn/day03.py`: kisi bhi YouTube URL se video ID nikalo (`watch?v=`, `youtu.be/`, `shorts/` teeno), captions fetch karo, pehli 10 lines `mm:ss` format mein print karo.

🛠️ **Project:** `ingestion/youtube.py`, `models.py` (Video table with status), `POST /api/videos` jo transcript background mein fetch kare.

✅ **Check:** Whisper kya karta hai? Timestamps kyun save kar rahe hain? YouTube audio download karne mein kya legal dikkat hai?

📚 `youtube-transcript-api` README · `faster-whisper` README

---

### Day 4 — Embeddings: text ko numbers mein badalna

📖 **Samjho**
- **Embedding** = text ka matlab ek list of numbers (vector) mein, jaise 384 ya 1536 numbers.
- Matlab mein milte-julte sentences ke vectors **paas-paas** hote hain, chahe words alag hon ("DB connect kaise karein" ≈ "database URL set karna").
- **Cosine similarity**: do vectors kitne ek hi direction mein hain — 1 = bilkul same matlab, 0 = koi relation nahi.
- **Multilingual model** (jaise `multilingual-e5-small`) Hindi aur English ko ek hi "space" mein rakhta hai — isliye Hinglish sawaal Hindi video se match ho sakta hai.
- Rule: jis model se data embed kiya, **usi model** se sawaal embed karo.

🧪 **Practice** — `learn/day04.py`
```python
from sentence_transformers import SentenceTransformer, util
m = SentenceTransformer("intfloat/multilingual-e5-small")
s = ["query: database kaise connect karein",
     "passage: application.properties mein datasource URL set karo",
     "passage: aaj mausam bahut achha hai",
     "passage: डेटाबेस कनेक्शन के लिए URL सेट करें"]
v = m.encode(s, normalize_embeddings=True)
print(util.cos_sim(v[0], v[1:]))
```
Dekho kaunsa sentence sabse close aaya. Apne 5 sentences add karke try karo. (e5 models mein `query:` / `passage:` prefix lagate hain.)

🛠️ **Project:** `ingestion/embedder.py` — ek function `embed(texts) -> list[list[float]]`.

✅ **Check:** Embedding kya hai? Cosine similarity 0.9 ka matlab? Do alag embedding models ke vectors compare kyun nahi kar sakte?

📚 sbert.net (Sentence-Transformers docs) · 3Blue1Brown — "Transformers" video (word vectors wala part)

---

### Day 5 — Chunking: bade text ko sahi tukdon mein todna

📖 **Samjho**
- Poora transcript ek saath embed nahi karte — ek vector mein bahut saare topics mix ho jaate hain aur search kharab hota hai.
- Bahut chhote chunks (1 line) = context kam. Bahut bade (5000 words) = matlab dhundhla.
- Video ke liye ~250–400 words ka chunk + **overlap** (pichle chunk ki 1–2 lines repeat) achha rehta hai, taaki koi baat cut na ho.
- Har chunk ke saath **metadata**: `video_id`, `start`, `end`.

🧪 **Practice** — Day 3 ke transcript ko 100, 300 aur 800 words ke chunks mein todo; har case mein chunks ki ginti aur pehle chunk ka start/end print karo.

🛠️ **Project:** `ingestion/chunker.py` + `tests/test_chunker.py` (pytest: overlap sahi hai, timestamps badhte ja rahe hain, khaali input).

✅ **Check:** Overlap kyun? Chunk size ka search par kya asar padta hai? Metadata kya hota hai?

---

### Day 6 — Vector Database: ChromaDB

📖 **Samjho**
- **Vector DB** = embeddings store karne aur "sabse milte-julte" dhoondhne ka database.
- Normal DB: `WHERE title = 'Docker'` (exact). Vector DB: "Docker jaisa matlab wale top 5" (similarity).
- Lakhon vectors mein har ek se compare karna slow hai, isliye **HNSW index** (ek graph) use hota hai — approximate par bahut fast search.
- ChromaDB mein: `collection` (table jaisa), `documents` (text), `embeddings`, `metadatas`, `ids`, aur `where` filter.
- Doosre options: pgvector (Postgres ke andar), Qdrant, Pinecone — interview mein farak batana aana chahiye.

🧪 **Practice** — `learn/day06.py`: 20 sentences ChromaDB mein daalo (metadata mein `topic`), phir query karo, `where={"topic": "java"}` filter lagao, `distances` dekho.

🛠️ **Project:** `vectorstore/chroma_store.py` — `add_chunks`, `search(question, video_id, k)`, `delete_video`. Indexing pipeline: transcript → chunks → Chroma; status `READY`. `GET /api/search?q=` banao.

✅ **Check:** Vector DB aur SQL DB mein farak? HNSW kya karta hai (simple words)? ChromaDB vs pgvector kab kaunsa?

📚 docs.trychroma.com — "Getting Started"

---

### Day 7 — RAG: sab kuch jodna (Retrieve → Augment → Generate)

📖 **Samjho**
- **R**etrieve: sawaal ka embedding → vector DB se top-k chunks.
- **A**ugment: un chunks ko prompt mein daalo.
- **G**enerate: LLM sirf un chunks se jawab de, timestamps ke saath.
- Hallucination rokne ke tareeke: "sirf context se jawab do", "nahi mila to bolo", citations, low temperature.
- `k` (kitne chunks): bahut kam = jawab adhoora; bahut zyada = noise + mehenga.

🧪 **Practice** — pehle bina RAG ke LLM se video ke baare mein poochho (galat/generic jawab aayega), phir RAG ke saath. Dono ka farak screenshot karke `NOTES.md` mein rakho — interview story ban jaayegi.

🛠️ **Project:** `POST /api/chat` — search + prompt + `get_llm().chat()`; jawab mein `[mm:ss]`. 10 sawaal test karo.

✅ **Check:** RAG ke 3 steps? RAG fine-tuning se kab behtar hai? Agar galat chunk aaye to kya galat ho sakta hai aur kaise sudhaaroge?

📚 Anthropic / OpenAI docs ke "RAG" / "retrieval" guides

**Week 1 ka result:** YouTube URL do → index ho → sawaal poochho → timestamps ke saath jawab. 🎉 Isse GitHub par push karo.

---

## Week 2 — Advanced: Structured Outputs → Agents → MCP → Production

### Day 8 — Structured outputs + Tool calling

📖 **Samjho**
- **Structured output**: LLM se pakka JSON lena, Pydantic schema ke hisaab se (title, summary, chapters, tags).
- **Tool / function calling**: aap model ko functions ki list dete ho; model decide karta hai kaunsa call karna hai aur kin arguments ke saath. Function **aapka code** chalata hai, result model ko wapas deta hai.
- Claude mein structured JSON ka reliable tareeka: tool ka `input_schema` = Pydantic schema, aur `tool_choice` se usse force karo.

🧪 **Practice** — ek `get_weather(city)` jaisa fake tool banao, model se "Delhi ka mausam?" poochho, dekho woh tool call karta hai.

🛠️ **Project:** `VideoInsights` (title, summary, chapters, tags) indexing ke baad generate karke DB mein save; `structured()` method dono providers mein.

✅ **Check:** Structured output aur tool calling mein farak? Tool asal mein kaun chalata hai — model ya aapka code?

---

### Day 9 — Agents aur LangGraph basics

📖 **Samjho**
- **Agent** = LLM jo khud decide kare agla step kya hai (tool call, ya jawab).
- **LangGraph**: agents ko ek **graph** ki tarah jodna — **nodes** (functions), **edges** (agla kaun), **state** (sabke beech shared data).
- **Conditional edge**: state dekh ke raasta chuno (jaise router).

🧪 **Practice** — 2 node ka graph: `classify` (sawaal "math" hai ya "general") → `answer`. State print karke flow samjho.

🛠️ **Project:** `agents/state.py`, `agents/router.py` (intent: qa / summary / search_library / quiz), `agents/graph.py` mein router + retriever + answer.

✅ **Check:** Node, edge, state kya hai? Ek bade prompt ke bajaye graph kyun?

📚 LangGraph docs — "Quickstart"

---

### Day 10 — Multi-agent system + Verifier

📖 **Samjho**
- Har agent ka **ek kaam**: Router, Retriever, Answer, Summarizer, Quiz, Library Search, **Verifier**.
- **Verifier** jawab check karta hai — har `[mm:ss]` sach mein kisi retrieved chunk ke andar hai ya nahi; nahi to Answer agent ko ek baar retry.
- **Query rewriting**: Hinglish/adhoore sawaal ko search ke liye saaf query mein badalna — retrieval behtar hota hai.

🧪 **Practice** — jaan-boojh ke galat timestamp wala jawab verifier ko do, dekho woh pakadta hai.

🛠️ **Project:** baaki agents + verifier loop; `POST /api/chat` ab `agent_app.invoke()` use kare; SSE streaming endpoint.

✅ **Check:** Multi-agent ka fayda aur nuksaan (cost, latency)? Verifier kaise decide karta hai?

---

### Day 11 — Frontend: React + Vite

📖 **Samjho**
- Vite = fast dev server + build tool. React Router, axios, Tailwind.
- **SSE / streaming**: jawab word-by-word aata hai (ChatGPT jaisa).
- `react-player` ka `seekTo(seconds)` — timestamp click → video wahan.

🧪 **Practice** — ek component jo text mein `[04:12]` dhoondh ke button banaye (Plan file section 10).

🛠️ **Project:** Login, Library (status badges), Add video (URL + upload), Video page (player + chapters + chat + quiz), model dropdown (ChatGPT / Claude).

✅ **Check:** Streaming kaise kaam karta hai? Status ke liye polling vs websocket?

---

### Day 12 — MCP: apne system ko AI assistants se jodna

📖 **Samjho**
- **MCP (Model Context Protocol)** = ek standard jisse koi bhi AI app (Claude Desktop, Cursor) aapke **tools** use kar sake.
- Function calling ek app ke andar hota hai; MCP ek **common plug** hai — ek baar server banao, kai AI clients use karein.
- MCP server **patla** hota hai: woh aapke existing API ko call karta hai.

🧪 **Practice** — ek `add(a, b)` tool wala FastMCP server banao, Claude Desktop se jodo, use karwao.

🛠️ **Project:** `mcp_server/server.py` — `search_videos`, `ask_video`, `get_video_summary`, `ingest_youtube`. Claude Desktop mein chalate hue screen record karo.

✅ **Check:** MCP vs function calling? MCP server mein auth kaise handle karoge?

📚 modelcontextprotocol.io — "Quickstart (server)"

---

### Day 13 — Evaluation + n8n automation

📖 **Samjho**
- **Eval** bina sab andaaza hai. 20 sawaal + expected timestamp → **hit rate @k** = kitne sawaalon mein sahi chunk top-k mein aaya.
- Ek-ek cheez badlo (chunk size, k, embedding model, provider) aur number dekho.
- **n8n**: no-code automation — webhook, schedule, HTTP request, email/Telegram.

🧪 **Practice** — chunk size 150 vs 300 vs 600 par eval chalao, table banao.

🛠️ **Project:** `eval/questions.json` + `eval/run_eval.py --provider openai|claude`; n8n "video ready" + "YouTube channel watcher" workflows, JSON export.

✅ **Check:** Hit rate @6 ka matlab? Aapke eval mein kya badla aur kyun?

📚 n8n docs — "Webhook node", "Schedule trigger"

---

### Day 14 — Production: Docker, CI, README, launch

📖 **Samjho**
- Docker = "mere laptop par chalta hai" problem khatam. Compose = sab services ek command mein.
- CI (GitHub Actions) = har push par tests + build.
- README hi aapka **sales page** hai.

🛠️ **Project:** Dockerfiles + `docker-compose.yml`, GitHub Actions (ruff + pytest + `npm run build`), README (problem, features, architecture, setup, GIF, eval table, OpenAI vs Claude comparison), 2-minute demo video, deploy, LinkedIn post. Resume mein project add karo.

✅ **Final self-test (bina dekhe whiteboard par samjhao):**
1. Token, context window, temperature
2. Embedding aur cosine similarity
3. Chunking aur overlap
4. Vector DB aur HNSW
5. RAG ke 3 steps, hallucination kaise kam ki
6. Structured output vs tool calling
7. Aapka multi-agent graph aur verifier
8. MCP kya hai aur aapka server kya karta hai
9. Aapke eval numbers aur kya improve kiya

Agar ye 9 cheezein aap 2–2 minute mein samjha sakte ho, to RAG/AI wale interview ke liye ready ho.

---

## Daily tracker

| Day | Topic | Done | Commit | Notes |
|---|---|---|---|---|
| 1 | LLM basics + API | ☐ | | |
| 2 | Prompting + provider layer | ☐ | | |
| 3 | Transcript + Whisper | ☐ | | |
| 4 | Embeddings | ☐ | | |
| 5 | Chunking | ☐ | | |
| 6 | Vector DB (ChromaDB) | ☐ | | |
| 7 | RAG | ☐ | | |
| 8 | Structured outputs + tools | ☐ | | |
| 9 | Agents + LangGraph | ☐ | | |
| 10 | Multi-agent + verifier | ☐ | | |
| 11 | React + Vite frontend | ☐ | | |
| 12 | MCP | ☐ | | |
| 13 | Eval + n8n | ☐ | | |
| 14 | Docker, CI, launch | ☐ | | |

**Tip:** roz ke `NOTES.md` ko apne Instagram/LinkedIn par "Day X of building an AI project" post ki tarah share karo — seekhna bhi pakka hoga aur profile bhi banega.
