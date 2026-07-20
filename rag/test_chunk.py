# /// script
# requires-python = ">=3.11"
# dependencies = ["tiktoken"]
# ///
"""Self-check for rag/chunking.py. No pytest — runs as `uv run rag/test_chunk.py`.

Each test guards an invariant of the chunker. Exit 0 = pass; AssertionError = regression.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from chunking import CHUNK_SIZE, Chunk, _count, chunk


def _many_tokens(n: int) -> str:
    """Build a paragraph of ~n tokens by repeating a short sentence."""
    base = "The Vulkan RADV driver exposes the AMD GPU to Ollama. "
    one = _count(base)
    return base * (n // one + 1)


def test_two_headings():
    doc = ("# Title\n"
           "Intro paragraph one.\n\n"
           "Intro paragraph two.\n\n"
           "## Setup\n"
           "Do this then that.\n\n"
           "More setup detail here.\n")
    chunks = chunk(doc, title="Title")
    assert chunks, "expected non-empty"
    assert all(c.section in {"Title", "Setup"} for c in chunks), \
        f"sections leaked: {set(c.section for c in chunks)}"


def test_oversized_paragraph():
    big = _many_tokens(1500)
    chunks = chunk(big, title="t")
    assert len(chunks) >= 3, f"expected >=3 chunks, got {len(chunks)}"
    for c in chunks:
        assert _count(c.text) <= CHUNK_SIZE, \
            f"chunk exceeds CHUNK_SIZE: {_count(c.text)} > {CHUNK_SIZE}"


def test_code_fence_not_heading():
    """`#`-comments and `*`-lines inside code blocks must not become sections."""
    doc = ("# Real Heading\n"
           "Some intro text.\n\n"
           "```bash\n"
           "# this bash comment is NOT a heading\n"
           "echo hello\n"
           "```\n\n"
           "Trailing text under Real Heading.\n")
    chunks = chunk(doc, title="t")
    sections = {c.section for c in chunks}
    assert "this bash comment is NOT a heading" not in sections, \
        f"code comment leaked as section: {sections}"
    assert all(c.section in {"Real Heading", "t"} for c in chunks), \
        f"unexpected section: {sections}"


def test_empty():
    assert chunk("", title="") == [Chunk("", "")]


def test_no_headings_uses_title():
    chunks = chunk("Just plain text. Another sentence.\n\nSecond paragraph here.",
                   title="t")
    assert all(c.section == "t" for c in chunks), \
        f"expected all sections == title, got {set(c.section for c in chunks)}"


if __name__ == "__main__":
    for fn in (test_two_headings,
               test_oversized_paragraph,
               test_code_fence_not_heading,
               test_empty,
               test_no_headings_uses_title):
        fn()
        print(f"ok: {fn.__name__}")
    print("all chunker checks passed")
