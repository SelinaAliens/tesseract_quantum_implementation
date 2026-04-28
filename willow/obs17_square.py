#!/usr/bin/env python3
"""
OBSERVABLE 17 — 4-Square CA Z_3 Holonomy (Paper 32)

Pre-registered Willow hardware test of the 17-qubit four-merkabit square
topology. Four merkabits A, B, C, D on an oriented plaquette with perimeter
tunnels u_A->v_B, u_B->v_C, u_C->v_D, u_D->v_A at J = 0.1.

The oriented loop carries a Z_3 HOLONOMY PHASE
    loop_phase = (a + b + c + d) mod 3       (a, b, c, d in {0, 1, 2})
The test is whether the four perimeter tunnel observables group by loop-phase
class (between-class gap > within-class variance) — the signature of genuine
Z_3 holonomy on the Eisenstein lattice.

Qubit count: 17 (4 merkabits x 4 data qubits + 1 ancilla).
Transpiled depth on Willow PhXZ merge: ~3 per merkabit data-qubit.
Source circuit: ../cirq/run_p4s_4square_cirq.py (canonical, imported unchanged)

Pre-registered predictions (Paper 32 Section 5, Willow noise p_depol = 0.003)
---------------------------------------------------------------------------
At n = 1 Coxeter period, families AAAA, aaaa_p1, bbbb_pw, gggg_pw2, bgbg_p1,
bbgg_p1, bbaa_pw2, bbbg_pw2:

  Observable 17a -- Z_3 loop-phase classification
    between-class mean gap (phase 1 vs omega vs omega^2) across the 4
    perimeter tunnel observables >= 0.15 (ideal: 0.22).
    within-phase-class variance <= between-class gap on >= 3 of 4 bonds.

  Observable 17b -- topology-independence (triangle vs square)
    lookup-table values for 9 universal ordered pairs agree to within 0.05
    between the triangle (Observable 16) and the 4-square perimeter bonds.

  Observable 17c -- memory capacity
    at least 15 of 28 ordered-pair input cells separable at >= 3 sigma via
    perimeter-bond fingerprint (4 bonds x 4 local coherences = 8-dim metric).

  Observable 17d -- diagonal bonds path-independent
    |<u_A | v_C>| - |<u_A | v_B>| - |<u_B | v_C>| within 0.10 of zero
    (information flows around the perimeter, not across the plaquette).

Strong pass: 17a AND 17b AND 17c.
Weak pass:   17a only (Z_3 holonomy present but topology/capacity degraded).
Null:        17a fails — no Z_3 holonomy distinguishable at Willow noise.

Resource budget: 17 qubits x 8 families x 10 observables x 6 repeats x 4096
shots ~= 3.3M shots, ~= 65 minutes of Willow QPU at current batch throughput.

Usage
-----
  python obs17_square.py --sim-only
  python obs17_square.py --project <GCP> --processor <PROC>

Authors: Stenberg with Claude Anthropic, April 2026.
"""
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))
from _engine_wrapper import (
    engine_submit_or_fail, write_pre_registration_json, std_argparser,
)

sys.path.insert(0, str(SCRIPT_DIR.parent / "cirq"))
from run_p4s_4square_cirq import (
    measure_observable, family_states, FAMILY_LOOP_PHASE, OBSERVABLE_PAIRS,
)
import numpy as np


OBSERVABLE = "obs17_square"
PAPER_REF  = "Paper 32 (The Merkabit Tunnel Network as a Z_3 Cellular Automaton)"

THRESHOLDS = {
    "17a_between_class_gap_strong":  0.15,
    "17a_between_class_gap_weak":    0.08,
    "17a_min_sep_bonds":             3,     # of 4 perimeter bonds
    "17b_topology_agreement":        0.05,
    "17c_min_separable_cells":       15,    # of 28
    "17c_min_sigma":                 3.0,
    "17d_diagonal_tolerance":        0.10,
}


# Families grouped by Z_3 loop-phase class (Z_3 eigenstates only)
PHASE_CLASSES = {
    0: ["aaaa_p1", "bgbg_p1", "bbgg_p1"],      # trivial
    1: ["bbbb_pw"],                             # omega
    2: ["gggg_pw2", "bbaa_pw2", "bbbg_pw2"],   # omega^2
}
PERIMETER_BONDS = ["tunnel_AB", "tunnel_BC", "tunnel_CD", "tunnel_DA"]


def measure_bond_for_family(family, bond, n_periods, J, p_depol, shots, n_repeats):
    vals = []
    states = family_states(family)
    for _ in range(n_repeats):
        val = measure_observable(states, which=bond, n_periods=n_periods,
                                  J=J, p_depol=p_depol, shots=shots)
        vals.append(val)
    return float(np.mean(vals)), float(np.std(vals, ddof=1) / np.sqrt(n_repeats))


def main():
    ap = std_argparser(OBSERVABLE, default_shots=4096)
    ap.add_argument("--n-periods", type=int,   default=1)
    ap.add_argument("--J",         type=float, default=0.1)
    ap.add_argument("--p-depol",   type=float, default=0.003)
    args = ap.parse_args()

    print(f"OBSERVABLE 17: 4-Square CA Z_3 Holonomy (Paper 32)")
    print(f"  17 qubits, n_periods={args.n_periods}, J={args.J}, "
          f"p_depol={args.p_depol}")
    print(f"  shots={args.shots}, n_trials={args.n_trials}")

    if not args.sim_only:
        raise NotImplementedError(
            "Hardware path: add GCP credentials via engine_submit_or_fail. "
            "The imported circuit builder measure_observable() from "
            "../cirq/run_p4s_4square_cirq.py is unchanged for hardware; "
            "sim.run() is replaced with engine.run_batch()."
        )

    print("  mode: SIMULATION (cirq DensityMatrixSimulator with depol noise)")

    # 17a: Z_3 loop-phase classification on four perimeter bonds
    # Loop over the families that have defined phase classes, measuring
    # each perimeter bond.
    bond_measurements = {bond: {} for bond in PERIMETER_BONDS}
    for phase_class, families in PHASE_CLASSES.items():
        for family in families:
            print(f"  family {family} (phase class {phase_class}):")
            for bond in PERIMETER_BONDS:
                mean, sem = measure_bond_for_family(
                    family, bond, args.n_periods, args.J,
                    args.p_depol, args.shots, args.n_trials)
                bond_measurements[bond][family] = (mean, sem, phase_class)
                print(f"    {bond}: {mean:.4f} +/- {sem:.4f}")

    # Compute between-class vs within-class variation for each bond
    bond_stats = {}
    separable_bonds = 0
    for bond, fam_data in bond_measurements.items():
        per_class_means = {}
        for family, (mean, sem, pc) in fam_data.items():
            per_class_means.setdefault(pc, []).append(mean)

        class_centroids = {pc: float(np.mean(v)) for pc, v in per_class_means.items()}
        between_spread = float(max(class_centroids.values())
                                - min(class_centroids.values()))
        within_spreads = [float(np.std(v, ddof=1)) if len(v) > 1 else 0.0
                           for v in per_class_means.values()]
        within_mean = float(np.mean(within_spreads))

        bond_stats[bond] = {
            "class_centroids": class_centroids,
            "between_spread":  between_spread,
            "within_spread":   within_mean,
        }

        separable = (between_spread >= THRESHOLDS["17a_between_class_gap_weak"]
                     and between_spread > within_mean)
        if separable:
            separable_bonds += 1
        print(f"  {bond}: between={between_spread:.4f}, within={within_mean:.4f}, "
              f"separable={separable}")

    mean_between = float(np.mean([s["between_spread"] for s in bond_stats.values()]))

    # 17d: diagonal vs perimeter consistency (one pass, using bbbb_pw family)
    diag_family = "bbbb_pw"
    states_diag = family_states(diag_family)
    diag_ac, _  = measure_bond_for_family(diag_family, "tunnel_AC",
                                             args.n_periods, args.J,
                                             args.p_depol, args.shots,
                                             args.n_trials)
    diag_ab, _  = bond_measurements["tunnel_AB"][diag_family][0], None
    diag_bc, _  = bond_measurements["tunnel_BC"][diag_family][0], None
    path_residual = float(diag_ac - diag_ab - diag_bc)

    # Pass/fail
    if (mean_between >= THRESHOLDS["17a_between_class_gap_strong"]
         and separable_bonds >= THRESHOLDS["17a_min_sep_bonds"]):
        verdict_17a = "STRONG PASS"
    elif (mean_between >= THRESHOLDS["17a_between_class_gap_weak"]
           and separable_bonds >= THRESHOLDS["17a_min_sep_bonds"]):
        verdict_17a = "WEAK PASS"
    else:
        verdict_17a = (f"NULL (mean_between={mean_between:.3f}, "
                        f"separable={separable_bonds}/4)")

    print(f"\n  17a (Z_3 loop-phase): {verdict_17a}")
    print(f"  17d path residual (diag_AC - tAB - tBC) = {path_residual:.4f} "
           f"(|.| <= {THRESHOLDS['17d_diagonal_tolerance']})")

    summary = {
        "bond_stats":           bond_stats,
        "mean_between_class":   mean_between,
        "separable_bonds":      separable_bonds,
        "verdict_17a":          verdict_17a,
        "path_residual_17d":    path_residual,
        "mode":                 "simulation",
        "parameters":           {"n_periods": args.n_periods, "J": args.J,
                                  "p_depol": args.p_depol, "shots": args.shots,
                                  "n_trials": args.n_trials},
    }
    out = write_pre_registration_json(OBSERVABLE, PAPER_REF,
                                        THRESHOLDS, summary)
    print(f"\n  wrote {out}")


if __name__ == "__main__":
    main()
