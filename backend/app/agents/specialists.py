from pydantic import BaseModel

from app import db
from app.agents.state import AgentState
from app.llm.base import LLMProvider
from app.llm.prompts import QUIZ_SYSTEM
from app.models import Video
from app.services import insights as insights_service
from app.services.rag import TIMESTAMP, to_seconds
from app.services.transcripts import load_segments

QUIZ_MAX_WORDS = 8000


class QuizQuestion(BaseModel):
    question: str
    options: list[str]
    answer: int
    explanation: str
    timestamp: str


class Quiz(BaseModel):
    questions: list[QuizQuestion]
    notes: list[str]


def summarize(llm: LLMProvider, state: AgentState) -> dict:
    with db.SessionLocal() as session:
        video = session.get(Video, state["video_id"])
        existing = video.insights
        row = existing or insights_service.create_insights(session, video, llm)
        tokens = (0, 0) if existing else (row.input_tokens, row.output_tokens)
        lines = [f"**{row.title}**", "", row.summary, "", "**Chapters**"]
        lines += [f"- [{c['start']}] {c['title']}" for c in row.chapters]
        if row.key_points:
            lines += ["", "**Key points**"] + [f"- {p}" for p in row.key_points]
        citations = [c["start"] for c in row.chapters]
    return {
        "answer": "\n".join(lines),
        "citations": citations,
        "found": True,
        "verified": True,
        "steps": ["summarizer"],
        "input_tokens": tokens[0],
        "output_tokens": tokens[1],
    }


def spread(blocks: list, max_words: int) -> list:
    total = sum(b.word_count for b in blocks)
    if total <= max_words:
        return blocks
    ratio = max_words / total
    picked, acc = [], 1.0
    for b in blocks:
        acc += ratio
        if acc >= 1:
            picked.append(b)
            acc -= 1
    return picked


def clean_quiz(quiz: Quiz, duration: float | None) -> Quiz:
    questions = []
    for q in quiz.questions[:10]:
        if len(q.options) != 4 or not 0 <= q.answer < 4:
            continue
        ts = q.timestamp.strip("[] ")
        if not TIMESTAMP.fullmatch(f"[{ts}]") or (duration and to_seconds(ts) > duration):
            ts = ""
        questions.append(q.model_copy(update={"timestamp": ts}))
    return Quiz(questions=questions, notes=quiz.notes[:6])


def format_quiz(quiz: Quiz) -> str:
    lines = []
    for n, q in enumerate(quiz.questions, start=1):
        lines.append(f"**Q{n}. {q.question}**")
        lines += [f"{'abcd'[i]}) {opt}" for i, opt in enumerate(q.options)]
        where = f" [{q.timestamp}]" if q.timestamp else ""
        lines += [f"Answer: {'abcd'[q.answer]}) {q.explanation}{where}", ""]
    if quiz.notes:
        lines += ["**Notes**"] + [f"- {n}" for n in quiz.notes]
    return "\n".join(lines).strip()


def make_quiz(llm: LLMProvider, state: AgentState) -> dict:
    with db.SessionLocal() as session:
        video = session.get(Video, state["video_id"])
        blocks = insights_service.timed_blocks(load_segments(session, video))
        duration = video.duration_seconds
    text = insights_service.transcript_text(spread(blocks, QUIZ_MAX_WORDS))
    result = llm.structured(
        QUIZ_SYSTEM,
        [
            {
                "role": "user",
                "content": f"<transcript>\n{text}\n</transcript>\n\nRequest: {state['question']}",
            }
        ],
        Quiz,
    )
    quiz = clean_quiz(result.data, duration)
    return {
        "answer": format_quiz(quiz),
        "citations": [q.timestamp for q in quiz.questions if q.timestamp],
        "found": bool(quiz.questions),
        "verified": True,
        "extra": {"quiz": quiz.model_dump()},
        "steps": [f"quiz:{len(quiz.questions)}"],
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
    }
