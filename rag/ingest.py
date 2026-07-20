# /// script
# requires-python = ">=3.11"
# dependencies = ["qdrant-client>=1.12", "httpx", "python-dotenv", "tiktoken"]
# ///
"""Embed text files into Qdrant.

Token-aware, heading-aware chunking; idempotent per-file reingest.

Usage:
  uv run rag/ingest.py README.org
  uv run rag/ingest.py ./some-docs-dir
"""
import hashlib
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from qdrant_client.models import FieldCondition, Filter, MatchValue, PointStruct

from chunking import _title_from, chunk
from common import COLLECTION, ensure_collection, embed, get_client


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

    total_points = 0
    for f in files:
        content = f.read_text(errors="ignore")
        title = _title_from(content, f.stem)
        doc_hash = hashlib.sha256(content.encode()).hexdigest()
        ingested_at = datetime.now(timezone.utc).isoformat()
        chunks = chunk(content, title=title)
        n = len(chunks)

        # Idempotent per-file clobber: delete this file's existing points
        # (by exact source match) before reinserting. Also self-migrates
        # old {text, source}-only points to the new rich payload.
        client.delete(
            collection_name=COLLECTION,
            points_selector=Filter(must=[
                FieldCondition(key="source", match=MatchValue(value=str(f))),
            ]),
        )

        vectors = embed([c.text for c in chunks])
        client.upsert(
            COLLECTION,
            points=[
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=v,
                    payload={
                        "text": c.text,
                        "source": str(f),
                        "title": title,
                        "section": c.section,
                        "chunk_index": i,
                        "total_chunks": n,
                        "doc_hash": doc_hash,
                        "ingested_at": ingested_at,
                    },
                )
                for i, (c, v) in enumerate(zip(chunks, vectors))
            ],
        )
        total_points += n
        print(f"  {f}: {n} chunks (clobbered old, upserted new)")

    print(f"Ingested {total_points} chunks from {len(files)} file(s) into '{COLLECTION}'.")


if __name__ == "__main__":
    main(sys.argv[1:])
