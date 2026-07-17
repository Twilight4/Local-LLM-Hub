# /// script
# requires-python = ">=3.11"
# dependencies = ["qdrant-client>=1.12", "httpx", "python-dotenv"]
# ///
"""Embed text files into Qdrant.

Usage:
  uv run rag/ingest.py README.org
  uv run rag/ingest.py ./some-docs-dir
"""
import sys
import uuid
from pathlib import Path

from qdrant_client.models import PointStruct

from common import COLLECTION, ensure_collection, embed, get_client

CHUNK_SIZE = 800      # characters
OVERLAP    = 100


def chunk(text: str) -> list[str]:
    out, i = [], 0
    while i < len(text):
        out.append(text[i:i + CHUNK_SIZE])
        i += CHUNK_SIZE - OVERLAP
    return out or [text]


def gather(paths: list[str]) -> list[Path]:
    files = []
    for p in paths:
        path = Path(p)
        if path.is_dir():
            files.extend(f for f in path.rglob("*") if f.is_file() and f.suffix in {".org", ".md", ".txt"})
        elif path.is_file():
            files.append(path)
    return files


def main(paths: list[str]) -> None:
    files = gather(paths) or [Path("README.org")]
    client = get_client()
    ensure_collection(client)

    records = []  # (text, source)
    for f in files:
        for c in chunk(f.read_text(errors="ignore")):
            records.append((c, str(f)))
    if not records:
        print("Nothing to ingest."); return

    vectors = embed([t for t, _ in records])
    client.upsert(
        COLLECTION,
        points=[
            PointStruct(id=str(uuid.uuid4()), vector=v, payload={"text": t, "source": s})
            for (t, s), v in zip(records, vectors)
        ],
    )
    print(f"Upserted {len(records)} chunks from {len(files)} file(s) into '{COLLECTION}'.")


if __name__ == "__main__":
    main(sys.argv[1:])
