import os
import sys
import time

from dotenv import load_dotenv

sys.path.insert(0, "backend")
load_dotenv("backend/.env")

TOPIC = "Kafka"
QUESTION = "Few-shot prompting kya hai? 2 line mein Hinglish mein."


def available() -> list[str]:
    names = []
    if os.getenv("OPENAI_API_KEY"):
        names.append("openai")
    if os.getenv("ANTHROPIC_API_KEY"):
        names.append("claude")
    return names


def provider_compare(names: list[str]) -> None:
    from app.llm.factory import get_llm

    print("\n=== 1. OpenAI vs Claude ===")
    for name in names:
        llm = get_llm(name)
        start = time.perf_counter()
        r = llm.complete("You are a friendly teacher.", [{"role": "user", "content": QUESTION}])
        ms = int((time.perf_counter() - start) * 1000)
        print(f"\n[{name} | {llm.model} | {ms} ms | in={r.input_tokens} out={r.output_tokens}]")
        print(r.text)


def style_compare(name: str) -> None:
    from app.llm.factory import get_llm
    from app.llm.prompts import STYLES, build_prompt

    print(f"\n=== 2. Bad vs good vs few-shot ({name}) ===")
    llm = get_llm(name)
    for style in STYLES:
        system, messages = build_prompt(style, TOPIC)
        r = llm.complete(system, messages, temperature=0.2)
        print(f"\n[{style} | in={r.input_tokens} out={r.output_tokens}]")
        print(r.text)


def streaming(name: str) -> None:
    from app.llm.factory import get_llm

    print(f"\n=== 3. Streaming ({name}) ===\n")
    llm = get_llm(name)
    start = time.perf_counter()
    first = None
    for token in llm.stream("You are a friendly teacher.", [{"role": "user", "content": QUESTION}]):
        if first is None:
            first = int((time.perf_counter() - start) * 1000)
        print(token, end="", flush=True)
    total = int((time.perf_counter() - start) * 1000)
    print(f"\n\n[first token {first} ms | total {total} ms]")


if __name__ == "__main__":
    names = available()
    if not names:
        sys.exit("Add OPENAI_API_KEY or ANTHROPIC_API_KEY to backend/.env first.")
    provider_compare(names)
    style_compare(names[0])
    streaming(names[0])
