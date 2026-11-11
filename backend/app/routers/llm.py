import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.llm.factory import get_llm

router = APIRouter(prefix="/llm", tags=["llm"])


class LLMTestRequest(BaseModel):
    prompt: str = "Explain what RAG is in two short lines."
    provider: str | None = None  # "openai" | "claude", falls back to .env


class LLMTestResponse(BaseModel):
    provider: str
    model: str
    answer: str
    latency_ms: int


@router.post("/test", response_model=LLMTestResponse)
def test_llm(body: LLMTestRequest) -> LLMTestResponse:
    try:
        llm = get_llm(body.provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    start = time.perf_counter()
    try:
        answer = llm.chat(
            system="You are a helpful assistant. Keep answers short.",
            messages=[{"role": "user", "content": body.prompt}],
        )
    except Exception as e:  # provider errors: bad key, rate limit, network
        raise HTTPException(status_code=502, detail=f"{llm.name} call failed: {e}") from e

    return LLMTestResponse(
        provider=llm.name,
        model=llm.model,
        answer=answer,
        latency_ms=int((time.perf_counter() - start) * 1000),
    )
