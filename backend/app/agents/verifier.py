import re

from app.agents.state import AgentState
from app.services.rag import TIMESTAMP, to_seconds
from app.vectorstore.chroma_store import Hit

SLACK_SECONDS = 2.0
MAX_RETRIES = 1


def inside(seconds: int, hits: list[Hit]) -> bool:
    return any(h.start - SLACK_SECONDS <= seconds <= h.end + SLACK_SECONDS for h in hits)


def check(answer: str, citations: list[str], hits: list[Hit], found: bool) -> list[str]:
    if not found:
        return []
    problems = []
    bad = [ts for ts in citations if not inside(to_seconds(ts), hits)]
    if bad:
        problems.append(
            "these timestamps are not inside any excerpt: "
            + ", ".join(f"[{b}]" for b in bad)
            + ". Only use the start times written in the excerpt headers."
        )
    if not citations:
        problems.append("the answer has no [mm:ss] citation. Cite the excerpt start time.")
    return problems


def strip_bad(answer: str, hits: list[Hit]) -> tuple[str, list[str]]:
    kept: list[str] = []

    def keep(match) -> str:
        ts = match.group(1)
        if inside(to_seconds(ts), hits):
            if ts not in kept:
                kept.append(ts)
            return match.group(0)
        return ""

    cleaned = TIMESTAMP.sub(keep, answer)
    cleaned = re.sub(r" {2,}", " ", cleaned)
    return re.sub(r" ([.,;:])", r"\1", cleaned).strip(), kept


def verify(state: AgentState) -> dict:
    hits = state.get("chunks", [])
    problems = check(
        state.get("answer", ""), state.get("citations", []), hits, state.get("found", True)
    )
    retries = state.get("retries", 0)
    if not problems:
        return {"verified": True, "verify_notes": [], "steps": ["verifier:ok"]}
    if retries < MAX_RETRIES:
        return {
            "verified": False,
            "verify_notes": problems,
            "retries": retries + 1,
            "steps": ["verifier:retry"],
        }
    text, kept = strip_bad(state.get("answer", ""), hits)
    return {
        "verified": False,
        "verify_notes": problems,
        "answer": text,
        "citations": kept,
        "steps": ["verifier:failed"],
    }


def next_step(state: AgentState) -> str:
    return "retry" if state.get("steps", [""])[-1] == "verifier:retry" else "done"
