# Final self-test: 9 topics, 2 minutes each

Day 14 ka final test. Har topic ko bina dekhe whiteboard par 2 minute mein samjhao. Har jawab mein VidMind ka asli example aur number hai, taaki interview mein "maine banaya hai" bol sako.

Kaise practice karein: topic padho, kitab band karo, phone pe 2 minute ka timer lagao aur bol ke samjhao. Jo point bhool gaye, uske aage ✗ lagao aur kal sirf wahi dobara karo.

---

## 1. Token, context window, temperature

- **Token:** text ka chhota tukda (lagbhag 3/4 English word). Billing aur limits tokens mein hote hain. Hindi/Hinglish mein ek word ke zyada tokens bante hain.
- **Context window:** model ek baar mein kitne tokens dekh sakta hai (input + output). API stateless hai, isliye har request mein history khud bhejni padti hai.
- **Temperature:** randomness. Kam = same jawab baar baar (facts, RAG), zyada = creative.
- **VidMind mein:** RAG answer 0.2 temperature pe (OpenAI). Naya Claude API temperature nahi leta, wahan `output_config.effort` use hota hai. Har response mein `input_tokens` / `output_tokens` dikhte hain.
- **Trap question:** "Poori 1 ghante ki transcript prompt mein kyun nahi daal dete?" Cost aur latency badhti hai, aur beech ka content model miss karta hai (lost in the middle). Isliye RAG.

## 2. Embedding aur cosine similarity

- **Embedding:** text → numbers ki list (vector) jisme meaning chhupa hota hai. Same meaning = paas wale vectors.
- **Cosine similarity:** do vectors ke beech ka angle. 1 = same direction (same meaning), 0 = koi rishta nahi.
- **VidMind mein:** `multilingual-e5-small`, 384 dimensions, laptop pe local chalta hai. `query:` aur `passage:` prefix lagte hain. Hinglish sawaal English transcript se match ho jaata hai kyunki model multilingual hai.
- **Rule:** index aur query dono same model se banne chahiye. Isliye Chroma collection mein model ka naam save hai, mismatch pe `ModelMismatchError`.

## 3. Chunking aur overlap

- **Kyun:** ek caption line bahut chhoti hai (meaning kam), poori video bahut badi. Beech ka size chahiye.
- **Overlap:** do chunks ke beech kuch words common, taaki boundary pe kati baat dono mein rahe.
- **VidMind mein:** segment-aware chunker, 300 words + 50 overlap, har chunk ka start/end timestamp saath mein.
- **Eval ka saboot:** 150 words → Hit@1 79%, **300 → 82%**, 600 → 68%. Bade chunk mein meaning ghul jaata hai, chhote mein context kam.

## 4. Vector DB aur HNSW

- **Vector DB:** vectors + metadata store karta hai aur "sabse paas wale k" jaldi dhoondhta hai.
- **HNSW:** graph ki kai layers. Upar ki layer se lambi chhalang, neeche aate hue paas wale padosi. Approximate nearest neighbour, lakhon vectors pe bhi milliseconds.
- **VidMind mein:** ChromaDB (cosine). Metadata: `video_id`, `start`, `end`, `title`, `user_id`. Filter `user_id in [0, mera_id]`, taaki private upload sirf owner ko mile.
- **Follow-up:** "Scale kaise karoge?" Managed DB (Pinecone, Qdrant, pgvector), sharding, aur metadata filter pe index.

## 5. RAG ke 3 steps, hallucination kaise kam ki

1. **Retrieve:** sawaal ka embedding → top 6 chunks.
2. **Augment:** chunks ko `[mm:ss]` header ke saath prompt mein daalo.
3. **Generate:** model sirf us context se jawab de aur har fact ke saath timestamp de.

Hallucination kam karne ke tareeke (sab VidMind mein hain):
- System prompt: "sirf context se jawab do, nahi mila to NOT_FOUND bolo".
- Har fact pe `[mm:ss]` citation.
- **Verifier:** check karta hai ki har timestamp kisi retrieved chunk ke andar hai. Galat ho to ek baar retry, phir bhi galat to wo timestamp hata deta hai.
- Eval: 93-96% jawab sahi moment cite karte hain, aur retrieval miss ho to model guess nahi karta.

## 6. Structured output vs tool calling

- **Structured output:** model ka jawab ek fixed schema (Pydantic) mein aata hai. Use: data nikalna. VidMind: `VideoInsights` (title, summary, chapters, tags, key points), quiz MCQs, router ka `RouteDecision`.
- **Tool calling:** model bolta hai "ye function in arguments ke saath chalao", code chalata hai, result model ko wapas jaata hai. Use: model ko action ya live data chahiye.
- **Ek line mein:** structured output = "jawab is shape mein do", tool calling = "ye kaam karwao".
- **Code:** Claude `messages.parse(output_format=...)`, OpenAI `chat.completions.parse(response_format=...)`, dono ek `structured()` method ke peeche.

## 7. Multi-agent graph aur verifier

```
router ─┬─ qa ─────────► retriever ──┐
        ├─ search_library ► library ─┼► answer → verifier ─► END
        ├─ summary ─────► summarizer ─────────────► END   ▲ retry once
        └─ quiz ────────► quiz (MCQ) ─────────────► END
```

- **Router:** structured output se intent chunta hai aur Hinglish sawaal ko search-friendly English mein rewrite karta hai. Rewrite se Hit@6 96% → 100%.
- **State:** TypedDict. `steps` aur `tokens` reducers (`operator.add`) se jud-te hain, poora trace UI mein dikhta hai.
- **Verifier:** conditional edge. Galat timestamp → feedback ke saath answer node pe wapas (max 1 baar).
- **Streaming:** LangGraph `stream_mode=["updates", "custom"]` → SSE events `step`, `token`, `retry`, `done`.
- **Kyun graph, simple chain kyun nahi:** alag kaam ke liye alag raasta, retry loop, aur har step test ho sakta hai.

## 8. MCP kya hai aur mera server kya karta hai

- **MCP (Model Context Protocol):** AI apps (Claude Desktop, Cursor) ko tools aur data dene ka standard. Ek baar server banao, har MCP client use kar sakta hai. USB-C jaisa.
- **Mera server:** 5 tools: `list_videos`, `search_videos`, `ask_video`, `get_video_summary`, `ingest_youtube`. Ye FastAPI API ko call karta hai, apna logic dobara nahi likhta.
- **Transport:** stdio (Claude Desktop process start karta hai). Errors `ToolError` se saaf message ke saath jaate hain.
- **Demo line:** "Claude Desktop mein poochha 'is talk mein tokenizer kab samjhaya?', usne `search_videos` chalaya aur timestamp ke saath jawab diya."

## 9. Eval numbers aur kya improve kiya

- **Set:** 1 ghante ka talk, 28 sawaal (22 English, 6 Hinglish), har sawaal ke saath sahi time window.
- **Metrics:** Hit@k (top k mein sahi chunk aaya?), MRR (sahi chunk kitna upar aaya), citation accuracy.
- **Numbers:** 300 words chunk → Hit@1 82%, Hit@3 96%, MRR 0.89. Query rewrite → Hit@6 100% (Hinglish 83% → 100%). Answers: 93-96% sahi citation, ~2.3 s.
- **Kya try kiya jo kaam nahi aaya:** RRF fusion (original + rewritten query) se koi fayda nahi mila, isliye simple rewrite rakha. Ye bolna achha lagta hai: data dekh ke decide kiya.
- **Aage kya:** reranker (cross-encoder), Hinglish ke aur sawaal, OpenAI column bharna.

---

## Bonus: aaj ke naye topics

- **bcrypt:** salt + slow hash, leak ho to bhi crack karna mehenga.
- **JWT:** `header.payload.signature`, stateless. Nuksaan: expiry se pehle revoke mushkil.
- **Upload pipeline:** FFmpeg audio → `faster-whisper` (VAD ke saath) → wahi chunk → embed → index raasta.
- **Range request (206):** video seek karne pe sirf maanga hua hissa aata hai.

## 30 second pitch

"VidMind ek chat-with-video app hai. YouTube link do ya apni file upload karo, aur English, Hindi ya Hinglish mein sawaal poochho. Har jawab transcript se aata hai aur `[mm:ss]` timestamp ke saath, jis pe click karo to video wahi pahunch jaata hai. Peeche LangGraph ka multi-agent graph hai jisme ek verifier har timestamp check karta hai. Maine 28 sawaalon ka eval banaya: 82% sawaalon mein pehla result hi sahi, aur 93-96% jawab sahi moment cite karte hain. Ye FastAPI, ChromaDB, React aur Docker pe bana hai, aur MCP server se Claude Desktop bhi isse use kar sakta hai."
