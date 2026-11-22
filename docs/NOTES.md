# My Learning Notes

Write each concept in my own words after learning it. If I can't explain it here, I don't understand it yet.

## Day 1 — LLM basics
- Token: text ka chhota tukda (~4 English characters). Bill tokens pe banta hai, input + output dono. Hindi mein same baat ke zyada tokens lagte hain.
- Context window: ek call mein model kitne tokens dekh sakta hai (system + history + sawaal + jawab). Iske bahar ki cheez model ke liye exist nahi karti.
- Temperature: agla token kitni randomness se chunna hai. 0 = har baar same, 1 = creative. RAG mein kam rakhte hain. Naye Claude API (2026-10-21) mein temperature hata diya gaya hai, wahan `effort` + prompt se control karte hain.
- Why the model doesn't remember old chats: API stateless hai. Har call nayi hoti hai, isliye poori history khud bhejni padti hai (`/api/llm/chat` yahi karta hai).
- Hallucination: model "sach" nahi, "likely next words" deta hai, isliye confident hokar galat bol sakta hai. RAG + low temperature + "pata nahi to bolo" se kam hota hai.
- My test: `/api/llm/chat` mein history ke saath "Mera naam kya hai?" ka jawab sahi aaya, bina history ke model ko nahi pata tha.

## Day 2 — Prompting
- Achha prompt = role + task + context + format + examples.
- Few-shot = 1-2 examples (user → assistant history ki tarah) dikhao, format pakka ho jaata hai. Nuksaan: zyada input tokens.
- `/api/llm/prompt-styles` test: bad prompt ka jawab lamba aur bina format ka, good/few-shot mein 3 bullet aaye. Few-shot ke input tokens sabse zyada.
- Adapter pattern: app sirf `llm.complete()` / `llm.stream()` jaanta hai. Claude API badla to sirf `claude_provider.py` badla, baaki code same raha.
- Streaming (SSE): total time same, par first token jaldi aata hai, isliye app fast lagti hai. Stream ke beech error aaye to `error` event bhejte hain (status 200 pehle hi ja chuka hota hai).
- OpenAI vs Claude: Claude mein `system` alag field hai, `max_tokens` zaroori hai, aur ab temperature nahi hai.

## Day 3 — Transcript + background job
- Ingestion = RAG ka pehla kadam: link → 11-char video ID → captions (text + start + end) → database.
- Timestamps shuru se save karte hain, kyunki Day 7 mein jawab `[04:12]` citations ke saath aayega.
- Auto-generated captions (`is_generated: true`) mein galtiyan hoti hain, jo search quality pe asar daalti hain.
- Background job: `POST /api/videos` turant 202 + `pending` deta hai, kaam peeche chalta hai: `pending → processing → ready / failed`. Frontend status poll karta hai.
- `BackgroundTasks` restart pe kaam kho deta hai, isliye startup pe atke jobs `failed` mark hote hain. Production mein Celery/RQ + Redis.
- `youtube_id` unique hai, isliye same video dobara add karne pe purana record milta hai (idempotent).
- Legal: YouTube captions theek hain, audio download ToS ke khilaaf hai. Whisper sirf apni upload ki hui files pe.

## Day 4 — Embeddings
- Embedding: text ka matlab numbers ki list mein. `multilingual-e5-small` har text ke liye 384 numbers deta hai. Milta-julta matlab = paas-paas vectors, chahe shabd alag hon.
- Cosine similarity: do vectors ki direction kitni same hai. 1 = same matlab, 0 = koi relation nahi, -1 = ulta. Vectors normalize hain (length 1), isliye cosine = dot product.
- e5 ke scores 0.75-0.90 ke beech hi rehte hain. Score ki value nahi, **ranking** dekho (sabse upar kaun hai).
- e5 rule: sawaal pe `query:` aur data pe `passage:` prefix lagao. Jis model se data embed kiya, usi model se sawaal embed karo. Do alag models ke vectors compare nahi ho sakte.
- My test (`learn/day04_embeddings.py`): "database kaise connect karein" ke top 3 English, Hindi aur Hinglish DB wale sentences aaye. Mausam aur cricket neeche rahe. Multilingual model Hindi + English ko ek hi "space" mein rakhta hai.
- My test (semantic search on video): "I will never leave you" se "Never gonna give you up" mila, jabki shabd alag the. Par Hinglish sawaal ne sirf related line dhoondhi, kyunki segments bahut chhote hain aur model chhota hai. Day 5 chunking se ye behtar hoga.
- Pehli search 606 ms (61 segments embed hue), cached search 18 ms. Har sawaal pe saare segments embed karna slow hai, isliye Day 6 mein vector DB mein pehle se save karenge.

## Day 5 — Chunking
- Chunk: lambe transcript ka chhota tukda jo ek baar mein embed hota hai. Poora transcript ek vector mein daalo to saare topics mix ho jaate hain. Har line alag rakho to context nahi bachta.
- Mera chunker poore segments jodta hai jab tak `max_words` (default 300) na ho jaaye, taaki sentence beech mein na kate. Bahut lamba segment mile to use words mein todta hai aur time baraabar baant deta hai.
- Overlap: agla chunk pichle chunk ke aakhri ~50 words (poore segments) se shuru hota hai. Jo baat do chunks ki seema pe hai, wo kisi ek chunk mein poori mil jaati hai.
- Metadata: har chunk ke saath `start`, `end`, `first_segment`, `last_segment`. Isi se jawab mein `[mm:ss]` timestamp dikhega (Day 7).
- My test (`learn/day05_chunking.py`, 487 words ka video): 100 words = 6 chunks, 300 = 2 chunks, 800 = 1 chunk. Size badha to chunks kam, par har chunk ka matlab dhundhla.
- My test (semantic search, 100 words + 20 overlap): Hinglish "main tumhe kabhi dhokha nahi dunga" ab chorus wala chunk ("never gonna ... hurt you") laaya. Segments pe ye galat lines laata tha. 61 segments embed karne mein 920 ms, 6 chunks mein 395 ms.
- Rule of thumb: video ke liye 250-400 words + 10-20% overlap. Asli size eval se tay hoga (Day 13).

## Day 6 — Vector DB
- Vector DB vs SQL: SQL exact match dhoondhta hai (`WHERE title = 'Docker'`). Vector DB "matlab mein sabse paas" wale top-k dhoondhta hai. Hum dono use karte hain: SQLite mein videos aur status, Chroma mein chunk vectors.
- HNSW: vectors ka ek graph jisme har vector apne kuch paas wale padosiyon se juda hota hai. Search upar ki layer se shuru hoke padosiyon pe kood-kood ke paas pahunchta hai. Har vector se compare nahi karna padta, isliye lakhon vectors mein bhi fast (approximate, par lagbhag hamesha sahi).
- Chroma mein: collection (table jaisa), ids (`video_id:position`), documents (chunk text), embeddings (humne khud e5 se banaye), metadatas (`video_id`, `start`, `end`, `title`), aur `where={"video_id": 1}` filter.
- Distance vs score: collection `cosine` pe hai, Chroma distance = 1 - cosine deta hai. Hum `score = 1 - distance` dikhate hain.
- Same-model rule ko code mein pakka kiya: collection ke metadata mein `embedding_model` save hai. Model badla to app error deta hai, chupchaap galat results nahi.
- Indexing pipeline: transcript → chunks (300 words, 50 overlap) → embed → Chroma → status `ready`. Naya status `indexing` beech mein aata hai.
- My test (`learn/day06_chroma.py`): "database se data kaise nikaalein" ka top result "JPA repository se database query likho" (distance 0.093). `where={"topic": "java"}` se sirf java wale aaye.
- My test (live): 2 videos (Rick Astley 2 chunks, 1 ghante ka LLM talk 49 chunks). Library search "jailbreak attacks on LLM security" ne 47:28, 50:07, 57:34 laaye. Server restart ke baad bhi vectors bache rahe. Cached model ke saath search ~20-200 ms.
- Bug: do videos ek saath add kiye to dono background threads ne ek saath Chroma client banaya aur indexing fail hui. Lock lagaya (store aur model dono pe), ab theek hai.
- ChromaDB vs pgvector: Chroma = alag, simple, Python-native, chhote/medium projects. pgvector = Postgres ke andar, SQL join + vector search ek jagah, already Postgres hai to best. Qdrant/Pinecone = bade scale, managed.

## Day 7 — RAG
- R (Retrieve): sawaal ka embedding (`query:` prefix) → Chroma se top-k (default 6) chunks, `where={"video_id": ...}` ke saath.
- A (Augment): chunks ko `<context>` mein daalo, har chunk ke upar `[mm:ss] (until mm:ss)` header. Model wahi timestamp copy karta hai, isliye citation sahi aata hai.
- G (Generate): system prompt: sirf context se jawab, har fact ke baad `[mm:ss]`, nahi mila to `NOT_FOUND`, sawaal ki bhasha mein jawab. Temperature 0.2 (Claude pe effort low).
- Without RAG vs with RAG (my test, 1 ghante ka LLM talk, Claude haiku): talk famous hai to bina RAG bhi model ne "2 files, 140 GB" bataya, par **koi timestamp nahi** aur khud bola "my knowledge of the talk, figures may differ". RAG ke saath wahi facts `[01:17]` citation ke saath, transcript se. Kam famous ya private video pe bina RAG model ya to mana karega ya galat banayega.
- 10 sawaal test kiye: 9 sahi jawab + timestamps (LLM OS [42:18], system 1/2 [35:18], fine-tuning [14:33], scaling laws [24:35], prompt injection [51:23], Hinglish pretraining sawaal ka Hinglish jawab [03:41] [04:55]). "2011 cricket world cup" pe sahi se NOT_FOUND.
- Cost: har RAG sawaal ~3000 input tokens (6 chunks × ~300 words) + 150-400 output. Retrieval ~250-450 ms, LLM ~1-3 s.
- `/api/chat/compare` dono jawab ek saath deta hai, interview demo ke liye.

## Day 8 — Structured outputs + tool calling
- Structured output: LLM se pakka JSON, Pydantic schema ke hisaab se. Claude: `client.messages.parse(output_format=Schema)` (andar `output_config.format` json_schema). OpenAI: `chat.completions.parse(response_format=Schema)`. Dono `llm.structured(system, messages, Schema)` ke peeche, routes ko farak nahi padta.
- Naye Claude models pe forced `tool_choice` (type `tool`/`any`) kai models pe 400 deta hai, isliye JSON ke liye structured outputs hi sahi raasta hai. Tools ke liye `strict: true` + `additionalProperties: false`.
- Tool calling: model sirf bolta hai "get_weather({city: Delhi}) chalao". Tool **mera code** chalata hai, result `tool_result` mein wapas jaata hai, model phir jawab likhta hai. Loop tab tak jab tak `stop_reason != "tool_use"`.
- My test (`learn/day08_tools.py`): "Delhi ka mausam" → 1 tool call. "Mumbai aur Shimla mein kahan thand" → ek hi step mein 2 parallel tool calls, phir sahi comparison. "Paris" → tool nahi chalaya, mana kiya. "2+2" → tool ki zaroorat hi nahi.
- VideoInsights (title, summary, chapters, tags, key_points) indexing ke baad apne aap banta hai (`AUTO_INSIGHTS=true`) aur `video_insights` table mein save hota hai. `POST /api/videos/{id}/insights` se dobara bana sakte hain.
- LLM ka JSON bhi saaf karna padta hai: chapter timestamps check (format, video ki length ke andar, duplicate hatao, pehla 00:00), tags lowercase + unique.
- Chapters sirf transcript ke markers pe ban sakte hain. Pehle har chunk pe ek marker tha (Rick video = sirf 2 chapters). Ab har ~30 second pe marker, to 7 achhe chapters aaye.
- Lamba video (> 40k words): map-reduce. Har hisse ke partial insights, phir ek merge call.
- My test: 1 ghante ka LLM talk → 14 chapters (00:00 se 44:55 security tak), 8 tags, key points ("70B model = 140 GB"). Cost ~20k input tokens, haiku pe ~0.2 cent.

## Day 9 — Agents + LangGraph
- Agent: LLM jo khud decide kare agla step kya hai. Hamare app mein Router agent decide karta hai sawaal kis type ka hai.
- LangGraph: **state** (TypedDict, sab nodes ke beech shared data), **nodes** (functions jo state lete hain aur sirf badla hua hissa lautate hain), **edges** (agla node kaun), **conditional edge** (state dekh ke raasta chuno).
- Reducer: `steps: Annotated[list, operator.add]` matlab har node ka `steps` purani list mein jud jaata hai, overwrite nahi hota. Tokens bhi isi tarah jodte hain.
- `learn/day09_graph.py`: classify → math / general. "12 * (3 + 4)" math raaste gaya (84), "Docker kya hai?" general raaste. `draw_mermaid()` se graph ki picture.
- Project graph: router (structured output se `qa / summary / search_library / quiz` + reason) → retriever → answer. Video khula nahi hai to router ka jawab `search_library` mein badal dete hain.
- `POST /api/agent/chat` poora trace deta hai: `intent`, `route_reason`, `steps` (`router:qa → retriever:6 → answer`).
- My test (live, Claude): 4/4 sahi intent. "Pretraining mein kitna data" → qa, "summary do" → summary, "3 MCQ banao" → quiz, bina video "jailbreak wali video kaunsi" → search_library aur sahi video mili.
- Abhi har intent retriever + answer se hi jaata hai. Day 10 mein har intent ka apna agent aur verifier.
- Kharcha: router ek extra LLM call hai (~1-3 s). Graph ka fayda: har step alag, test karna aasaan, naya step jodna aasaan.

## Day 10 — Multi-agent + verifier
- Graph: router → (qa: retriever → answer → verifier) / (search_library: library_search → answer → verifier) / (summary: summarizer) / (quiz: quiz). Verifier fail hua to answer ek baar dobara (feedback ke saath), phir bhi galat to galat timestamps hata deta hai.
- Har agent ka ek kaam: Router (intent + query rewrite), Retriever (ek video), Library Search (saari videos), Answer (RAG), Summarizer (saved insights se, nahi hai to banata hai), Quiz (MCQ + notes, structured), Verifier (code, LLM nahi).
- Verifier kaise decide karta hai: jawab ke har `[mm:ss]` ko seconds mein badlo, dekho kisi retrieved chunk ke `start-2s ... end+2s` ke andar hai ya nahi. Koi citation hi nahi hai to bhi retry. NOT_FOUND pe check nahi.
- Query rewriting router ke structured output mein hi (`search_query`), alag LLM call nahi. "DB ka url kidhar daalna hai bhai?" jaisa sawaal saaf keywords mein badal jaata hai.
- Streaming: `POST /api/chat/stream` (SSE). Events: `start`, `step` (har node ke baad), `token` (answer ke shabd, LangGraph `get_stream_writer` se), `retry`, `done` (poora result), `error`.
- My test (`learn/day10_agents.py`): galat `[12:00]` wala jawab → `verifier:retry` → phir bhi galat to `[12:00]` hata diya, `[03:41]` rakha. Bina citation wala jawab bhi pakda gaya.
- My test (live, warm server): router 1.6 s, retriever 2.3 s, pehla token 4.2 s, done 5.2 s. Cold start (server restart ke baad) ~50 s, kyunki embedding model load hota hai.
- Summary 2 s (saved insights), quiz 3 MCQ ~16 s, library search sahi video + [51:23].
- `POST /api/chat` ab agent graph chalata hai. Purana seedha RAG `POST /api/chat/rag` pe hai.
- Fayda vs nuksaan: har agent chhota aur testable, verifier galat citation pakadta hai. Par router + retry = zyada LLM calls, zyada latency aur cost.

## Day 11 — React frontend
- Pages: Library (`/`: video add, status badges, 2 s polling jab tak koi video pending/processing/indexing hai, retry, delete, meaning se library search, library chat) aur Video (`/videos/:id?t=`: player, summary + tags + clickable chapters + key points, chat, quiz).
- `RichText` component (practice wala): jawab mein `[04:12]` regex se dhoondh ke button banata hai, click → `seekTo(252)`. `**bold**` aur `- bullet` bhi.
- Player: YouTube IFrame API seedha (`window.YT.Player`), `forwardRef` se `seekTo()` bahar diya. Library chat ka timestamp doosri video ka ho to us video pe `?t=` ke saath chale jaate hain.
- Streaming: `EventSource` sirf GET karta hai, hamara `/api/chat/stream` POST hai. Isliye `fetch` + `res.body.getReader()` se padha, `\n\n` pe tod ke `data: {...}` parse kiya. Events: step (chips), token (text judta hai), retry (text saaf), done (final jawab + quiz), error.
- Quiz: options pe click → sahi hara, galat laal, explanation + timestamp, score.
- Model dropdown: `/api/llm/providers` se, jiski key nahi wo disabled ("no key").
- Polling vs websocket: status har 2 s poll karna simple hai aur sirf busy videos tak chalta hai. Websocket/SSE tab jab bahut users ya turant update chahiye.
- Test: `npm run build` (tsc + vite) saaf. Headless Chrome se dono pages ke screenshots dekhe. Frontend ka `streamChat` Node mein live server pe chalaya: quiz (steps + result) aur QA (101 token events, verified, [35:18] [36:23]).
- Abhi nahi bana: login (backend mein auth nahi hai) aur video upload (Whisper wala raasta). Dono TODO.

## Day 12 — MCP
- MCP (Model Context Protocol): ek standard plug. Ek baar MCP server banao, phir Claude Desktop, Cursor ya koi bhi MCP client mere tools use kar sakta hai. Function calling ek app ke andar hota hai; MCP tools ko app ke bahar, sabke liye kholta hai.
- Server ke 3 cheezein de sakta hai: tools (actions), resources (data padhna), prompts (templates). Maine tools banaye.
- `mcp_server/server.py` patla hai: koi AI logic nahi, sirf VidMind API (`/api/videos`, `/api/search`, `/api/chat`, `/api/videos/{id}/insights`) ko httpx se call karta hai. Saara dimaag backend mein hi rehta hai.
- 5 tools: `list_videos`, `search_videos`, `ask_video`, `get_video_summary` (nahi bana to bana deta hai), `ingest_youtube`. Read-only tools pe `readOnlyHint` annotation, taaki client jaane ye kuch badalte nahi.
- Transport: `stdio` (Claude Desktop server ko subprocess ki tarah chalata hai, stdin/stdout pe baat) ya `streamable-http` (remote).
- `mcp` 2.x mein `FastMCP` ka naam `MCPServer` ho gaya (`from mcp.server.mcpserver import MCPServer`). Normal exception ka message chhup jaata hai, isliye `ToolError` raise karo taaki AI ko asli wajah dikhe ("Video not found").
- Auth: backend mein abhi login nahi hai. Server `VIDMIND_API_KEY` ho to `Authorization: Bearer` bhejta hai. Remote MCP ke liye OAuth (MCP spec ka auth) ya API key + HTTPS.
- My test: `learn/day12_mcp_add.py --demo` (add, multiply). Asli server stdio subprocess ki tarah chalaya, live backend pe 5 calls: list, search ("data poisoning" → [55:08]), ask (LLM OS [42:18]), summary, aur galat id pe saaf error. 8 pytest tests (in-process MCP client + mock API).
- Claude Desktop config `mcp_server/README.md` mein hai. Screen recording abhi baaki hai (mujhe Claude Desktop pe khud chalana hai).

## Day 13 — Eval + n8n
- Eval ke bina sab andaaza hai. 28 sawaal (22 English, 6 Hinglish) 1 ghante ke LLM talk pe, har sawaal ke saath sahi time window (transcript padh ke nikali, jaise "10 TB" = 04:49-04:57).
- Hit@k: kitne sawaalon mein sahi chunk top-k mein aaya. MRR: sahi chunk kitna upar aaya (1/rank ka average).
- Chunk size: 150 → Hit@1 79%, 300 → 82%, 600 → 68%. MRR 0.86 / 0.89 / 0.77. 300 sabse achha, isliye default 300 hi rakha. 600 mein ek vector mein kai topics mil jaate hain.
- Language: English Hit@1 91%, Hinglish sirf 50%. Chhota e5 model Romanised Hindi pe kamzor hai.
- Query rewriting (Day 10 router): Hit@6 96% → 100% (Hinglish 83% → 100%), par Hit@1 thoda gira (keywords mein sawaal ka matlab thoda kho jaata hai). Original + rewritten dono ko RRF se milaya, fayda nahi hua. Answer step saare 6 chunks padhta hai, isliye Hit@6 zyada maayne rakhta hai, rewriting rakhi.
- LLM wale hisse har run mein thoda badalte hain (rewrite aur answers), isliye range likhi (93-96%). Ek run pe bharosa mat karo.
- Answers: Claude haiku, 93-96% jawab sahi moment cite karte hain, ~2.3 s. Jo miss hue wahan retrieval fail tha, aur model ne galat banane ki jagah NOT_FOUND bola.
- n8n: backend `N8N_WEBHOOK_URL` pe `video.ready` / `video.failed` POST karta hai (title, summary, chapters, app link). Workflow 1: Webhook → IF → Telegram. Workflow 2: har 6 ghante → channel RSS → naye uploads → `POST /api/videos`. Local receiver se live test kiya, payload sahi aaya. Webhook fail ho to sirf warning, ingest nahi tootta.

## Interview answers (practice)
1. Why ChromaDB? Local, free, Python se seedha chalta hai, disk pe save hota hai (PersistentClient), metadata filter (`where`) deta hai. Is size ke project ke liye alag server nahi chahiye. Scale badhe to pgvector ya Qdrant pe ja sakte hain, kyunki store ek wrapper (`chroma_store.py`) ke peeche hai.
2. Why chunk overlap? Chunk ki seema pe koi baat aadhi ek chunk mein aur aadhi agle mein chali jaati hai. Overlap se wo baat kam se kam ek chunk mein poori rehti hai. Kharcha: thoda zyada storage aur embedding.
3. How did I reduce hallucinations? (1) Sirf retrieved context se jawab ka rule, (2) har fact pe `[mm:ss]` citation, (3) jawab na mile to `NOT_FOUND` bolna allowed (aur hum use friendly message mein badalte hain), (4) low temperature / low effort, (5) Day 10 mein verifier jo check karta hai ki har timestamp kisi retrieved chunk ke andar hai.
4. Keyword search vs semantic search? Keyword search exact shabd dhoondta hai ("database" likha hai to milega). Semantic search matlab dhoondta hai ("DB connect" ≈ "datasource URL set karo"). Best result dono ko milake milta hai (hybrid search).
5. Embedding model kaise chunoge? Language support (Hindi chahiye to multilingual), dimension (size vs quality), speed, cost (local free vs API), aur apne data pe test karke.
6. Model badal diya to kya karna padega? Saara data dobara embed karna padega, kyunki purane aur naye vectors compare nahi ho sakte.
7. Chunk size ka search pe asar? Chhote chunks = exact match par context kam, LLM ko adhoora jawab. Bade chunks = context zyada par ek vector mein kai topics, ranking dhundhli aur prompt mein tokens zyada. Isliye beech ka size aur eval se tune.
8. Chunking ke tareeke? Fixed size (words/tokens), sentence/segment boundary pe, recursive (paragraph → sentence → word), semantic (matlab badle wahan todo). Video ke liye segment boundary + time metadata best hai.
9. Vector DB aur SQL DB mein farak? SQL exact values aur joins ke liye, vector DB similarity (top-k paas wale vectors) ke liye. Vector DB HNSW jaise index se approximate nearest neighbour fast dhoondhta hai.
10. HNSW kya hai? Padosiyon ka multi-layer graph. Upar ki layer mein lambi chhalaang, neeche ki layer mein chhoti. Har vector se compare kiye bina paas wale mil jaate hain.
11. RAG ke 3 steps? Retrieve (vector search se top-k chunks), Augment (chunks prompt mein), Generate (LLM context se jawab + citations).
12. RAG vs fine-tuning? RAG: naya ya private data, jaldi update, citations, sasta. Fine-tuning: style/format/behaviour sikhana, data model ke andar ghus jaata hai, update mehenga, citation nahi. Video Q&A ke liye RAG.
13. Galat chunk aaye to? Jawab galat ya NOT_FOUND aayega. Sudhaar: chunk size/overlap tune karo, k badhao, query rewriting, hybrid (keyword + vector) search, reranker, aur eval se naapo.
14. Structured output vs tool calling? Structured output = jawab ka format fix (pakka JSON schema). Tool calling = model ek action maangta hai (function + arguments), aapka code use chalata hai aur result wapas deta hai. Structured output ek baar ka jawab, tool calling ek loop.
15. Tool kaun chalata hai? Hamesha aapka code. Model sirf naam aur arguments deta hai. Isliye validation, permissions aur errors (`is_error: true`) aapke haath mein.
16. Node, edge, state kya hai? State = shared data (sawaal, chunks, jawab). Node = ek function jo state padhta hai aur update lautata hai. Edge = agla node. Conditional edge = state ke hisaab se raasta (jaise intent).
17. Ek bade prompt ki jagah graph kyun? Har step ka ek kaam (chhote, focused prompts), har node ka alag test, beech mein code se check (verifier, retries), aur naya agent jodna aasaan. Nuksaan: zyada LLM calls = zyada latency aur cost.
18. Multi-agent ka fayda aur nuksaan? Fayda: har agent ka chhota prompt aur ek kaam, alag test, alag model chun sakte ho, verifier jaisa check beech mein. Nuksaan: zyada calls (router + answer + retry) = zyada latency aur cost, debug mein zyada steps. Isliye trace (`steps`) aur tokens log karte hain.
19. Verifier kaise decide karta hai? Regex se `[mm:ss]` nikalo, seconds mein badlo, check karo ki kisi retrieved chunk ke time range (±2 s) mein hai. Galat ho ya citation na ho to feedback ke saath ek retry, phir bhi galat to galat timestamp hata do. Ye code hai, LLM nahi, isliye sasta aur pakka.
20. Streaming kaise kaam karta hai? Server ek lambi HTTP response kholta hai (`text/event-stream`) aur har token aate hi `data: {...}\n\n` likh deta hai. Browser `fetch` ka body stream padhta hai aur UI turant update karta hai. User ko pehla shabd ~4 s mein dikhta hai, poora jawab ka wait nahi.
21. Status ke liye polling vs websocket? Polling: har N second GET, simple, stateless, thode users ke liye kaafi. Websocket/SSE: server khud batata hai, kam requests, turant update, par connection sambhalna padta hai. Mainne polling li, sirf jab koi video busy ho.
22. MCP vs function calling? Function calling: ek app apne LLM ko tools deta hai, sirf us app ke andar. MCP: tools ek alag server mein, standard protocol se; koi bhi MCP client (Claude Desktop, Cursor, IDE) bina naya code likhe use kar sakta hai. MCP andar se function calling hi use karta hai.
23. MCP server mein auth kaise? Local stdio: process user ki machine pe hai, env mein API key. Remote HTTP: HTTPS + OAuth (MCP auth spec) ya bearer token, server har tool call pe user ke permissions check kare, read-only aur write tools alag, write pe confirmation.
24. Hit rate @6 ka matlab? 100 sawaalon mein se kitne sawaalon ke liye sahi chunk top 6 results mein tha. Mere RAG mein answer step top 6 padhta hai, isliye ye number seedha batata hai ki LLM ke paas sahi jaankari thi ya nahi.
25. Eval mein kya badla aur kyun? Chunk size 150/300/600 try kiye, 300 best (MRR 0.89). Hinglish kamzor mila (Hit@1 50%), to query rewriting naapi: Hit@6 96% → 100%. Do queries ko milana (RRF) try kiya, fayda nahi, to chhod diya. Ek waqt pe ek cheez badli.
