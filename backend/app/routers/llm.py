import time
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.llm.base import LLMProvider, LLMResult
from app.llm.claude_provider import ClaudeProvider
from app.llm.factory import SUPPORTED, get_llm
from app.llm.openai_provider import OpenAIProvider

router = APIRouter(prefix="/llm", tags=["llm"])

PROVIDER_CLASSES = {"openai": OpenAIProvider, "claude": ClaudeProvider}

DEFAULT_SYSTEM = "You are a helpful teacher. Answer in Hinglish. Keep answers short."


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class ProviderInfo(BaseModel):
    name: str
    model: str
    configured: bool
    default: bool
    supports_temperature: bool


class LLMTestRequest(BaseModel):
    prompt: str = "Explain what RAG is in two short lines."
    provider: str | None = None
    temperature: float = Field(0.2, ge=0, le=1)


class LLMTestResponse(BaseModel):
    provider: str
    model: str
    answer: str
    latency_ms: int
    temperature: float
    input_tokens: int
    output_tokens: int


class ChatRequest(BaseModel):
    messages: list[Message] = Field(min_length=1)
    system: str = DEFAULT_SYSTEM
    provider: str | None = None
    temperature: float = Field(0.2, ge=0, le=1)


class ChatResponse(LLMTestResponse):
    messages: list[Message]


class TemperatureRequest(BaseModel):
    prompt: str = "Spring Boot kya hai, 2 line mein?"
    provider: str | None = None
    temperatures: list[float] = Field(default=[0.0, 1.0], min_length=1, max_length=3)
    runs: int = Field(3, ge=1, le=3)


class TemperatureRun(BaseModel):
    temperature: float
    run: int
    answer: str
    output_tokens: int


class TemperatureResponse(BaseModel):
    provider: str
    model: str
    prompt: str
    results: list[TemperatureRun]
    identical_by_temperature: dict[str, bool]
    temperature_supported: bool


def resolve(provider: str | None) -> LLMProvider:
    try:
        return get_llm(provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


def call(
    llm: LLMProvider, system: str, messages: list[dict], temperature: float
) -> tuple[LLMResult, int]:
    start = time.perf_counter()
    try:
        result = llm.complete(system=system, messages=messages, temperature=temperature)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"{llm.name} call failed: {e}") from e
    return result, int((time.perf_counter() - start) * 1000)


@router.get("/providers", response_model=list[ProviderInfo])
def list_providers() -> list[ProviderInfo]:
    keys = {"openai": settings.OPENAI_API_KEY, "claude": settings.ANTHROPIC_API_KEY}
    models = {"openai": settings.OPENAI_MODEL, "claude": settings.CLAUDE_MODEL}
    return [
        ProviderInfo(
            name=name,
            model=models[name],
            configured=bool(keys[name]),
            default=name == settings.LLM_PROVIDER.lower(),
            supports_temperature=PROVIDER_CLASSES[name].supports_temperature,
        )
        for name in SUPPORTED
    ]


@router.post("/test", response_model=LLMTestResponse)
def test_llm(body: LLMTestRequest) -> LLMTestResponse:
    llm = resolve(body.provider)
    result, latency = call(
        llm, DEFAULT_SYSTEM, [{"role": "user", "content": body.prompt}], body.temperature
    )
    return LLMTestResponse(
        provider=llm.name,
        model=llm.model,
        answer=result.text,
        latency_ms=latency,
        temperature=body.temperature,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
    )


@router.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest) -> ChatResponse:
    if body.messages[-1].role != "user":
        raise HTTPException(status_code=400, detail="Last message must be from the user")
    llm = resolve(body.provider)
    history = [m.model_dump() for m in body.messages]
    result, latency = call(llm, body.system, history, body.temperature)
    return ChatResponse(
        provider=llm.name,
        model=llm.model,
        answer=result.text,
        latency_ms=latency,
        temperature=body.temperature,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        messages=[*body.messages, Message(role="assistant", content=result.text)],
    )


@router.post("/temperature", response_model=TemperatureResponse)
def compare_temperature(body: TemperatureRequest) -> TemperatureResponse:
    for t in body.temperatures:
        if not 0 <= t <= 1:
            raise HTTPException(status_code=400, detail="Temperatures must be between 0 and 1")
    llm = resolve(body.provider)
    messages = [{"role": "user", "content": body.prompt}]
    results: list[TemperatureRun] = []
    for t in body.temperatures:
        for i in range(1, body.runs + 1):
            result, _ = call(llm, DEFAULT_SYSTEM, messages, t)
            results.append(
                TemperatureRun(
                    temperature=t, run=i, answer=result.text, output_tokens=result.output_tokens
                )
            )
    identical = {
        str(t): len({r.answer for r in results if r.temperature == t}) == 1
        for t in body.temperatures
    }
    return TemperatureResponse(
        provider=llm.name,
        model=llm.model,
        prompt=body.prompt,
        results=results,
        identical_by_temperature=identical,
        temperature_supported=llm.supports_temperature,
    )
