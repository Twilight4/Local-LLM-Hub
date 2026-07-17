"""Shared config + helpers for ingest.py and mcp_server.py."""
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

# Load the project .env (works regardless of which dir you run from).
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

QDRANT_URL    = "http://127.0.0.1:6333"
LITELLM_URL   = "http://127.0.0.1:4000"
COLLECTION    = "internal-docs"
EMBED_MODEL   = "nomic-embed-text"
EMBED_DIM     = 768                       # must match nomic-embed-text
MASTER_KEY    = os.environ["LITELLM_MASTER_KEY"]


def get_client() -> QdrantClient:
    return QdrantClient(url=QDRANT_URL)


def ensure_collection(client: QdrantClient) -> None:
    """Create the collection once with cosine similarity."""
    if not client.collection_exists(COLLECTION):
        client.create_collection(
            COLLECTION,
            vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
        )


def embed(texts: list[str]) -> list[list[float]]:
    """Embed a batch of strings via the LiteLLM gateway."""
    r = httpx.post(
        f"{LITELLM_URL}/v1/embeddings",
        headers={"Authorization": f"Bearer {MASTER_KEY}"},
        json={"model": EMBED_MODEL, "input": texts},
        timeout=60.0,
    )
    r.raise_for_status()
    return [d["embedding"] for d in r.json()["data"]]
