import re
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph


class State(TypedDict, total=False):
    question: str
    kind: Literal["math", "general"]
    answer: str


def classify(state: State) -> dict:
    kind = "math" if re.fullmatch(r"[\d\s+\-*/().]+", state["question"]) else "general"
    print(f"  [classify] state in = {dict(state)} -> kind={kind}")
    return {"kind": kind}


def math_answer(state: State) -> dict:
    allowed = re.fullmatch(r"[\d\s+\-*/().]+", state["question"])
    result = eval(state["question"], {"__builtins__": {}}) if allowed else "?"
    print(f"  [math]     calculating {state['question']}")
    return {"answer": f"{state['question'].strip()} = {result}"}


def general_answer(state: State) -> dict:
    print("  [general]  would call the LLM here")
    return {"answer": f"(LLM jawab dega) {state['question']}"}


def build():
    graph = StateGraph(State)
    graph.add_node("classify", classify)
    graph.add_node("math", math_answer)
    graph.add_node("general", general_answer)
    graph.add_edge(START, "classify")
    graph.add_conditional_edges(
        "classify", lambda s: s["kind"], {"math": "math", "general": "general"}
    )
    graph.add_edge("math", END)
    graph.add_edge("general", END)
    return graph.compile()


def main() -> None:
    app = build()
    print("=== Graph (mermaid) ===")
    print(app.get_graph().draw_mermaid())
    for q in ["12 * (3 + 4)", "Docker kya hai?"]:
        print(f"\nQuestion: {q}")
        final = app.invoke({"question": q})
        print(f"  final state = {final}")


if __name__ == "__main__":
    main()
