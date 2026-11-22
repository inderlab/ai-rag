import json
import sys

sys.path.insert(0, "backend")

FAKE_WEATHER = {
    "delhi": {"temp_c": 31, "sky": "haze"},
    "mumbai": {"temp_c": 29, "sky": "humid, light rain"},
    "shimla": {"temp_c": 9, "sky": "clear and cold"},
}

TOOLS = [
    {
        "name": "get_weather",
        "description": "Get today's weather for an Indian city. Returns temperature in C and sky.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {"city": {"type": "string", "description": "City name, e.g. Delhi"}},
            "required": ["city"],
            "additionalProperties": False,
        },
    }
]


def get_weather(city: str) -> dict:
    data = FAKE_WEATHER.get(city.strip().lower())
    if data is None:
        raise ValueError(f"No weather data for '{city}'")
    return {"city": city, **data}


def run_tool(name: str, args: dict) -> tuple[str, bool]:
    try:
        if name == "get_weather":
            return json.dumps(get_weather(**args)), False
        return f"Unknown tool {name}", True
    except (ValueError, TypeError) as e:
        return f"Error: {e}", True


def ask_with_tools(question: str) -> None:
    import anthropic
    from app.config import settings

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    messages = [{"role": "user", "content": question}]
    print(f"\nUSER: {question}")
    for step in range(1, 6):
        resp = client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=4000,
            output_config={"effort": "low"},
            tools=TOOLS,
            messages=messages,
        )
        calls = [b for b in resp.content if b.type == "tool_use"]
        if resp.stop_reason != "tool_use" or not calls:
            text = "".join(b.text for b in resp.content if b.type == "text")
            print(f"CLAUDE (step {step}, stop={resp.stop_reason}): {text}")
            return
        messages.append({"role": "assistant", "content": resp.content})
        results = []
        for call in calls:
            output, is_error = run_tool(call.name, call.input)
            print(f"  step {step}: model asked {call.name}({call.input}) -> my code ran it -> {output}")
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": call.id,
                    "content": output,
                    "is_error": is_error,
                }
            )
        messages.append({"role": "user", "content": results})


def structured_demo() -> None:
    from app.llm.factory import get_llm
    from pydantic import BaseModel

    class Recipe(BaseModel):
        dish: str
        minutes: int
        ingredients: list[str]
        vegetarian: bool

    llm = get_llm()
    result = llm.structured(
        "Extract the recipe as structured data.",
        [{"role": "user", "content": "Paneer bhurji 15 min mein: paneer, pyaaz, tamatar, mirch."}],
        Recipe,
    )
    print("\n=== Structured output (Pydantic schema) ===")
    print(repr(result.data))
    print(f"type: {type(result.data).__name__}, tokens {result.input_tokens}+{result.output_tokens}")


def main() -> None:
    print("=== Tool calling: model decides, my code runs the tool ===")
    ask_with_tools("Delhi ka mausam kaisa hai?")
    ask_with_tools("Mumbai aur Shimla mein se kahan zyada thand hai?")
    ask_with_tools("Paris ka mausam?")
    ask_with_tools("2 + 2 kitna hota hai?")
    structured_demo()


if __name__ == "__main__":
    main()
