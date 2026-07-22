# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib"]
# ///
"""Render the local-llm-hub Kubernetes (kind) deployment-topology diagram.

Run:  uv run assets/render_k8s_topology.py

Companion to architecture.png (which shows the logical request/tracing flow).
This shows the K8s *deployment* view:
  - 5 single-replica Deployments + NodePort Services
  - 4 PVCs (ollama, qdrant, phoenix, open-webui; litellm is DB-less)
  - initContainer ordering (open-webui waits litellm; litellm waits ollama)
  - host localhost access via kind extraPortMappings (4 ports; ollama internal-only)
  - post-install model-pull Job
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

C = {
    "entry":  "#D6EAF8",  # host
    "pod_ow": "#D5F5E3",  # open-webui
    "pod_ll": "#FCF3CF",  # litellm
    "pod_ol": "#FDEBD0",  # ollama
    "pod_qd": "#D1F2EB",  # qdrant
    "pod_px": "#E8DAEF",  # phoenix
    "pvc":    "#AEB6BF",  # volumes
    "job":    "#F9E79F",  # pull job
}

fig, ax = plt.subplots(figsize=(14, 8.2))
ax.set_xlim(0, 14)
ax.set_ylim(0.4, 8.2)
ax.axis("off")


def box(cx, cy, w, h, title, subtitle, color):
    ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h,
                                boxstyle="round,pad=0.04", fc=color, ec="#555", lw=1.2))
    ax.text(cx, cy + 0.16, title, ha="center", va="center", fontsize=9.5, fontweight="bold")
    ax.text(cx, cy - 0.18, subtitle, ha="center", va="center", fontsize=7.5, color="#444")


def arrow(x1, y1, x2, y2, label=None, style="-", color="#333", rad=0.0,
          loff=(0, 0.16), fs=7.5):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2),
                                 arrowstyle="-|>", mutation_scale=12, lw=1.4,
                                 color=color, linestyle=style,
                                 connectionstyle=f"arc3,rad={rad}"))
    if label:
        mx, my = (x1 + x2) / 2 + loff[0], (y1 + y2) / 2 + loff[1]
        ax.text(mx, my, label, ha="center", va="center", fontsize=fs, color=color,
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.9))


# --- Cluster boundary ---
ax.add_patch(Rectangle((0.4, 1.15), 13.2, 4.95, fc="#FBFCFC", ec="#7B8A8B", lw=1.4, ls="--"))
ax.text(0.65, 5.95, "kind cluster  ·  namespace: local-llm-hub",
        fontsize=8.5, color="#7B8A8B", fontweight="bold")

# --- Host band (outside the cluster) ---
box(7.0, 6.75, 6.4, 0.8, "Host — localhost",
    "4000 · 8080 · 6006 · 6333  →  extraPortMappings → NodePorts", C["entry"])

# --- Pods (single row) ---
PY = 4.85
box(1.7, PY, 2.2, 0.85, "open-webui", "Deployment · 1 replica", C["pod_ow"])
box(4.4, PY, 2.2, 0.85, "litellm", "Deployment · 1 replica", C["pod_ll"])
box(7.1, PY, 2.2, 0.85, "ollama", "Deployment · 1 replica", C["pod_ol"])
box(9.8, PY, 2.2, 0.85, "qdrant", "Deployment · 1 replica", C["pod_qd"])
box(12.5, PY, 2.2, 0.85, "phoenix", "Deployment · 1 replica", C["pod_px"])

# --- Service annotations (under each pod) ---
for x, t in [
    (1.7, "Service :8080 → 30080"),
    (4.4, "Service :4000 → 30400"),
    (7.1, "Service :11434 (internal)"),
    (9.8, "Service :6333 → 30333"),
    (12.5, "Service :6006 → 30006"),
]:
    ax.text(x, 4.15, t, ha="center", va="center", fontsize=7, color="#555",
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="#bbb", lw=0.6))

# --- PVCs (litellm has none — DB-less) ---
box(1.7, 3.2, 2.2, 0.6, "open-webui-data", "PVC · 2Gi", C["pvc"])
box(7.1, 3.2, 2.2, 0.6, "ollama-models", "PVC · 30Gi", C["pvc"])
box(9.8, 3.2, 2.2, 0.6, "qdrant-data", "PVC · 5Gi", C["pvc"])
box(12.5, 3.2, 2.2, 0.6, "phoenix-data", "PVC · 2Gi", C["pvc"])
ax.text(4.4, 3.2, "(no PVC — DB-less)", ha="center", va="center",
        fontsize=7, style="italic", color="#888")

# pod -> PVC
for x in (1.7, 7.1, 9.8, 12.5):
    arrow(x, PY - 0.43, x, 3.5, color="#999")

# --- host -> mapped pods (ollama intentionally skipped: internal only) ---
for x in (1.7, 4.4, 9.8, 12.5):
    arrow(7.0, 6.35, x, PY + 0.43, color="#2E86C1")

# --- initContainer waits (dashed, between adjacent pods) ---
arrow(2.8, PY, 3.3, PY, label="init: wait :4000", style="--", color="#B9770E")
arrow(5.5, PY, 6.0, PY, label="init: wait :11434", style="--", color="#B9770E")

# --- OTel trace: litellm -> phoenix, arcing over the pod row ---
arrow(5.5, PY + 0.25, 11.4, PY + 0.25, label="OTel trace", style="--",
      color="#7D3C98", rad=-0.32, loff=(0, 0.05))

# --- post-install model-pull Job (near ollama) ---
box(7.1, 1.75, 3.6, 0.7, "post-install Job", "ollama-pull: llama3.2 + nomic-embed-text", C["job"])
arrow(7.1, 2.1, 7.1, 2.9, color="#B7950B")

# --- Title + caption ---
ax.text(7, 7.9, "Local LLM Hub on Kubernetes (kind) — deployment topology",
        ha="center", va="center", fontsize=13, fontweight="bold")
ax.text(7, 7.6, "5 Deployments · 5 NodePort Services · 4 PVCs · initContainer ordering · "
                "post-install model-pull Job · Ollama internal-only",
        ha="center", va="center", fontsize=8, color="#666", style="italic")

plt.tight_layout()
out = Path(__file__).parent / "k8s_topology.png"
plt.savefig(out, dpi=150, bbox_inches="tight")
print(f"saved {out}  ({out.stat().st_size:,} bytes)")
