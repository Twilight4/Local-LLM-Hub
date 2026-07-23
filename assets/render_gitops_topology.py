# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib"]
# ///
"""Render the local-llm-hub GitOps (ArgoCD) control-flow diagram.

Run:  uv run assets/render_gitops_topology.py

Companion to architecture.png (logical request/tracing flow) and
k8s_topology.png (K8s deployment topology). This shows the *GitOps* view:
  - git `main` (public repo) as the source of truth
  - ArgoCD (ns argocd) pulling the chart anonymously + auto-syncing (prune+selfHeal)
  - the kind cluster (ns local-llm-hub) reconciled to git
  - the master-key Secret applied OUT-OF-BAND (never in git, invisible to ArgoCD)
  - self-heal reverting manual drift back to the declared state

Image-reading is unavailable in this environment, so layout correctness is
asserted via geometry checks (no overlapping content boxes; all within canvas).
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

C = {
    "git":     "#D6EAF8",  # source of truth
    "argocd":  "#D5F5E3",  # operator
    "cluster": "#FCF3CF",  # reconciled workload
    "secret":  "#FADBD8",  # out-of-band secret
    "zone":    "#FBFCFC",  # zone fill
}

LIM_X, LIM_Y = (0, 14), (0.3, 8.4)
fig, ax = plt.subplots(figsize=(14, 8.4))
ax.set_xlim(*LIM_X)
ax.set_ylim(*LIM_Y)
ax.axis("off")

rects = []  # (name, x0, y0, x1, y1) content boxes for geometry validation


def zone(x, y, w, h, label, ec):
    ax.add_patch(Rectangle((x, y), w, h, fc=C["zone"], ec=ec, lw=1.4, ls="--"))
    ax.text(x + 0.25, y + h - 0.28, label, fontsize=8.5, color=ec, fontweight="bold")


def box(cx, cy, w, h, title, subtitle, color, name):
    x0, y0 = cx - w / 2, cy - h / 2
    ax.add_patch(FancyBboxPatch((x0, y0), w, h, fc=color, ec="#566573", lw=1.2,
                                boxstyle="round,pad=0.02"))
    ax.text(cx, cy + 0.24, title, ha="center", va="center", fontsize=9.5, fontweight="bold")
    ax.text(cx, cy - 0.24, subtitle, ha="center", va="center", fontsize=7.8, color="#444")
    rects.append((name, x0, y0, x0 + w, y0 + h))


def arrow(x1, y1, x2, y2, label=None, color="#333", style="-", rad=0.0, loff=(0, 0.16)):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                 mutation_scale=14, lw=1.4, color=color, ls=style,
                                 connectionstyle=f"arc3,rad={rad}"))
    if label:
        ax.text((x1 + x2) / 2 + loff[0], (y1 + y2) / 2 + loff[1], label,
                ha="center", va="center", fontsize=7.4, color=color,
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.9))


# --- Title + caption ---
ax.text(7, 8.05, "Local LLM Hub — GitOps (ArgoCD) control flow",
        ha="center", va="center", fontsize=13.5, fontweight="bold")
ax.text(7, 7.72,
        "git main is the source of truth · ArgoCD auto-syncs (prune + selfHeal) · "
        "master-key Secret stays out of git",
        ha="center", va="center", fontsize=8.2, color="#666", style="italic")

# --- Zones ---
zone(0.4, 2.7, 3.0, 3.7, "GitHub (public)", "#2E86C1")
zone(3.9, 2.2, 3.1, 4.2, "namespace: argocd", "#1E8449")
zone(7.5, 1.5, 6.1, 4.9, "kind cluster · namespace: local-llm-hub", "#B7950B")

# --- Content boxes ---
box(1.9, 4.55, 2.5, 1.6, "git: main",
    "Twilight4/Local-LLM-Hub\ndeploy/helm/local-llm-hub/", C["git"], "git")
box(5.45, 4.4, 2.6, 1.8, "ArgoCD v3.4.5",
    "Application CR\nauto-sync: prune + selfHeal", C["argocd"], "argocd")
box(10.55, 4.3, 5.2, 1.9, "5 Deployments reconciled to git",
    "open-webui · litellm · ollama · qdrant · phoenix\n+ post-install model-pull Job (llama3.2)",
    C["cluster"], "cluster")
box(5.3, 1.15, 3.6, 1.2, "out-of-band Secret",
    "values.local.yaml (gitignored)\n→ kubectl apply", C["secret"], "secret")

# --- Arrows ---
arrow(3.15, 4.55, 4.15, 4.45,
      label="anonymous HTTPS pull\n(public repo, no creds)", color="#2E86C1")
arrow(6.75, 4.4, 7.95, 4.3,
      label="sync\n(prune + selfHeal)", color="#1E8449")
arrow(7.1, 1.35, 9.6, 3.35,
      label="LITELLM_MASTER_KEY\n(invisible to ArgoCD · never in git)",
      color="#922B21", rad=0.12, loff=(0.35, 0.15))
arrow(12.9, 5.25, 10.7, 5.95,
      label="self-heal: kubectl scale/edit\n→ reverted to main",
      color="#B7950B", style="--", rad=-0.3, loff=(0.2, 0.05))

# --- Geometry validation (vision unavailable) ---
def _overlap(a, b, pad=0.05):
    return not (a[2] <= b[0] + pad or b[2] <= a[0] + pad
                or a[3] <= b[1] + pad or b[3] <= a[1] + pad)

problems = []
for i in range(len(rects)):
    for j in range(i + 1, len(rects)):
        na, *ra = rects[i]
        nb, *rb = rects[j]
        if _overlap(ra, rb):
            problems.append(f"{na} overlaps {nb}")
for name, x0, y0, x1, y1 in rects:
    if x0 < LIM_X[0] or x1 > LIM_X[1] or y0 < LIM_Y[0] or y1 > LIM_Y[1]:
        problems.append(f"{name} out of canvas")
assert not problems, "geometry problems: " + "; ".join(problems)

plt.tight_layout()
out = Path(__file__).parent / "gitops_topology.png"
plt.savefig(out, dpi=150, bbox_inches="tight")
print(f"saved {out}  ({out.stat().st_size:,} bytes)")
print(f"geometry OK ({len(rects)} boxes, no overlaps, within canvas)")
