#!/usr/bin/env python3
"""
Generate the three figures for Paper 31 from the raw JSON data.

Figure 1 - Per-family tunnel / local attractor values (Cirq, n=2)
Figure 2 - J-sweep: directional gap oscillation and nulls
Figure 3 - (n, noise) significance matrix showing FakeSherbrooke operating point
"""
import json
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np

mpl.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.labelsize": 10,
    "axes.titlesize": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 120,
})

RESULTS = Path(__file__).parent.parent / "results"
FIG     = Path(__file__).parent / "figures"
FIG.mkdir(exist_ok=True)


# =============================================================================
#  Figure 1 — per-family tunnel and local attractor values at n=2
# =============================================================================
def figure_1():
    # Cirq tunnel data (full 6-reps x 4096-shots run)
    src = sorted(RESULTS.glob("p4s_tunnel_cirq_*.json"))[-1]
    data = json.loads(src.read_text())

    families = list(data["results"]["0.0"].keys())
    pretty = {
        "AA_matched":       "A, A\n(basis)",
        "aa_Z3_1_both":     "α, α\n(Z₃=1)",
        "bb_Z3_omega_both": "β, β\n(Z₃=ω)",
        "gg_Z3_w2_both":    "γ, γ\n(Z₃=ω²)",
        "bg_cross_fwd":     "β, γ",
        "gb_cross_rev":     "γ, β",
    }
    x = np.arange(len(families))
    w = 0.26

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for ax, p_depol, title in zip(
        axes, ["0.0", "0.005"],
        [r"(a) ideal (p$_\mathrm{depol}$=0)",
         r"(b) Willow-realistic (p$_\mathrm{depol}$=0.005)"]
    ):
        la, la_e = [], []
        lb, lb_e = [], []
        tu, tu_e = [], []
        for f in families:
            c = data["results"][p_depol][f]
            la.append(c["local_A"]["mean"]); la_e.append(c["local_A"]["sem"])
            lb.append(c["local_B"]["mean"]); lb_e.append(c["local_B"]["sem"])
            tu.append(c["tunnel"]["mean"]);  tu_e.append(c["tunnel"]["sem"])

        ax.bar(x - w, la, w, yerr=la_e, label="local A ⟨u$_A$|v$_A$⟩",
               color="#9ec3e6", edgecolor="#1f77b4", capsize=3)
        ax.bar(x,     lb, w, yerr=lb_e, label="local B ⟨u$_B$|v$_B$⟩",
               color="#fcbfa6", edgecolor="#d62728", capsize=3)
        ax.bar(x + w, tu, w, yerr=tu_e, label="tunnel ⟨u$_A$|v$_B$⟩",
               color="#7dc99a", edgecolor="#2ca02c", capsize=3)
        ax.set_xticks(x)
        ax.set_xticklabels([pretty[f] for f in families], fontsize=9)
        ax.set_ylabel(r"|overlap|")
        ax.set_ylim(0, 1.0)
        ax.axhline(0.5, color="grey", lw=0.6, ls="--", alpha=0.6,
                   label=r"Haar random (1/√d)")
        ax.set_title(title)

    axes[0].legend(loc="upper left", fontsize=8, frameon=False)

    # Annotate the key (β,γ) vs (γ,β) asymmetry on both panels
    for ax, p_depol in zip(axes, ["0.0", "0.005"]):
        bg = data["results"][p_depol]["bg_cross_fwd"]["tunnel"]["mean"]
        gb = data["results"][p_depol]["gb_cross_rev"]["tunnel"]["mean"]
        ax.annotate(
            "", xy=(4 + w, bg), xytext=(5 + w, gb),
            arrowprops=dict(arrowstyle="<->", color="#2ca02c", lw=1.4),
        )
        ax.text(4.5 + w, (bg + gb) / 2, f" gap\n {abs(gb - bg):.2f}",
                color="#2ca02c", fontsize=9, ha="left", va="center", fontweight="bold")

    fig.suptitle(
        "Figure 1.  Per-family overlap observables at n = 2 Coxeter periods "
        "(J = 0.1, Cirq, 6 reps × 4096 shots).\n"
        "Tunnel coherence encodes directional ternary information that "
        "local coherences do not.",
        fontsize=10, y=1.02,
    )
    fig.tight_layout()
    out = FIG / "fig1_per_family_overlaps.png"
    fig.savefig(out, bbox_inches="tight", dpi=200)
    plt.close(fig)
    print(f"wrote {out}")


# =============================================================================
#  Figure 2 — J-sweep: directional gap and oscillation structure
# =============================================================================
def figure_2():
    src = sorted(RESULTS.glob("stress_J_cirq_*.json"))[-1]
    data = json.loads(src.read_text())

    J = []; bg = []; gb = []; gap = []; sigma = []; sem = []
    for k, v in data["results"].items():
        J.append(float(k.split("=")[1]))
        bg.append(v["bg_mean"]); gb.append(v["gb_mean"])
        gap.append(v["gap"]);    sigma.append(v["sigma"])
        sem.append(v["sem_tot"])
    idx = np.argsort(J)
    J = np.array(J)[idx]; bg = np.array(bg)[idx]; gb = np.array(gb)[idx]
    gap = np.array(gap)[idx]; sigma = np.array(sigma)[idx]; sem = np.array(sem)[idx]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6.4), sharex=True,
                                   gridspec_kw={"height_ratios": [1.2, 1]})
    # Panel a: raw bg and gb tunnel values
    ax1.plot(J, bg, "o-", color="#1f77b4", label="(β, γ) tunnel", lw=1.6, ms=6)
    ax1.plot(J, gb, "s-", color="#d62728", label="(γ, β) tunnel", lw=1.6, ms=6)
    ax1.axhline(0.5, color="grey", lw=0.6, ls="--", alpha=0.6)
    ax1.set_ylabel(r"|⟨u$_A$|v$_B$⟩|")
    ax1.legend(loc="upper left", frameon=False, fontsize=9)
    ax1.set_title("(a) Tunnel coherence per ordered-pair family vs J", loc="left")
    ax1.set_ylim(0.35, 0.60)

    # Panel b: directional gap with 3σ shaded band
    ax2.errorbar(J, gap, yerr=sem, fmt="o-", color="#2ca02c", lw=1.6, ms=6,
                 capsize=3, label="directional gap")
    ax2.axhline(0, color="black", lw=0.6)
    ax2.fill_between(J, -3 * sem, 3 * sem, alpha=0.18, color="grey",
                     label=r"±3σ band")
    # Mark nulls
    for Jn in [0.15, 0.70]:
        ax2.axvline(Jn, color="grey", lw=0.7, ls=":", alpha=0.7)
    ax2.text(0.15, -0.11, "null", fontsize=8, color="grey",
             rotation=90, ha="right", va="top")
    ax2.text(0.70, -0.11, "null", fontsize=8, color="grey",
             rotation=90, ha="right", va="top")
    ax2.set_xlabel("J  (tunnel strength, iSWAP$^J$ exponent per internal step)")
    ax2.set_ylabel(r"gap = |⟨u$_A$|v$_B$⟩|($\beta$,$\gamma$) − |⟨u$_A$|v$_B$⟩|($\gamma$,$\beta$)")
    ax2.legend(loc="lower right", frameon=False, fontsize=9)
    ax2.set_title("(b) Directional gap vs J (sign flips, oscillation)",
                  loc="left")

    fig.suptitle(
        "Figure 2.  J-dependence of the directional tunnel gap  (n = 2, p = 0.005, Cirq).\n"
        "Signal robust across most J values; two specific nulls at J ≈ 0.15, 0.70 avoidable in hardware tuning.",
        fontsize=10, y=1.01,
    )
    fig.tight_layout()
    out = FIG / "fig2_J_sweep.png"
    fig.savefig(out, bbox_inches="tight", dpi=200)
    plt.close(fig)
    print(f"wrote {out}")


# =============================================================================
#  Figure 3 — n vs noise-channel significance table
# =============================================================================
def figure_3():
    # n sweep (from stress_n file)
    n_src = sorted(RESULTS.glob("stress_n_cirq_*.json"))[-1]
    n_data = json.loads(n_src.read_text())
    n_vals = []; n_sigma = []
    for k, v in n_data["results"].items():
        n_vals.append(int(k.split("=")[1]))
        n_sigma.append(v["sigma"])
    idx = np.argsort(n_vals)
    n_vals = np.array(n_vals)[idx]; n_sigma = np.array(n_sigma)[idx]

    # Noise sweeps at n=1 and n=2
    noise_files = sorted(RESULTS.glob("stress_noise_aer_*.json"))
    noise_data = {}
    for f in noise_files:
        d = json.loads(f.read_text())
        key = d["n_periods"]
        noise_data[key] = d["results"]

    noise_channels = list(noise_data[2].keys())
    channel_pretty = {
        "ideal":                 "ideal (no noise)",
        "depolarizing(0.005)":   "depolarising 0.005",
        "amp_damp(0.005)":       "amplitude damping 0.005",
        "phase_damp(0.005)":     "phase damping 0.005",
        "amp_and_phase(0.005)":  "amp + phase damping",
        "fake(sherbrooke)":      "FakeSherbrooke (Eagle r3)",
    }

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.5, 4.4),
                                   gridspec_kw={"width_ratios": [1, 1.55]})

    # Panel a: n-dependence, Cirq, p=0.005 depolarising
    bars = ax1.bar(n_vals, np.abs(n_sigma), color=["#2ca02c" if abs(s) > 3 else "#cccccc"
                                                   for s in n_sigma],
                   edgecolor="black", linewidth=0.6)
    ax1.axhline(3, color="red", lw=1, ls="--", alpha=0.7, label="3σ threshold")
    ax1.set_xlabel("n  (Coxeter periods)")
    ax1.set_ylabel(r"|directional gap / SEM|")
    ax1.set_xticks(n_vals)
    ax1.set_title("(a) Signal significance vs horizon n\n(J = 0.1, p = 0.005, Cirq)", loc="left")
    ax1.legend(frameon=False, fontsize=8, loc="upper right")
    # Annotate max
    max_i = int(np.argmax(np.abs(n_sigma)))
    ax1.annotate(f"max |σ| = {abs(n_sigma[max_i]):.1f}\nat n = {n_vals[max_i]}",
                 xy=(n_vals[max_i], abs(n_sigma[max_i])),
                 xytext=(n_vals[max_i] + 1, abs(n_sigma[max_i]) - 3),
                 arrowprops=dict(arrowstyle="->", color="black", lw=0.7),
                 fontsize=9)

    # Panel b: n x noise heatmap
    sigma_matrix = np.zeros((len(noise_channels), 2))
    for j, n_p in enumerate([2, 1]):
        for i, ch in enumerate(noise_channels):
            sigma_matrix[i, j] = abs(noise_data[n_p][ch]["sigma"])

    # Order: n=1 first, then n=2 in the visual
    sigma_matrix = sigma_matrix[:, [1, 0]]
    col_labels = ["n = 1", "n = 2"]

    # For color scaling, clip heatmap so FakeSherbrooke still visible
    # Use log10 with floor of 1
    disp = np.log10(np.clip(sigma_matrix, 1, 200))
    im = ax2.imshow(disp, aspect="auto", cmap="viridis", vmin=0, vmax=np.log10(200))
    ax2.set_xticks([0, 1]); ax2.set_xticklabels(col_labels)
    ax2.set_yticks(range(len(noise_channels)))
    ax2.set_yticklabels([channel_pretty.get(c, c) for c in noise_channels],
                        fontsize=9)
    # Annotate each cell
    for i in range(len(noise_channels)):
        for j in range(2):
            val = sigma_matrix[i, j]
            color = "white" if disp[i, j] > 1.1 else "black"
            tag  = "✓" if val >= 3 else "✗"
            ax2.text(j, i, f"{tag}  {val:.1f}σ", ha="center", va="center",
                     color=color, fontsize=9, fontweight="bold")
    ax2.set_title("(b) Directional-gap significance across (n, noise channel)",
                  loc="left")
    cbar = plt.colorbar(im, ax=ax2, fraction=0.04, pad=0.03)
    cbar.set_label("log₁₀(|σ|)", fontsize=9)

    fig.suptitle(
        "Figure 3.  Signal survival across horizon and noise channel.\n"
        "n = 1 is the hardware-viable operating point; FakeSherbrooke "
        "(Eagle r3 calibrated) passes at 6.4σ.",
        fontsize=10, y=1.03,
    )
    fig.tight_layout()
    out = FIG / "fig3_n_noise.png"
    fig.savefig(out, bbox_inches="tight", dpi=200)
    plt.close(fig)
    print(f"wrote {out}")


if __name__ == "__main__":
    figure_1()
    figure_2()
    figure_3()
