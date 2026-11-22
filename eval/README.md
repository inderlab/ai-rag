# Eval

Measures how often retrieval finds the right moment, and how often the final answer cites it.

- `questions.json`: 28 questions (22 English, 6 Hinglish) on *[1hr Talk] Intro to Large Language Models* (`zjkBMFhNj_g`). Each has the `start`/`end` seconds where the transcript answers it, found by reading the transcript.
- `run_eval.py`: chunks the transcript at each size, embeds with the app's embedding model, ranks chunks by cosine (exact, same as Chroma on this size) and scores.
- `results/*.json`: full output of a run, including every answer.

## Metrics

- **Hit@k**: share of questions where a chunk overlapping the right time window is in the top k.
- **MRR**: average of 1 / rank of the first right chunk (1.0 = always first).
- **Right citation**: share of answers whose `[mm:ss]` points to a chunk that covers the right window (±30 s).

## Run

```bash
cd backend && source .venv/bin/activate
python ../eval/run_eval.py                                   # chunk sizes 150, 300, 600
python ../eval/run_eval.py --sizes 200,300,400 --k 1,3,6,10
python ../eval/run_eval.py --rewrite --provider claude       # + query rewriting + answers
EMBEDDING_MODEL=intfloat/multilingual-e5-base python ../eval/run_eval.py
```

It reads the transcript from the app database, or fetches captions with `--source youtube`.

## Results (2026-11-22, multilingual-e5-small)

**1. Chunk size** (overlap = 1/6 of the size)

| Chunk words | Overlap | Chunks | Hit@1 | Hit@3 | Hit@6 | MRR |
|---|---|---|---|---|---|---|
| 150 | 25 | 98 | 79% | 93% | 100% | 0.86 |
| **300** | 50 | 49 | **82%** | **96%** | 96% | **0.89** |
| 600 | 100 | 25 | 68% | 86% | 93% | 0.77 |

300 words has the best Hit@1 and MRR. 600 mixes topics in one vector and drops. 150 reaches 100% at k=6, but each chunk carries less context for the answer.

**2. Language** (300 words): English Hit@1 91%, MRR 0.95. Hinglish Hit@1 50%, Hit@6 83%, MRR 0.64. The small embedding model is weaker on Romanised Hindi.

**3. Query rewriting** (router's `search_query`, 300 words)

| Query | Lang | Hit@1 | Hit@6 | MRR |
|---|---|---|---|---|
| original | all | 82% | 96% | 0.89 |
| rewritten | all | 75-79% | **100%** | 0.84-0.86 |
| original + rewritten (RRF) | all | 79-82% | 96% | 0.85-0.88 |
| original | hi | 50% | 83% | 0.64 |
| rewritten | hi | 50% | **100%** | 0.64-0.65 |

Rewriting puts the right chunk in the top 6 for every question (the answer step reads all 6), at a small cost in Hit@1. Fusing both queries did not help. The app keeps the rewritten query. Ranges are over two runs, because the rewrite is done by an LLM.

**4. Answers** (Claude `claude-haiku-5-5`, 300 words, k=6): right citation 93-96% over two runs, about 2.3 s per answer, about 2,900 input + 300 output tokens per question. The misses were "how many GPUs/days" and the Hinglish cost question, where the right chunk was not retrieved, and the model correctly said NOT_FOUND instead of guessing.

## Next ideas

- Try `multilingual-e5-base` for Hinglish (bigger model, 768 dims).
- Hybrid search: add keyword (BM25) scores, good for numbers like "$2 million".
- A reranker on the top 20.
