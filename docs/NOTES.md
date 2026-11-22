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
