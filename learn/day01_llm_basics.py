"""
Day 1 practice: talk to an LLM through the API.

Run from repo root:
    source backend/.venv/bin/activate
    python learn/day01_llm_basics.py

Needs OPENAI_API_KEY or ANTHROPIC_API_KEY in backend/.env
"""

import os
import sys
import time

from dotenv import load_dotenv

load_dotenv("backend/.env")

QUESTION = "Spring Boot kya hai? 2 line mein Hinglish mein batao."
SYSTEM = "You are a friendly programming teacher."


def ask_openai(temperature: float) -> None:
    from openai import OpenAI

    client = OpenAI()
    t0 = time.perf_counter()
    r = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=temperature,
        messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": QUESTION}],
    )
    ms = int((time.perf_counter() - t0) * 1000)
    print(f"\n[openai | temp={temperature} | {ms} ms | tokens={r.usage.total_tokens}]")
    print(r.choices[0].message.content)


def ask_claude(temperature: float) -> None:
    import anthropic

    client = anthropic.Anthropic()
    t0 = time.perf_counter()
    r = client.messages.create(
        model=os.getenv("CLAUDE_MODEL", "claude-haiku-5-5"),
        max_tokens=300,
        temperature=temperature,
        system=SYSTEM,
        messages=[{"role": "user", "content": QUESTION}],
    )
    ms = int((time.perf_counter() - t0) * 1000)
    used = r.usage.input_tokens + r.usage.output_tokens
    print(f"\n[claude | temp={temperature} | {ms} ms | tokens={used}]")
    print(r.content[0].text)


if __name__ == "__main__":
    if os.getenv("OPENAI_API_KEY"):
        for t in (0.0, 1.0):
            ask_openai(t)
    if os.getenv("ANTHROPIC_API_KEY"):
        for t in (0.0, 1.0):
            ask_claude(t)
    if not (os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")):
        sys.exit("Add an API key to backend/.env first.")

    # TODO (me): run 3 times, note how temp 0 vs 1 answers change -> docs/NOTES.md
