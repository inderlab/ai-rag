from typing import Literal

PromptStyle = Literal["bad", "good", "few_shot"]

STYLES: tuple[PromptStyle, ...] = ("bad", "good", "few_shot")

BAD_SYSTEM = "You are an assistant."

GOOD_SYSTEM = (
    "Role: You are a friendly programming teacher for Indian beginners.\n"
    "Task: Explain the given tech topic.\n"
    "Format: Exactly 3 bullet points. Each bullet under 15 words. Hinglish.\n"
    "Rules: No intro line, no outro line, no code."
)

FEW_SHOT_EXAMPLES: list[tuple[str, str]] = [
    (
        "Docker",
        "- Container tool hai, app ko packaged rakhta hai\n"
        "- Har machine pe same chalta hai\n"
        '- "Mere laptop pe chalta hai" problem khatam',
    ),
    (
        "Redis",
        "- In-memory database hai, RAM mein data rakhta hai\n"
        "- Bahut fast, cache ke liye best\n"
        "- Session aur rate limiting mein use hota hai",
    ),
]


def build_prompt(style: PromptStyle, topic: str) -> tuple[str, list[dict]]:
    if style == "bad":
        return BAD_SYSTEM, [{"role": "user", "content": f"{topic} batao"}]

    if style == "good":
        return GOOD_SYSTEM, [{"role": "user", "content": f"Topic: {topic}"}]

    messages: list[dict] = []
    for example_topic, example_answer in FEW_SHOT_EXAMPLES:
        messages.append({"role": "user", "content": f"Topic: {example_topic}"})
        messages.append({"role": "assistant", "content": example_answer})
    messages.append({"role": "user", "content": f"Topic: {topic}"})
    return GOOD_SYSTEM, messages


RAG_SYSTEM = """You are VidMind, an assistant that answers questions about videos.

Rules:
1. Answer ONLY from the transcript excerpts given inside <context>. Do not use outside knowledge.
2. After every fact, cite the excerpt it came from with its start time in square brackets,
   exactly as written in the excerpt header, for example [04:12] or [1:02:05].
3. If the excerpts do not contain the answer, reply with exactly: NOT_FOUND
4. Reply in the same language and style as the question (English, Hindi or Hinglish).
5. Keep it short: 2-5 sentences or a few bullet points."""

NO_RAG_SYSTEM = """You are a helpful assistant. Answer the question about the video named below
in 2-5 sentences."""

NOT_FOUND = "NOT_FOUND"
NOT_FOUND_REPLY = "Is video mein iska jawab nahi mila. Sawaal thoda badal ke poochho."


INSIGHTS_SYSTEM = """You turn a timestamped video transcript into structured insights.

Rules:
- title: a clear, specific title (max 80 characters), not clickbait.
- summary: 3-5 sentences covering the main ideas, in the transcript's language.
- chapters: 3-12 chapters in time order. The first starts at 00:00. Each start time must be
  one of the [mm:ss] or [h:mm:ss] markers in the transcript. Titles are 2-6 words.
- tags: 5-10 lowercase topic tags, no '#'.
- key_points: 3-6 short facts or takeaways from the video.
Use only what the transcript says."""

MERGE_SYSTEM = """You get partial insights from consecutive parts of one long video.
Merge them into one set of insights for the whole video, following the same rules:
one title, one 3-5 sentence summary, 3-12 chapters in time order using the given start times,
5-10 tags and 3-6 key points."""
