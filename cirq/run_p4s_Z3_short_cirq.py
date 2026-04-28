#!/usr/bin/env python3
"""
Protocol 4S-Z3 short-horizon sweep: is there a viable ternary-memory window
on current superconducting hardware?

At 10 Coxeter periods and p_depol = 0.005 (Willow-realistic) the A-vs-C
alignment gap is fully thermalised to 0.005. The question this experiment
answers: does the gap survive at SHORTER horizons on the same hardware?

Sweep: (n_periods in {1, 2, 3, 5, 7, 10}) x (p_depol in {0, 0.001, 0.002, 0.005})
       x (family in {A matched basis, C orthogonal basis})
       x 10 repetitions x 4096 shots

For each (n_periods, p_depol) cell: measure the overlap at exactly n_periods
(no averaging over periods) for both A and C, then compute the gap |A - C|.

Reports the region of (n_periods, p_depol) space in which the gap exceeds
3 x standard error of the mean -- the minimum viable ternary-memory window.

Usage: python run_p4s_Z3_short_cirq.py
"""
import argparse
import json
import math
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import cirq

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))
from run_p4s_Z3_cirq import (
    state_prep_2q, basis_state, build_snapshot, T_CYCLE,
)
from run_p4s_cirq import inject_depolarize, overlap_from_swap

RESULTS_DIR = SCRIPT_DIR.parent / "results"


def measure_single_horizon(u0, v0, n_periods, p_depol, n_repeats=10, shots=4096):
    """Measure |<u|v>| at exactly n_periods Coxeter cycles (no intermediate
    snapshots). Returns the array of n_repeats overlaps."""
    sim = cirq.DensityMatrixSimulator() if p_depol > 0 else cirq.Simulator()
    overlaps = []
    for _ in range(n_repeats):
        circ = build_snapshot(u0, v0, n_periods * T_CYCLE)
        circ = inject_depolarize(circ, p_depol)
        result = sim.run(circ, repetitions=shots)
        zeros = int(result.histogram(key="anc").get(0, 0))
        overlaps.append(overlap_from_swap(zeros, shots))
    return np.array(overlaps)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-repeats", type=int, default=10)
    ap.add_argument("--shots", type=int, default=4096)
    args = ap.parse_args()

    periods = [1, 2, 3, 5, 7, 10]
    noise = [0.0, 0.001, 0.002, 0.005]
    families = {
        "A_matched_basis_0": (basis_state(0), basis_state(0)),
        "C_orthog_0_3":      (basis_state(0), basis_state(3)),
    }

    print("Protocol 4S-Z3 short-horizon sweep")
    print(f"periods={periods}  noise={noise}  n_repeats={args.n_repeats}  shots={args.shots}")
    print()
    print(f"{'n_periods':>9} {'p_depol':>8} | {'A mean':>7} {'A SEM':>7} | {'C mean':>7} {'C SEM':>7} | {'gap':>7} {'gap/SEM_tot':>11}")
    print("-" * 87)

    results = {}
    for n_p in periods:
        results[str(n_p)] = {}
        for p in noise:
            cells = {}
            for fname, (u0, v0) in families.items():
                arr = measure_single_horizon(u0, v0, n_p, p,
                                             n_repeats=args.n_repeats,
                                             shots=args.shots)
                cells[fname] = {
                    "values": arr.tolist(),
                    "mean":   float(np.mean(arr)),
                    "std":    float(np.std(arr, ddof=1)),
                    "sem":    float(np.std(arr, ddof=1) / math.sqrt(args.n_repeats)),
                }
            ma = cells["A_matched_basis_0"]["mean"]
            mc = cells["C_orthog_0_3"]["mean"]
            sa = cells["A_matched_basis_0"]["sem"]
            sc = cells["C_orthog_0_3"]["sem"]
            gap = ma - mc
            sem_tot = math.sqrt(sa ** 2 + sc ** 2)
            ratio = gap / max(sem_tot, 1e-9)
            print(f"{n_p:>9d} {p:>8.4f} | {ma:>7.4f} {sa:>7.4f} | {mc:>7.4f} {sc:>7.4f} | {gap:>7.4f} {ratio:>11.2f}")
            results[str(n_p)][str(p)] = {
                "A": cells["A_matched_basis_0"],
                "C": cells["C_orthog_0_3"],
                "gap": gap,
                "sem_total": sem_tot,
                "gap_over_sem": ratio,
            }

    print()
    print("Viability heatmap (gap/SEM > 3 means the alignment signal is detectable):")
    print("(rows = periods, cols = p_depol)")
    header = "  " + " ".join(f"{p:>7.3f}" for p in noise)
    print(f"{'':>10}{header}")
    for n_p in periods:
        row = [results[str(n_p)][str(p)]["gap_over_sem"] for p in noise]
        cells_str = " ".join(f"{'PASS' if abs(r) > 3 else 'fail':>7s}" for r in row)
        print(f"{n_p:>10d}  {cells_str}")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "stack": "cirq",
        "n_repeats": args.n_repeats,
        "shots":     args.shots,
        "periods":   periods,
        "noise":     noise,
        "results":   results,
    }
    out = RESULTS_DIR / f"p4s_Z3_short_cirq_{datetime.now():%Y%m%dT%H%M%S}.json"
    out.write_text(json.dumps(payload, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
