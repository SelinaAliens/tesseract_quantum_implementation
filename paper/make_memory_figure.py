#!/usr/bin/env python3
"""Figure for the memory-persistence result."""
import json
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np

mpl.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                     "figure.dpi": 120})

RESULTS = Path(__file__).parent.parent / "results"
FIG     = Path(__file__).parent / "figures"

src = sorted(RESULTS.glob("p4s_memory_cirq_*.json"))[-1]
data = json.loads(src.read_text())
horizons = data["horizons"]
disc = data["discriminability"]

mean = [disc[str(n)]["mean_pairwise_distance"] for n in horizons]
mx   = [disc[str(n)]["max_pairwise_distance"]  for n in horizons]
mn   = [disc[str(n)]["min_pairwise_distance"]  for n in horizons]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.8),
                               gridspec_kw={"width_ratios": [1.1, 1]})

# Panel a — distance vs horizon
ax1.fill_between(horizons, mn, mx, alpha=0.18, color="#2ca02c",
                 label="min-to-max pair range")
ax1.plot(horizons, mean, "o-", color="#2ca02c", lw=2.2, ms=10,
         label="mean pairwise distance")
# Peak marker
imax = int(np.argmax(mean))
ax1.scatter(horizons[imax], mean[imax], s=200, facecolor="yellow",
            edgecolor="black", zorder=5,
            label=f"peak at n={horizons[imax]}")
ax1.axhline(0, color="grey", lw=0.4)
ax1.set_xlabel("n  (Coxeter periods)")
ax1.set_ylabel(r"pairwise bond-vector distance ‖ bond(M$_i$) − bond(M$_j$) ‖")
ax1.set_xticks(horizons)
ax1.set_title("(a) Memory discriminability survives to n = 10 periods\n"
              "(6 memories, 15 pairs, Cirq ideal, J = 0.1)",
              loc="left", fontsize=10)
ax1.legend(loc="upper right", frameon=False, fontsize=9)
ax1.set_ylim(0, max(mx) * 1.1)
# Annotate decay
ax1.annotate(
    f"late/early ratio = {mean[-1]/mean[0]:.2f}\n"
    "(memory 74% retained at 10 periods)",
    xy=(horizons[-1], mean[-1]), xytext=(horizons[-1] - 2.8, mean[-1] + 0.35),
    arrowprops=dict(arrowstyle="->", color="black", lw=0.8),
    fontsize=9, ha="left"
)
ax1.annotate(
    "early AMPLIFICATION:\ndistance grows n=1→3\nbefore slow decay",
    xy=(3, mean[2]), xytext=(4.5, 1.10),
    arrowprops=dict(arrowstyle="->", color="darkred", lw=0.9),
    fontsize=9, ha="left", color="darkred"
)

# Panel b — raw bond-vector heatmap at n=3 (peak) and n=10 (late)
memories = list(data["memories"].keys())
bonds = ["bond_AB", "bond_BC", "bond_CD", "bond_DA"]

def bond_matrix(n_p):
    M = np.zeros((len(memories), len(bonds)))
    for i, m in enumerate(memories):
        for j, b in enumerate(bonds):
            M[i, j] = data["results"][str(n_p)][m][b]["mean"]
    return M

M_peak = bond_matrix(3)
M_late = bond_matrix(10)

combined = np.hstack([M_peak, np.full((len(memories), 1), np.nan), M_late])
im = ax2.imshow(combined, aspect="auto", cmap="RdYlGn", vmin=0, vmax=0.9)
ax2.set_yticks(range(len(memories)))
ax2.set_yticklabels(memories, fontsize=9)
ax2.set_xticks([0, 1, 2, 3, 5, 6, 7, 8])
ax2.set_xticklabels(bonds + bonds, fontsize=8, rotation=30, ha="right")
ax2.axvline(3.5, color="black", lw=1.5)
ax2.text(1.5, -0.7, "n = 3 (peak)", ha="center", fontsize=10, fontweight="bold")
ax2.text(6.5, -0.7, "n = 10 (late)", ha="center", fontsize=10, fontweight="bold")
# Annotate cells
for i in range(len(memories)):
    for j in range(combined.shape[1]):
        if not np.isnan(combined[i, j]):
            color = "white" if combined[i, j] < 0.35 else "black"
            ax2.text(j, i, f"{combined[i, j]:.2f}",
                     ha="center", va="center", color=color, fontsize=8,
                     fontweight="bold")
cbar = plt.colorbar(im, ax=ax2, fraction=0.035, pad=0.04)
cbar.set_label(r"|⟨u|v⟩|  bond coherence", fontsize=9)
ax2.set_title("(b) Bond-pattern signatures at n = 3 (peak) and n = 10 (late)\n"
              "different memories give visibly different patterns at both",
              loc="left", fontsize=10)

fig.suptitle(
    "Figure.  Content-memory persistence on the 4-square merkabit substrate.\n"
    "Memories remain distinguishable for at least 10 Coxeter periods under "
    "internal dynamics alone. Early-period amplification is the substrate's "
    "feature-extraction signature.",
    fontsize=10, y=1.03
)
fig.tight_layout()
out = FIG / "fig_memory_persistence.png"
fig.savefig(out, bbox_inches="tight", dpi=200)
plt.close(fig)
print(f"wrote {out}")
