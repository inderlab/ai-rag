import logging
import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents import graph
from app.db import get_db
from app.llm.factory import get_llm
from app.routers.chat import ChatRequest, Citation, Source, citations, sources
from app.services import rag
from app.services.transcripts import ready_video

log = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])

DbSession = Annotated[Session, Depends(get_db)]


class AgentResponse(BaseModel):
    question: str
    video_id: int | None
    intent: str
    route_reason: str
    steps: list[str]
    answer: str
    found: bool
    citations: list[Citation]
    sources: list[Source]
    input_tokens: int
    output_tokens: int
    latency_ms: int


def to_response(body: ChatRequest, state: dict, latency: int) -> AgentResponse:
    answer = rag.Answer(
        text=state.get("answer", ""),
        citations=state.get("citations", []),
        sources=state.get("chunks", []),
        provider="",
        model="",
    )
    return AgentResponse(
        question=body.question,
        video_id=body.video_id,
        intent=state.get("intent", ""),
        route_reason=state.get("route_reason", ""),
        steps=state.get("steps", []),
        answer=answer.text,
        found=state.get("found", True),
        citations=citations(answer),
        sources=sources(answer),
        input_tokens=state.get("input_tokens", 0),
        output_tokens=state.get("output_tokens", 0),
        latency_ms=latency,
    )


@router.post("/chat", response_model=AgentResponse)
def agent_chat(body: ChatRequest, session: DbSession) -> AgentResponse:
    if body.video_id is not None:
        ready_video(session, body.video_id)
    try:
        llm = get_llm(body.provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    start = time.perf_counter()
    try:
        state = graph.run(
            llm,
            body.question,
            body.video_id,
            k=body.k,
            history=[m.model_dump() for m in body.history],
        )
    except Exception as e:
        log.exception("agent failed with %s", llm.name)
        raise HTTPException(status_code=502, detail=f"{llm.name} call failed: {e}") from e
    return to_response(body, state, int((time.perf_counter() - start) * 1000))
