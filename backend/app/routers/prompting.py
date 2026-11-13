import json
import time
from collections.abc import Iterator
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.llm.factory import SUPPORTED
from app.llm.prompts import STYLES, PromptStyle, build_prompt
from app.routers.llm import DEFAULT_SYSTEM, call, resolve

router = APIRouter(prefix="/llm", tags=["prompting"])


class StreamRequest(BaseModel):
    prompt: str = Field("RAG kya hai? 3 line mein samjhao.", min_length=1)
    system: str = DEFAULT_SYSTEM
    provider: str | None = None
    temperature: float = Field(0.2, ge=0, le=1)


class CompareRequest(BaseModel):
    prompt: str = Field("Few-shot prompting kya hai? 2 line mein.", min_length=1)
    system: str = DEFAULT_SYSTEM
    providers: list[str] = Field(default_factory=lambda: list(SUPPORTED), min_length=1)
    temperature: float = Field(0.2, ge=0, le=1)


class CompareResult(BaseModel):
    provider: str
    status: Literal["ok", "not_configured", "error"]
    model: str | None = None
    answer: str | None = None
    latency_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    error: str | None = None


class CompareResponse(BaseModel):
    prompt: str
    results: list[CompareResult]
    fastest: str | None


class PromptStylesRequest(BaseModel):
    topic: str = Field("Kafka", min_length=1, max_length=100)
    provider: str | None = None
    styles: list[PromptStyle] = Field(default_factory=lambda: list(STYLES), min_length=1)
    temperature: float = Field(0.2, ge=0, le=1)


class PromptStyleResult(BaseModel):
    style: PromptStyle
    system: str
    messages: list[dict]
    answer: str
    input_tokens: int
    output_tokens: int
    bullet_count: int


class PromptStylesResponse(BaseModel):
    provider: str
    model: str
    topic: str
    results: list[PromptStyleResult]


def sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/stream")
def stream(body: StreamRequest) -> StreamingResponse:
    llm = resolve(body.provider)
    messages = [{"role": "user", "content": body.prompt}]

    def events() -> Iterator[str]:
        start = time.perf_counter()
        first_token_ms: int | None = None
        count = 0
        yield sse({"type": "start", "provider": llm.name, "model": llm.model})
        try:
            for token in llm.stream(body.system, messages, body.temperature):
                if first_token_ms is None:
                    first_token_ms = int((time.perf_counter() - start) * 1000)
                count += 1
                yield sse({"type": "token", "text": token})
        except Exception as e:
            yield sse({"type": "error", "detail": f"{llm.name} stream failed: {e}"})
            return
        yield sse(
            {
                "type": "done",
                "chunks": count,
                "first_token_ms": first_token_ms,
                "total_ms": int((time.perf_counter() - start) * 1000),
            }
        )

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/compare", response_model=CompareResponse)
def compare(body: CompareRequest) -> CompareResponse:
    messages = [{"role": "user", "content": body.prompt}]
    results: list[CompareResult] = []
    for name in dict.fromkeys(p.lower() for p in body.providers):
        try:
            llm = resolve(name)
        except HTTPException as e:
            results.append(CompareResult(provider=name, status="not_configured", error=e.detail))
            continue
        try:
            result, latency = call(llm, body.system, messages, body.temperature)
        except HTTPException as e:
            results.append(CompareResult(provider=name, status="error", error=e.detail))
            continue
        results.append(
            CompareResult(
                provider=llm.name,
                status="ok",
                model=llm.model,
                answer=result.text,
                latency_ms=latency,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
            )
        )
    ok = [r for r in results if r.status == "ok"]
    fastest = min(ok, key=lambda r: r.latency_ms or 0).provider if ok else None
    return CompareResponse(prompt=body.prompt, results=results, fastest=fastest)


@router.post("/prompt-styles", response_model=PromptStylesResponse)
def prompt_styles(body: PromptStylesRequest) -> PromptStylesResponse:
    llm = resolve(body.provider)
    results: list[PromptStyleResult] = []
    for style in dict.fromkeys(body.styles):
        system, messages = build_prompt(style, body.topic)
        result, _ = call(llm, system, messages, body.temperature)
        bullets = sum(
            1 for line in result.text.splitlines() if line.strip().startswith(("-", "*", "•"))
        )
        results.append(
            PromptStyleResult(
                style=style,
                system=system,
                messages=messages,
                answer=result.text,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                bullet_count=bullets,
            )
        )
    return PromptStylesResponse(
        provider=llm.name, model=llm.model, topic=body.topic, results=results
    )
