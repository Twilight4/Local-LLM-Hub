# /// script
# requires-python = ">=3.11"
# dependencies = ["qdrant-client>=1.12", "httpx", "python-dotenv", "mcp>=1.2"]
# ///
"""MCP server exposing `search-internal-docs` over stdio.

The agent calls this tool to search your indexed documents in Qdrant.
"""
from mcp.server.fastmcp import FastMCP

from common import COLLECTION, embed, ensure_collection, get_client

mcp = FastMCP("qdrant-internal-docs")


@mcp.tool(name="search-internal-docs",
          description="Search the internal documents knowledge base for passages "
                      "most relevant to the query. Returns top matching text with sources.")
def search_internal_docs(query: str, limit: int = 4) -> str:
    vec = embed([query])[0]
    client = get_client()
    ensure_collection(client)
    res = client.query_points(collection_name=COLLECTION, query=vec, limit=limit)
    if not res.points:
        return "No matches found."
    blocks = [f"[{p.payload.get('source', '?')}]\n{p.payload.get('text', '')}"
              for p in res.points]
    return "\n\n---\n\n".join(blocks)


if __name__ == "__main__":
    mcp.run()   # stdio transport by default
