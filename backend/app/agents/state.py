import operator
from typing import Annotated, Literal, TypedDict

from app.vectorstore.chroma_store import Hit

Intent = Literal["qa", "summary", "search_library", "quiz"]


class AgentState(TypedDict, total=False):
    question: str
    video_id: int | None
    history: list[dict]
    k: int
    intent: Intent
    route_reason: str
    search_query: str
    chunks: list[Hit]
    answer: str
    citations: list[str]
    found: bool
    retries: int
    verified: bool
    verify_notes: list[str]
    extra: dict
    steps: Annotated[list[str], operator.add]
    input_tokens: Annotated[int, operator.add]
    output_tokens: Annotated[int, operator.add]
