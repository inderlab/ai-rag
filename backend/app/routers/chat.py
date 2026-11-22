import json
import logging
import time
from collections.abc import Iterator
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents import graph
from app.config import settings
from app.db import get_db
from app.ingestion.youtube import fmt_ts
from app.llm.base import LLMProvider
from app.llm.factory import get_llm
from app.models import Video
from app.services import rag
from app.services.transcripts import ready_video

log = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

DbSession = Annotated[Session, Depends(get_db)]


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    video_id: int | None = None
    k: int = Field(settings.SEARCH_K, ge=1, le=20)
    provider: str | None = None
    history: list[HistoryMessage] = Field(default_factory=list, max_length=20)


class Citation(BaseModel):
    timestamp: str
    seconds: int


class Source(BaseModel):
    video_id: int
    title: str
    timestamp: str
    end_timestamp: str
    start: float
    end: float
    score: float
    text: str


class ChatResponse(BaseModel):
    question: str
    video_id: int | None
    answer: str
    found: bool
    citations: list[Citation]
    sources: list[Source]
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    retrieval_ms: int
    llm_ms: int


class AgentChatResponse(ChatResponse):
    intent: str
    route_reason: str
    search_query: str
    steps: list[str]
    verified: bool
    verify_notes: list[str]
    quiz: dict[str, Any] | None = None
    latency_ms: int


class CompareRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    video_id: int
    provider: str | None = None


class CompareSide(BaseModel):
    answer: str
    citations: list[Citation]
    input_tokens: int
    output_tokens: int
    latency_ms: int


class CompareResponse(BaseModel):
    question: str
    title: str
    without_rag: CompareSide
    with_rag: CompareSide


def resolve(provider: str | None) -> LLMProvider:
    try:
        return get_llm(provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


def check_video(session: Session, video_id: int | None) -> Video | None:
    return ready_video(session, video_id) if video_id is not None else None


def citations(answer: rag.Answer) -> list[Citation]:
    return [Citation(timestamp=t, seconds=rag.to_seconds(t)) for t in answer.citations]


def sources(answer: rag.Answer) -> list[Source]:
    return [
        Source(
            video_id=h.video_id,
            title=h.title,
            timestamp=fmt_ts(h.start),
            end_timestamp=fmt_ts(h.end),
            start=h.start,
            end=h.end,
            score=h.score,
            text=h.text,
        )
        for h in answer.sources
    ]


def to_response(body: ChatRequest, answer: rag.Answer) -> ChatResponse:
    return ChatResponse(
        question=body.question,
        video_id=body.video_id,
        answer=answer.text,
        found=answer.found,
        citations=citations(answer),
        sources=sources(answer),
        provider=answer.provider,
        model=answer.model,
        input_tokens=answer.input_tokens,
        output_tokens=answer.output_tokens,
        retrieval_ms=answer.extra.get("retrieval_ms", 0),
        llm_ms=answer.latency_ms,
    )


def side(answer: rag.Answer) -> CompareSide:
    return CompareSide(
        answer=answer.text,
        citations=citations(answer),
        input_tokens=answer.input_tokens,
        output_tokens=answer.output_tokens,
        latency_ms=answer.latency_ms,
    )


def from_state(body: ChatRequest, llm: LLMProvider, state: dict, latency: int) -> AgentChatResponse:
    answer = rag.Answer(
        text=state.get("answer", ""),
        citations=state.get("citations", []),
        sources=state.get("chunks", []),
        provider=llm.name,
        model=llm.model,
        found=state.get("found", True),
    )
    return AgentChatResponse(
        question=body.question,
        video_id=body.video_id,
        answer=answer.text,
        found=answer.found,
        citations=citations(answer),
        sources=sources(answer),
        provider=llm.name,
        model=llm.model,
        input_tokens=state.get("input_tokens", 0),
        output_tokens=state.get("output_tokens", 0),
        retrieval_ms=0,
        llm_ms=0,
        intent=state.get("intent", ""),
        route_reason=state.get("route_reason", ""),
        search_query=state.get("search_query", ""),
        steps=state.get("steps", []),
        verified=state.get("verified", False),
        verify_notes=state.get("verify_notes", []),
        quiz=(state.get("extra") or {}).get("quiz"),
        latency_ms=latency,
    )


def history_of(body: ChatRequest) -> list[dict]:
    return [m.model_dump() for m in body.history]


def sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("", response_model=AgentChatResponse)
def chat(body: ChatRequest, session: DbSession) -> AgentChatResponse:
    check_video(session, body.video_id)
    llm = resolve(body.provider)
    start = time.perf_counter()
    try:
        state = graph.run(llm, body.question, body.video_id, k=body.k, history=history_of(body))
    except Exception as e:
        log.exception("agent chat failed with %s", llm.name)
        raise HTTPException(status_code=502, detail=f"{llm.name} call failed: {e}") from e
    return from_state(body, llm, state, int((time.perf_counter() - start) * 1000))


@router.post("/stream")
def chat_stream(body: ChatRequest, session: DbSession) -> StreamingResponse:
    check_video(session, body.video_id)
    llm = resolve(body.provider)

    def events() -> Iterator[str]:
        start = time.perf_counter()
        yield sse({"type": "start", "provider": llm.name, "model": llm.model})
        try:
            for kind, data in graph.stream(
                llm, body.question, body.video_id, k=body.k, history=history_of(body)
            ):
                if kind == "custom" and "token" in data:
                    yield sse({"type": "token", "text": data["token"]})
                elif kind == "custom" and "retry" in data:
                    yield sse({"type": "retry", "notes": data["retry"]})
                elif kind == "node":
                    yield sse({"type": "step", **data})
                elif kind == "final":
                    latency = int((time.perf_counter() - start) * 1000)
                    final = from_state(body, llm, data, latency)
                    yield sse({"type": "done", "result": final.model_dump()})
        except Exception as e:
            log.exception("agent stream failed with %s", llm.name)
            yield sse({"type": "error", "detail": f"{llm.name} call failed: {e}"})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/rag", response_model=ChatResponse)
def chat_rag(body: ChatRequest, session: DbSession) -> ChatResponse:
    check_video(session, body.video_id)
    llm = resolve(body.provider)
    try:
        answer = rag.ask(
            llm,
            body.question,
            body.video_id,
            body.k,
            [m.model_dump() for m in body.history],
        )
    except Exception as e:
        log.exception("chat failed with %s", llm.name)
        raise HTTPException(status_code=502, detail=f"{llm.name} call failed: {e}") from e
    return to_response(body, answer)


@router.post("/compare", response_model=CompareResponse)
def compare(body: CompareRequest, session: DbSession) -> CompareResponse:
    video = ready_video(session, body.video_id)
    llm = resolve(body.provider)
    try:
        without = rag.ask_without_rag(llm, body.question, video.title or video.youtube_id)
        with_rag = rag.ask(llm, body.question, video.id)
    except Exception as e:
        log.exception("chat failed with %s", llm.name)
        raise HTTPException(status_code=502, detail=f"{llm.name} call failed: {e}") from e
    return CompareResponse(
        question=body.question,
        title=video.title or "",
        without_rag=side(without),
        with_rag=side(with_rag),
    )
