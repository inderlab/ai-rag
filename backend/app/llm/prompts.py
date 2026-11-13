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
