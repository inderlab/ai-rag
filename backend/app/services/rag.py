import logging
import re
import time
from dataclasses import dataclass, field

from app.config import settings
from app.ingestion.youtube import fmt_ts
from app.llm.base import LLMProvider
from app.llm.prompts import NO_RAG_SYSTEM, NOT_FOUND, NOT_FOUND_REPLY, RAG_SYSTEM
from app.vectorstore.chroma_store import Hit, get_store

log = logging.getLogger(__name__)

TIMESTAMP = re.compile(r"\[((?:\d{1,2}:)?\d{1,2}:\d{2})\]")
RAG_TEMPERATURE = 0.2


@dataclass
class Answer:
    text: str
    citations: list[str]
    sources: list[Hit]
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    found: bool = True
    extra: dict = field(default_factory=dict)


def to_seconds(ts: str) -> int:
    seconds = 0
    for part in ts.split(":"):
        seconds = seconds * 60 + int(part)
    return seconds


def find_citations(text: str) -> list[str]:
    seen: list[str] = []
    for ts in TIMESTAMP.findall(text):
        if ts not in seen:
            seen.append(ts)
    return seen


def build_context(hits: list[Hit]) -> str:
    blocks = []
    for hit in hits:
        header = f"[{fmt_ts(hit.start)}] (until {fmt_ts(hit.end)})"
        if hit.title:
            header += f" from video '{hit.title}'"
        blocks.append(f"{header}\n{hit.text}")
    return "<context>\n" + "\n\n".join(blocks) + "\n</context>"


def build_messages(question: str, hits: list[Hit], history: list[dict]) -> list[dict]:
    prompt = f"{build_context(hits)}\n\nQuestion: {question}"
    return [*history, {"role": "user", "content": prompt}]


def retrieve(question: str, video_id: int | None, k: int) -> list[Hit]:
    return get_store().search(question, video_id=video_id, k=k)


def generate(
    llm: LLMProvider, question: str, hits: list[Hit], history: list[dict] | None = None
) -> Answer:
    if not hits:
        return Answer(NOT_FOUND_REPLY, [], [], llm.name, llm.model, found=False)
    start = time.perf_counter()
    result = llm.complete(
        RAG_SYSTEM, build_messages(question, hits, history or []), RAG_TEMPERATURE
    )
    latency = int((time.perf_counter() - start) * 1000)
    log.info(
        "rag provider=%s model=%s in=%s out=%s ms=%s",
        llm.name,
        llm.model,
        result.input_tokens,
        result.output_tokens,
        latency,
    )
    found = NOT_FOUND not in result.text
    text = result.text.strip() if found else NOT_FOUND_REPLY
    return Answer(
        text=text,
        citations=find_citations(text),
        sources=hits,
        provider=llm.name,
        model=llm.model,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        latency_ms=latency,
        found=found,
    )


def ask(
    llm: LLMProvider,
    question: str,
    video_id: int | None = None,
    k: int | None = None,
    history: list[dict] | None = None,
) -> Answer:
    start = time.perf_counter()
    hits = retrieve(question, video_id, k or settings.SEARCH_K)
    retrieval_ms = int((time.perf_counter() - start) * 1000)
    answer = generate(llm, question, hits, history)
    answer.extra["retrieval_ms"] = retrieval_ms
    return answer


def ask_without_rag(llm: LLMProvider, question: str, title: str) -> Answer:
    start = time.perf_counter()
    result = llm.complete(
        NO_RAG_SYSTEM,
        [{"role": "user", "content": f"Video: {title}\nQuestion: {question}"}],
        RAG_TEMPERATURE,
    )
    return Answer(
        text=result.text.strip(),
        citations=find_citations(result.text),
        sources=[],
        provider=llm.name,
        model=llm.model,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        latency_ms=int((time.perf_counter() - start) * 1000),
    )
