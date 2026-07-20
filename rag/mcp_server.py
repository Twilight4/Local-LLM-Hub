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
                      "most relevant to the query. Returns top matching text with "
                      "source and section. Optional filters narrow the search before "
                      "semantic ranking: source_contains (substring of file path) "
                      "and section_contains (substring of heading text).")
def search_internal_docs(
    query: str,
    limit: int = 4,
    source_contains: str | None = None,
    section_contains: str | None = None,
) -> str:
    vec = embed([query])[0]
    client = get_client()
    ensure_collection(client)
    # ponytail: post-filter on over-fetched results — fine for local scale
    # (≤10k points). If the collection grows past that, add a Qdrant full-text
    # payload index on `source`/`section` and switch to MatchText pre-filter.
    fetch_n = limit * 8 if (source_contains or section_contains) else limit
    res = client.query_points(collection_name=COLLECTION, query=vec, limit=fetch_n)
    points = res.points
    if source_contains:
        needle = source_contains.lower()
        points = [p for p in points if needle in str(p.payload.get("source", "")).lower()]
    if section_contains:
        needle = section_contains.lower()
        points = [p for p in points if needle in str(p.payload.get("section", "")).lower()]
    points = points[:limit]
    if not points:
        return "No matches found."
    blocks = [f"[{p.payload.get('source', '?')} · {p.payload.get('section', '?')}]\n"
              f"{p.payload.get('text', '')}"
              for p in points]
    return "\n\n---\n\n".join(blocks)


if __name__ == "__main__":
    mcp.run()   # stdio transport by default
