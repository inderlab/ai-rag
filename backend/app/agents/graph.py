from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

from app.agents import specialists, verifier
from app.agents.router import route
from app.agents.state import AgentState
from app.config import settings
from app.llm.base import LLMProvider
from app.services import rag

ROUTES = {
    "qa": "retriever",
    "search_library": "library_search",
    "summary": "summarizer",
    "quiz": "quiz",
}


def build_graph(llm: LLMProvider, stream: bool = False):
    def router_node(state: AgentState) -> dict:
        return route(llm, state)

    def retriever_node(state: AgentState) -> dict:
        query = state.get("search_query") or state["question"]
        hits = rag.retrieve(query, state.get("video_id"), state.get("k") or settings.SEARCH_K)
        return {"chunks": hits, "steps": [f"retriever:{len(hits)}"]}

    def library_node(state: AgentState) -> dict:
        query = state.get("search_query") or state["question"]
        hits = rag.retrieve(query, None, state.get("k") or settings.SEARCH_K, state.get("user_id"))
        videos = len({h.video_id for h in hits})
        return {"chunks": hits, "steps": [f"library_search:{len(hits)}/{videos}"]}

    def answer_node(state: AgentState) -> dict:
        notes = state.get("verify_notes") or []
        on_token = None
        if stream:
            writer = get_stream_writer()
            if notes:
                writer({"retry": notes})

            def on_token(piece: str) -> None:
                writer({"token": piece})

        answer = rag.generate(
            llm,
            state["question"],
            state.get("chunks", []),
            state.get("history"),
            feedback=" ".join(notes) or None,
            on_token=on_token,
            library=state.get("intent") == "search_library",
        )
        return {
            "answer": answer.text,
            "citations": answer.citations,
            "found": answer.found,
            "steps": ["answer:retry" if notes else "answer"],
            "input_tokens": answer.input_tokens,
            "output_tokens": answer.output_tokens,
        }

    def summarizer_node(state: AgentState) -> dict:
        return specialists.summarize(llm, state)

    def quiz_node(state: AgentState) -> dict:
        return specialists.make_quiz(llm, state)

    graph = StateGraph(AgentState)
    graph.add_node("router", router_node)
    graph.add_node("retriever", retriever_node)
    graph.add_node("library_search", library_node)
    graph.add_node("answer", answer_node)
    graph.add_node("verifier", verifier.verify)
    graph.add_node("summarizer", summarizer_node)
    graph.add_node("quiz", quiz_node)

    graph.add_edge(START, "router")
    graph.add_conditional_edges("router", lambda s: s["intent"], ROUTES)
    graph.add_edge("retriever", "answer")
    graph.add_edge("library_search", "answer")
    graph.add_edge("answer", "verifier")
    graph.add_conditional_edges("verifier", verifier.next_step, {"retry": "answer", "done": END})
    graph.add_edge("summarizer", END)
    graph.add_edge("quiz", END)
    return graph.compile()


def initial_state(question: str, video_id: int | None, **kwargs) -> AgentState:
    return {
        "question": question,
        "video_id": video_id,
        "user_id": kwargs.get("user_id"),
        "history": kwargs.get("history") or [],
        "k": kwargs.get("k") or settings.SEARCH_K,
        "retries": 0,
        "verify_notes": [],
        "extra": {},
        "steps": [],
        "input_tokens": 0,
        "output_tokens": 0,
    }


def run(llm: LLMProvider, question: str, video_id: int | None, **kwargs) -> AgentState:
    return build_graph(llm).invoke(initial_state(question, video_id, **kwargs))


def stream(llm: LLMProvider, question: str, video_id: int | None, **kwargs):
    app = build_graph(llm, stream=True)
    final: dict = dict(initial_state(question, video_id, **kwargs))
    for mode, chunk in app.stream(final, stream_mode=["updates", "custom"]):
        if mode == "custom":
            yield "custom", chunk
            continue
        for node, update in chunk.items():
            for key, value in (update or {}).items():
                if key in ("steps", "input_tokens", "output_tokens"):
                    final[key] = final.get(key, [] if key == "steps" else 0) + value
                else:
                    final[key] = value
            yield "node", {"node": node, "steps": (update or {}).get("steps", [])}
    yield "final", final
