from pydantic import BaseModel

from app.agents.state import AgentState, Intent
from app.llm.base import LLMProvider
from app.llm.prompts import ROUTER_SYSTEM

NEEDS_VIDEO: set[str] = {"qa", "summary", "quiz"}


class RouteDecision(BaseModel):
    intent: Intent
    reason: str
    search_query: str


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
    if not has_video and intent in NEEDS_VIDEO:
        intent, reason = "search_library", f"{reason} (no video open, searching library)"
    query = result.data.search_query.strip() or state["question"]
    return {
        "intent": intent,
        "route_reason": reason,
        "search_query": query,
        "steps": [f"router:{intent}"],
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
    }
