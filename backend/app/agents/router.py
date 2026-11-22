from pydantic import BaseModel

from app.agents.state import AgentState, Intent
from app.llm.base import LLMProvider
from app.llm.prompts import ROUTER_SYSTEM

NEEDS_VIDEO: set[str] = {"summary", "quiz"}


class RouteDecision(BaseModel):
    intent: Intent
    reason: str


def route(llm: LLMProvider, state: AgentState) -> dict:
    has_video = state.get("video_id") is not None
    context = "A video is open." if has_video else "No video is open, only the library."
    result = llm.structured(
        ROUTER_SYSTEM,
        [{"role": "user", "content": f"{context}\nMessage: {state['question']}"}],
        RouteDecision,
    )
    intent = result.data.intent
    reason = result.data.reason
    if not has_video and intent in NEEDS_VIDEO | {"qa"}:
        intent, reason = "search_library", f"{reason} (no video open, searching library)"
    return {
        "intent": intent,
        "route_reason": reason,
        "steps": [f"router:{intent}"],
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
    }
