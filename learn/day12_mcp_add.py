import sys

import anyio
from mcp import Client
from mcp.server.mcpserver import MCPServer

server = MCPServer(name="calculator", log_level="WARNING")


@server.tool(description="Add two numbers.")
def add(a: float, b: float) -> float:
    return a + b


@server.tool(description="Multiply two numbers.")
def multiply(a: float, b: float) -> float:
    return a * b


async def demo() -> None:
    async with Client(server) as client:
        tools = (await client.list_tools()).tools
        print("=== Tools the AI app will see ===")
        for t in tools:
            print(f"- {t.name}: {t.description}  schema={t.input_schema['properties']}")
        print("\n=== Calling them like Claude Desktop would ===")
        for name, args in [("add", {"a": 2, "b": 3}), ("multiply", {"a": 2.5, "b": 4})]:
            result = await client.call_tool(name, args)
            print(f"{name}({args}) -> {result.content[0].text}")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        anyio.run(demo)
    else:
        server.run("stdio")
