"""
Standalone diagnostic — run this directly to see exactly what Tavily's
remote MCP server returns: whether the key is set, whether the connection
succeeds, and what the actual tool names are.

Run with:  python diagnose_tavily.py
"""
import asyncio
from config import TAVILY_API_KEY


async def main():
    print("TAVILY_API_KEY set:", bool(TAVILY_API_KEY))
    print("TAVILY_API_KEY length:", len(TAVILY_API_KEY or ""))
    print("TAVILY_API_KEY prefix:", (TAVILY_API_KEY or "")[:8])

    if not TAVILY_API_KEY:
        print("\n>>> TAVILY_API_KEY is empty. Set it in your .env file.")
        return

    from langchain_mcp_adapters.client import MultiServerMCPClient

    url = f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY}"
    client = MultiServerMCPClient(
        {"tavily": {"transport": "streamable_http", "url": url}}
    )

    try:
        tools = await client.get_tools()
    except Exception as e:
        print("\n>>> Connection/auth FAILED with exception:")
        print(repr(e))
        return

    print("\nTool names found:", [t.name for t in tools])

    search_tool = None
    for t in tools:
        if "search" in t.name.lower():
            search_tool = t
            break

    if not search_tool:
        print("\n>>> No search-like tool found in the list above.")
        return

    print(f"\nCalling '{search_tool.name}' with a live test query...")
    try:
        result = await search_tool.ainvoke({"query": "PEL Pakistan official website"})
        print("Raw result:")
        print(result)
    except Exception as e:
        print("\n>>> Tool call FAILED with exception:")
        print(repr(e))


if __name__ == "__main__":
    asyncio.run(main())
