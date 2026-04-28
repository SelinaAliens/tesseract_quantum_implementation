#!/usr/bin/env python3
"""
Protocol 4S-Z3 noise sweep - characterise the alignment-invariant threshold

At p = 0 the four initial-state families separate into two clusters:
  A, B, D (matched initial overlap 1):  attractor ~ 0.67
  C (orthogonal initial overlap 0):      attractor ~ 0.34

At p = 0.005 (Willow-realistic) both clusters collapse to ~0.49 (Haar-random
expectation for d = 4). This sweep maps where the thermalisation happens
by running only Family A and Family C across a fine-grained noise ladder.

Usage:
  python run_p4s_Z3_noise_sweep.py
"""
import math, sys, json
from datetime import datetime
from pathlib import Path
import numpy as np
import cirq

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))
from run_p4s_Z3_cirq import (
    state_prep_2q, basis_state, bell_like,
    build_snapshot, T_CYCLE,
)
from run_p4s_cirq import inject_depolarize, overlap_from_swap

RESULTS_DIR = SCRIPT_DIR.parent / "results"


def run_one(u0, v0, p_depol, n_periods=10, shots=8192, n_repeats=5):
    sim = cirq.DensityMatrixSimulator() if p_depol > 0 else cirq.Simulator()
    overlaps = np.zeros((n_repeats, n_periods))
    for rep in range(n_repeats):
        for period in range(1, n_periods + 1):
            circ = build_snapshot(u0, v0, period * T_CYCLE)
            circ = inject_depolarize(circ, p_depol)
            result = sim.run(circ, repetitions=shots)
            zeros = int(result.histogram(key="anc").get(0, 0))
            overlaps[rep, period - 1] = overlap_from_swap(zeros, shots)
    return overlaps


def main():
    noise_levels = [0.0, 0.00005, 0.0002, 0.0005, 0.001, 0.002, 0.005]
    families = {
        "A_matched_basis_0": (basis_state(0), basis_state(0)),
        "C_orthog_0_3":      (basis_state(0), basis_state(3)),
    }

    print(f"{'p_depol':>10} | {'A mean':>7} {'A std':>7} | {'C mean':>7} {'C std':>7} | {'gap |A-C|':>9}")
    print("-" * 78)

    all_results = {}
    for p in noise_levels:
        row = {}
        for fname, (u0, v0) in families.items():
            overlaps = run_one(u0, v0, p_depol=p, n_repeats=5, shots=4096)
            last5 = overlaps[:, -5:]
            row[fname] = {
                "mean": float(np.mean(last5)),
                "std":  float(np.std(last5)),
            }
        gap = abs(row["A_matched_basis_0"]["mean"] - row["C_orthog_0_3"]["mean"])
        print(f"{p:>10.5f} | "
              f"{row['A_matched_basis_0']['mean']:>7.4f} {row['A_matched_basis_0']['std']:>7.4f} | "
              f"{row['C_orthog_0_3']['mean']:>7.4f} {row['C_orthog_0_3']['std']:>7.4f} | "
              f"{gap:>9.4f}")
        all_results[str(p)] = {"families": row, "gap": gap}

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "stack": "cirq",
        "noise_levels": noise_levels,
        "results": all_results,
    }
    out = RESULTS_DIR / f"p4s_Z3_noise_sweep_{datetime.now():%Y%m%dT%H%M%S}.json"
    out.write_text(json.dumps(payload, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
