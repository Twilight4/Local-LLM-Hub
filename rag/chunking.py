# /// script
# requires-python = ">=3.11"
# dependencies = ["tiktoken"]
# ///
"""Token-aware, heading-aware chunker. Pure function, no I/O.

Split hierarchy: markdown/org headings → paragraphs → sentences, packing
paragraphs into chunks up to CHUNK_SIZE tokens. Single deps surface (tiktoken)
so the test script can run in a minimal venv.
"""
import re
from typing import NamedTuple

import tiktoken

CHUNK_SIZE = 500   # tokens; nomic-embed-text ceiling is 8192, so 500 is ~6%
OVERLAP    = 50    # tokens (~10%); carried as trailing paragraphs into next chunk

# cl100k_base ≈ nomic-embed-text's BPE within ±20% — fine at 500/8192 budget.
_ENC = tiktoken.get_encoding("cl100k_base")


class Chunk(NamedTuple):
    text: str
    section: str   # nearest heading text; "" or title fallback if no heading seen


def _count(text: str) -> int:
    return len(_ENC.encode(text))


_HEADING_RE = re.compile(r'^(?:#{1,6}\s+|\*+\s+)(.*)$')

# Code-fence markers — lines inside these must NOT be read as headings
# (a `#` bash comment or `*` org-bullet inside a code block isn't a heading).
_ORG_FENCE_START = re.compile(r'#\+begin_src', re.IGNORECASE)
_ORG_FENCE_END   = re.compile(r'#\+end_src', re.IGNORECASE)
_MD_FENCE        = re.compile(r'^```')


def _split_sections(text: str) -> list[tuple[str, str]]:
    """Walk lines; on a heading line (outside code fences), flush buffered body
    under the prior heading. Code-fence lines are body, never headings."""
    sections: list[tuple[str, str]] = []
    cur_h, buf = "", []
    in_fence = False
    for line in text.splitlines():
        if _ORG_FENCE_START.search(line):
            in_fence = True
        elif _ORG_FENCE_END.search(line):
            in_fence = False
        elif _MD_FENCE.match(line):
            in_fence = not in_fence
        if not in_fence:
            m = _HEADING_RE.match(line)
            if m:
                if buf or sections:
                    sections.append((cur_h, "\n".join(buf)))
                cur_h, buf = m.group(1).strip(), []
                continue
        buf.append(line)
    sections.append((cur_h, "\n".join(buf)))
    return sections


def _split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]


_SENT_RE = re.compile(r'(?<=[.!?])\s+')


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT_RE.split(text) if s.strip()]


def _title_from(text: str, fallback: str) -> str:
    """First heading's text, or `fallback` (filename stem) if none."""
    for line in text.splitlines():
        m = _HEADING_RE.match(line)
        if m:
            return m.group(1).strip()
    return fallback


def chunk(text: str, title: str = "") -> list[Chunk]:
    """Token-aware, heading-aware chunker.

    Invariant: no emitted chunk's `_count(text)` exceeds CHUNK_SIZE, except
    when a single sentence is itself longer than CHUNK_SIZE tokens (last-resort
    hard token-slice, exact at CHUNK_SIZE boundary).
    """
    if not text.strip():
        return [Chunk("", title)]

    out: list[Chunk] = []
    for heading, body in _split_sections(text):
        section_label = heading or title
        pack: list[str] = []
        pack_tokens = 0

        def emit():
            """Flush pack as one Chunk; leave a carry of ≤OVERLAP tokens for the next."""
            nonlocal pack, pack_tokens
            if pack:
                out.append(Chunk("\n\n".join(pack), section_label))
                carry, carry_t = [], 0
                while pack and carry_t < OVERLAP:
                    c = pack.pop()
                    carry.insert(0, c)
                    carry_t += _count(c)
                pack, pack_tokens = carry, carry_t

        for para in _split_paragraphs(body):
            pt = _count(para)
            if pt > CHUNK_SIZE:
                emit()
                # sentence fallback within the oversized paragraph
                spack: list[str] = []
                spack_t = 0
                for sent in _split_sentences(para):
                    st = _count(sent)
                    if st > CHUNK_SIZE:
                        if spack:
                            out.append(Chunk("\n\n".join(spack), section_label))
                            spack, spack_t = [], 0
                        # last resort: hard token slice
                        toks = _ENC.encode(sent)
                        for i in range(0, len(toks), CHUNK_SIZE):
                            out.append(Chunk(_ENC.decode(toks[i:i + CHUNK_SIZE]),
                                             section_label))
                    elif spack_t + st > CHUNK_SIZE:
                        out.append(Chunk("\n\n".join(spack), section_label))
                        spack, spack_t = [sent], st
                    else:
                        spack.append(sent)
                        spack_t += st
                if spack:
                    out.append(Chunk("\n\n".join(spack), section_label))
                pack, pack_tokens = [], 0
            elif pack_tokens + pt > CHUNK_SIZE:
                emit()
                pack.append(para)
                pack_tokens += pt
            else:
                pack.append(para)
                pack_tokens += pt
        emit()
    return out
