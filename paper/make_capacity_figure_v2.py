"""Figure 2 (v2): capacity from exact ideal fingerprints and from the direct
noisy simulation of all 81 patterns; the v1 linear-damping projection is kept
as a dashed reference."""
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
matplotlib.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
HERE = Path(__file__).parent.resolve()
RES = HERE.parent / "results"

def greedy(D, thr):
    n = D.shape[0]; flat = D.copy(); np.fill_diagonal(flat, -1)
    i, j = divmod(int(np.argmax(flat)), n)
    if D[i, j] < thr: return []
    sel = [i, j]; rem = set(range(n)) - set(sel)
    while rem:
        best, bm = None, -1
        for k in rem:
            md = min(D[k, s] for s in sel)
            if md >= thr and md > bm: best, bm = k, md
        if best is None: break
        sel.append(best); rem.discard(best)
    return sel
dmat = lambda fp: np.linalg.norm(fp[:, None, :] - fp[None, :, :], axis=2)
ex = json.loads((RES / "exact_fingerprints.json").read_text())
nz = json.loads((RES / "noisy_p0.005_n1_T500.json").read_text())
f3 = np.array(ex["bond_n3"]); f1 = np.array(ex["bond_n1"])
fn = np.sqrt(np.maximum(0, 2 * np.array(nz["p0_mean"]) - 1))
fproj = 0.5 + 0.384 * (f1 - 0.5)
Tid = [0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 1.0]
Thw = [0.05, 0.07, 0.10, 0.15, 0.20, 0.30]
cur = {"n3": [len(greedy(dmat(f3), t)) for t in Tid],
       "n1": [len(greedy(dmat(f1), t)) for t in Tid],
       "direct": [len(greedy(dmat(fn), t)) for t in Thw],
       "proj": [len(greedy(dmat(fproj), t)) for t in Thw]}
print(cur)
bits = lambda v: [np.log2(x) if x > 0 else 0 for x in v]
fig, axes = plt.subplots(1, 3, figsize=(15, 4.8))
for ax, tr, yl, ttl in ((axes[0], lambda v: v, "capacity N", "(a) Capacity N(D)"),
                        (axes[1], bits, "bits (log₂ capacity)", "(b) Addressable bits")):
    ax.plot(Tid, tr(cur["n3"]), "o-", color="#2ca02c", lw=2, ms=7, label="n=3 ideal (exact)")
    ax.plot(Tid, tr(cur["n1"]), "s-", color="#1f77b4", lw=2, ms=7, label="n=1 ideal (exact)")
    ax.plot(Thw, tr(cur["direct"]), "^-", color="#d62728", lw=2, ms=7,
            label="n=1, p_depol=0.005, direct simulation")
    ax.plot(Thw, tr(cur["proj"]), "v--", color="#d62728", lw=1, ms=5, alpha=0.5,
            label="n=1, linear-damping projection (f = 0.384)")
    ax.set_xlabel("distinguishability threshold D"); ax.set_ylabel(yl)
    ax.set_xlim(0, 1.1); ax.set_title(ttl, loc="left", fontsize=10)
    ax.legend(loc="upper right", frameon=False, fontsize=8)
axes[0].axhline(81, color="grey", ls="--", lw=0.7); axes[0].axhline(16, color="black", ls=":", lw=0.7)
axes[0].text(0.02, 83, "3⁴ = 81", fontsize=8, color="grey"); axes[0].text(0.75, 18, "4-bit binary (16)", fontsize=8)
axes[0].set_ylim(0, 125)
axes[1].axhline(np.log2(81), color="grey", ls="--", lw=0.7); axes[1].axhline(4, color="black", ls=":", lw=0.7)
axes[1].set_ylim(0, 9)
ax = axes[2]; iu = np.triu_indices(81, 1)
ax.hist(dmat(f1)[iu], bins=40, color="#7dc99a", edgecolor="black", lw=0.4, alpha=0.7, label="n=1 ideal (exact)")
ax.hist(dmat(fn)[iu], bins=40, color="#d62728", edgecolor="black", lw=0.4, alpha=0.5,
        label="n=1, p_depol=0.005, direct simulation")
ax.set_xlabel("pairwise bond-vector distance"); ax.set_ylabel("# pairs"); ax.set_xlim(0, 1.25); ax.set_ylim(0, 300)
ax.set_title("(c) Pair distances (3240 pairs of 81 patterns)", loc="left", fontsize=10)
ax.legend(loc="upper right", frameon=False, fontsize=8)
fig.tight_layout(); fig.savefig(HERE / "figures" / "fig_memory_capacity_v2.png", bbox_inches="tight", dpi=200)
