# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib"]
# ///
"""Render the local-llm-hub architecture diagram to assets/architecture.png.

Run:  uv run assets/render_architecture.py

Layout:
  Top row    — main chat path: Browser → Open WebUI → LiteLLM → Ollama → GPU (optional)
  Mid-left   — second entry point: curl/SDK → LiteLLM (master key)
  Mid-center — tracing side-channel: LiteLLM → Phoenix (OTel/OTLP)
  Bottom row — RAG layer: AI agent → rag/mcp_server → Qdrant ← rag/ingest
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

# Box fill colours by role
C = {
    "entry":   "#D6EAF8",  # external callers (browser, curl, agent)
    "webui":   "#D5F5E3",  # Open WebUI
    "gateway": "#FCF3CF",  # LiteLLM (the hub)
    "engine":  "#FDEBD0",  # Ollama
    "gpu":     "#FADBD8",  # hardware
    "obs":     "#E8DAEF",  # Phoenix
    "db":      "#D1F2EB",  # Qdrant
    "rag":     "#EAECEE",  # rag/ scripts
}

fig, ax = plt.subplots(figsize=(14, 7.5))
ax.set_xlim(0, 14)
ax.set_ylim(0.5, 8.2)
ax.axis("off")


def box(cx, cy, w, h, title, subtitle, color):
    ax.add_patch(FancyBboxPatch(
        (cx - w / 2, cy - h / 2), w, h,
        boxstyle="round,pad=0.08", fc=color, ec="#555", lw=1.2))
    ax.text(cx, cy + 0.13, title, ha="center", va="center",
            fontsize=10.5, fontweight="bold")
    ax.text(cx, cy - 0.19, subtitle, ha="center", va="center",
            fontsize=8, color="#444")


def arrow(x1, y1, x2, y2, label=None, style="-", color="#333",
          rad=0.0, loff=(0, 0.16)):
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2), arrowstyle="->", mutation_scale=16,
        color=color, lw=1.5, linestyle=style,
        connectionstyle=f"arc3,rad={rad}"))
    if label:
        mx, my = (x1 + x2) / 2 + loff[0], (y1 + y2) / 2 + loff[1]
        ax.text(mx, my, label, ha="center", va="center", fontsize=7.5,
                style="italic", color="#555",
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85))


# --- Top row: main chat path ---
box(1.3, 6.8, 2.0, 0.85, "Browser", "user", C["entry"])
box(3.8, 6.8, 2.2, 0.85, "Open WebUI", ":8080", C["webui"])
box(6.8, 6.8, 2.0, 0.85, "LiteLLM", ":4000 · master key", C["gateway"])
box(9.5, 6.8, 2.0, 0.85, "Ollama", ":11434", C["engine"])
box(12.3, 6.8, 2.4, 0.85, "AMD GPU (optional)", "RX 9070 XT · Vulkan", C["gpu"])

arrow(2.3, 6.8, 2.7, 6.8)
arrow(4.9, 6.8, 5.8, 6.8)
arrow(7.8, 6.8, 8.5, 6.8)
arrow(10.5, 6.8, 11.1, 6.8, label="GPU override", style="--", color="#999")

# --- Tracing side-channel (LiteLLM → Phoenix) ---
box(6.8, 4.3, 2.0, 0.85, "Phoenix", ":6006 · traces", C["obs"])
arrow(6.8, 6.37, 6.8, 4.73, label="trace (OTel/OTLP)", style="--",
      color="#7D3C98", loff=(1.2, 0))

# --- Second entry point: curl / SDK → LiteLLM ---
box(3.0, 4.3, 2.4, 0.85, "curl / SDK", "OpenAI-compatible client", C["entry"])
arrow(3.8, 4.73, 6.2, 6.37, label="master key", rad=-0.18, loff=(0.6, 0.12))

# --- Bottom row: RAG layer ---
box(1.3, 1.8, 2.0, 0.85, "AI agent", "MCP client", C["entry"])
box(4.5, 1.8, 2.8, 0.85, "rag/mcp_server", "search-internal-docs", C["rag"])
box(8.3, 1.8, 2.0, 0.85, "Qdrant", ":6333 · vectors", C["db"])
box(11.5, 1.8, 2.4, 0.85, "rag/ingest", "chunk → embed → upsert", C["rag"])

arrow(2.3, 1.8, 3.1, 1.8, label="MCP / stdio")
arrow(5.9, 1.8, 7.3, 1.8, label="search")
arrow(10.3, 1.8, 9.3, 1.8, label="embed + upsert")

# --- Title + caption ---
ax.text(7, 7.85, "Local LLM Hub — request & tracing flow",
        ha="center", va="center", fontsize=13.5, fontweight="bold")
ax.text(7, 7.5, "every LiteLLM call is traced to Phoenix via OTel  ·  "
        "Open WebUI routes through LiteLLM (not Ollama directly)  ·  "
        "all ports bind to 127.0.0.1  ·  CPU by default (GPU optional)",
        ha="center", va="center", fontsize=8, color="#666", style="italic")

plt.tight_layout()
out = Path(__file__).parent / "architecture.png"
plt.savefig(out, dpi=150, bbox_inches="tight")
print(f"saved {out}  ({out.stat().st_size:,} bytes)")
