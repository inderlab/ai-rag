from langgraph.graph import END, START, StateGraph

from app.agents.router import route
from app.agents.state import AgentState
from app.config import settings
from app.llm.base import LLMProvider
from app.services import rag

ROUTES = {
    "qa": "retriever",
    "search_library": "retriever",
    "summary": "retriever",
    "quiz": "retriever",
}


def build_graph(llm: LLMProvider):
    def router_node(state: AgentState) -> dict:
        return route(llm, state)

    def retriever_node(state: AgentState) -> dict:
        query = state.get("search_query") or state["question"]
        video_id = None if state.get("intent") == "search_library" else state.get("video_id")
        hits = rag.retrieve(query, video_id, state.get("k") or settings.SEARCH_K)
        return {"chunks": hits, "steps": [f"retriever:{len(hits)}"]}

    def answer_node(state: AgentState) -> dict:
        answer = rag.generate(llm, state["question"], state.get("chunks", []), state.get("history"))
        return {
            "answer": answer.text,
            "citations": answer.citations,
            "found": answer.found,
            "steps": ["answer"],
            "input_tokens": answer.input_tokens,
            "output_tokens": answer.output_tokens,
        }

    graph = StateGraph(AgentState)
    graph.add_node("router", router_node)
    graph.add_node("retriever", retriever_node)
    graph.add_node("answer", answer_node)
    graph.add_edge(START, "router")
    graph.add_conditional_edges(
        "router",
        lambda s: s["intent"],
        {
            "qa": "retriever",
            "search_library": "retriever",
            "summary": "retriever",
            "quiz": "retriever",
        },
    )
    graph.add_edge("retriever", "answer")
    graph.add_edge("answer", END)
    return graph.compile()


def run(llm: LLMProvider, question: str, video_id: int | None, **kwargs) -> AgentState:
    state: AgentState = {
        "question": question,
        "video_id": video_id,
        "history": kwargs.get("history") or [],
        "k": kwargs.get("k") or settings.SEARCH_K,
        "retries": 0,
        "steps": [],
        "input_tokens": 0,
        "output_tokens": 0,
    }
    return build_graph(llm).invoke(state)
