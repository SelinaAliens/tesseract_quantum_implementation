#!/usr/bin/env python3
"""Figure for the memory-capacity result.

Three regimes shown:
  (a) capacity N(D): n=3 ideal (peak amplification), n=1 ideal, n=1 hardware-
      projected with empirical p_depol=0.005 damping
  (b) information bits vs threshold
  (c) pairwise distance distribution at n=1 ideal (hardware operating point)
"""
import json
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np

mpl.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                     "figure.dpi": 120})

RESULTS = Path(__file__).parent.parent / "results"
FIG     = Path(__file__).parent / "figures"
FIG.mkdir(parents=True, exist_ok=True)

# Load both ideal runs
caps = sorted(RESULTS.glob("p4s_memory_capacity_cirq_*.json"))
# First run was n=3 (peak), second was n=1
def load_by_n(n):
    for f in caps:
        d = json.loads(f.read_text())
        if d.get("n_periods") == n:
            return d
    return None

d_n3 = load_by_n(3)
d_n1 = load_by_n(1)
assert d_n3 is not None and d_n1 is not None, f"need both n=1 and n=3 runs in {caps}"

def extract(d):
    tbl = d["capacity_table"]
    return [row["D"] for row in tbl], [row["N"] for row in tbl]

D_n3, N_n3 = extract(d_n3)
D_n1, N_n1 = extract(d_n1)

# Hardware projection: bond values converge toward fixed point 0.5 under
# depolarization. Distances shrink by damping factor f_damp. We apply this
# analytically to the n=1 ideal fingerprints.
# f_damp is measured by calibrate_4square_damping.py; default to 0.20
# (placeholder based on 2-merkabit tunnel result pending 4-square calibration).
CALIB = sorted(RESULTS.glob("calibrate_4square_damping_*.json"))
if CALIB:
    cal = json.loads(CALIB[-1].read_text())
    f_damp = abs(cal.get("damping_factor_mean", 0.20))
    damp_label = f"measured f={f_damp:.2f}"
else:
    f_damp = 0.20
    damp_label = f"provisional f={f_damp:.2f} (2-merkabit proxy)"

# Apply damping to n=1 fingerprints and recompute capacity
fp_n1 = np.array(d_n1["fingerprints"])
fp_hw = 0.5 + (fp_n1 - 0.5) * f_damp
Dmat_hw = np.linalg.norm(fp_hw[:, None, :] - fp_hw[None, :, :], axis=2)

def greedy_pack(Dmat, thresh):
    n = Dmat.shape[0]
    flat = Dmat.copy(); np.fill_diagonal(flat, -1)
    i, j = divmod(int(np.argmax(flat)), n)
    if Dmat[i, j] < thresh:
        return []
    selected = [i, j]
    rem = set(range(n)) - set(selected)
    while rem:
        best, best_min = None, -1
        for k in rem:
            md = min(Dmat[k, s] for s in selected)
            if md >= thresh and md > best_min:
                best, best_min = k, md
        if best is None:
            break
        selected.append(best)
        rem.discard(best)
    return selected

thresholds = [0.01, 0.02, 0.03, 0.05, 0.07, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50]
N_hw = [len(greedy_pack(Dmat_hw, t)) for t in thresholds]
D_hw = thresholds

bits_n3 = [np.log2(n) if n > 0 else 0 for n in N_n3]
bits_n1 = [np.log2(n) if n > 0 else 0 for n in N_n1]
bits_hw = [np.log2(n) if n > 0 else 0 for n in N_hw]

# Pairwise distances at n=1 ideal
fp_n1_arr = np.array(d_n1["fingerprints"])
D_n1_all = np.linalg.norm(fp_n1_arr[:, None, :] - fp_n1_arr[None, :, :], axis=2)
upper_n1 = D_n1_all[np.triu_indices(len(fp_n1_arr), k=1)]

# ---------------- plotting ----------------
fig, axes = plt.subplots(1, 3, figsize=(15, 4.8))

# Panel a — capacity curves
ax = axes[0]
ax.plot(D_n3, N_n3, "o-", color="#2ca02c", lw=2.2, ms=9,
        label="n=3 ideal (peak amplification)")
ax.plot(D_n1, N_n1, "s-", color="#1f77b4", lw=2.2, ms=9,
        label="n=1 ideal (HW op-point)")
ax.plot(D_hw, N_hw, "^-", color="#d62728", lw=2.2, ms=9,
        label=f"n=1, p_depol=0.005 ({damp_label})")
ax.axhline(81, color="grey", ls="--", lw=0.7, alpha=0.5)
ax.text(1.02, 81.5, "theoretical max (3⁴=81)", fontsize=8, color="grey")
ax.axhline(16, color="black", ls=":", lw=0.7, alpha=0.5)
ax.text(1.02, 17, "4-bit binary (16)", fontsize=8, color="black")
ax.set_xlabel("distinguishability threshold D")
ax.set_ylabel("capacity N")
ax.set_xlim(0, 1.1)
ax.set_ylim(0, 90)
ax.set_title("(a) Capacity N(D): ideal vs hardware-realistic",
             loc="left", fontsize=10)
ax.legend(loc="upper right", frameon=False, fontsize=8)

# Panel b — bits
ax = axes[1]
ax.plot(D_n3, bits_n3, "o-", color="#2ca02c", lw=2.2, ms=9, label="n=3 ideal")
ax.plot(D_n1, bits_n1, "s-", color="#1f77b4", lw=2.2, ms=9, label="n=1 ideal")
ax.plot(D_hw, bits_hw, "^-", color="#d62728", lw=2.2, ms=9,
        label="n=1, p=0.005")
ax.axhline(np.log2(81), color="grey", ls="--", lw=0.7)
ax.text(1.02, np.log2(81) + 0.08, "log₂(81)=6.34", fontsize=8, color="grey")
ax.axhline(4, color="black", ls=":", lw=0.7)
ax.text(1.02, 4.08, "4-bit binary", fontsize=8, color="black")
ax.set_xlabel("distinguishability threshold D")
ax.set_ylabel("bits (log₂ capacity)")
ax.set_xlim(0, 1.1)
ax.set_ylim(0, 7)
ax.set_title("(b) Information bits vs threshold", loc="left", fontsize=10)
ax.legend(loc="upper right", frameon=False, fontsize=8)

# Panel c — distance histogram (n=1 ideal)
ax = axes[2]
ax.hist(upper_n1, bins=40, color="#7dc99a", edgecolor="black", lw=0.4,
        alpha=0.7, label="n=1 ideal")
ax.axvline(np.median(upper_n1), color="black", lw=1.5,
           label=f"median = {np.median(upper_n1):.3f}")
# Also overlay projected hardware histogram (same pairs, scaled by f_damp)
upper_hw = upper_n1 * f_damp
ax.hist(upper_hw, bins=40, color="#d62728", edgecolor="black", lw=0.4,
        alpha=0.5, label=f"n=1 p=0.005 (×{f_damp:.2f})")
ax.set_xlabel("pairwise bond-vector distance")
ax.set_ylabel("# pairs")
ax.set_xlim(0, 1.25)
ax.set_title(f"(c) Pair distance distribution\n(3240 pairs of 81 patterns)",
             loc="left", fontsize=10)
ax.legend(loc="upper right", frameon=False, fontsize=8)

fig.suptitle(
    "Figure. Memory capacity of the 4-square merkabit substrate.\n"
    "Ideal: ~5 bits addressable at D=0.3 (31/81 memories, 78% of 3⁴ ceiling). "
    f"Hardware projection at p_depol=0.005 ({damp_label}): pairwise distances "
    f"shrink by f={f_damp:.2f}, collapsing practical capacity.",
    fontsize=10, y=1.03,
)
fig.tight_layout()
out = FIG / "fig_memory_capacity.png"
fig.savefig(out, bbox_inches="tight", dpi=200)
plt.close(fig)
print(f"wrote {out}")
print(f"n=3 ideal @ D=0.3: N={N_n3[D_n3.index(0.3)]}  ({bits_n3[D_n3.index(0.3)]:.2f} bits)")
print(f"n=1 ideal @ D=0.3: N={N_n1[D_n1.index(0.3)]}  ({bits_n1[D_n1.index(0.3)]:.2f} bits)")
d_hw_target = 0.3 * f_damp
N_hw_at_target = len(greedy_pack(Dmat_hw, d_hw_target))
print(f"n=1 hw @ D={d_hw_target:.3f} (equivalent ideal 0.3): N={N_hw_at_target}")
