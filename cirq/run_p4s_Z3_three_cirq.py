#!/usr/bin/env python3
"""
Protocol 4S-Z3-three: test ternary (not just binary) memory on the tesseract.

Protocol 4S-Z3-short established that the substrate distinguishes matched
inputs (A, B, D -> attractor ~ 0.67) from orthogonal inputs (C -> 0.34)
at short horizons under Willow-realistic noise. That is a BINARY memory:
one bit of input information (alignment-class) survives.

This experiment tests whether the substrate distinguishes three Z_3
eigenstate classes -- the minimum requirement for TRUE ternary memory.

Z_3 action on C^4: T |0> = |1>, T |1> = |2>, T |2> = |0>, T |3> = |3>.
Three eigenstates of T on the span{|0>, |1>, |2>}:

  alpha  (Z_3 eigenvalue 1):    (|0> + |1>   + |2>)  / sqrt(3)
  beta   (Z_3 eigenvalue omega):(|0> + omega |1> + omega^2 |2>) / sqrt(3)
  gamma  (Z_3 eigenvalue omega^2): (|0> + omega^2 |1> + omega |2>) / sqrt(3)

Five families total (three Z_3 eigenstates plus two references from the
previous test):

  A      u = v = |0>                       (matched basis, reference)
  C      u = |0>, v = |3>                  (orthogonal basis, reference)
  alpha  u = v = |ψ_1>                     (Z_3 eigenvalue 1)
  beta   u = v = |ψ_omega>                 (Z_3 eigenvalue omega)
  gamma  u = v = |ψ_omega^2>               (Z_3 eigenvalue omega^2)

Hypothesis test at each (n_periods, p_depol) cell: compute the pairwise
mean-distance between all C(5, 2) = 10 family pairs, and identify which
pairs are separated beyond shot noise.

Ternary-memory confirmation requires: alpha, beta, gamma pairwise
separable by more than 3 standard errors, at a horizon where noise
does not erase the signal.

Usage: python run_p4s_Z3_three_cirq.py
"""
import argparse
import json
import math
import sys
from datetime import datetime
from pathlib import Path
from itertools import combinations

import numpy as np
import cirq

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))
from run_p4s_Z3_cirq import build_snapshot, state_prep_2q, T_CYCLE
from run_p4s_cirq import inject_depolarize, overlap_from_swap

RESULTS_DIR = SCRIPT_DIR.parent / "results"

OMEGA = complex(math.cos(2 * math.pi / 3), math.sin(2 * math.pi / 3))


# ============================================================================
#  Five initial-state families
# ============================================================================
def basis_state(n: int) -> np.ndarray:
    v = np.zeros(4, dtype=complex)
    v[n] = 1.0
    return v


def z3_eigenstate(eigenvalue_power: int) -> np.ndarray:
    """Z_3 eigenstate on span{|0>, |1>, |2>}.
    eigenvalue_power in {0, 1, 2} corresponds to T-eigenvalue {1, omega, omega^2}.
    Construction: for T-eigenvalue lambda, the eigenvector is
      (1/sqrt(3)) * sum_k lambda^-k |k>
    so that T|psi> = lambda |psi>.
    """
    k = eigenvalue_power % 3
    coeffs = np.array([
        1.0,
        OMEGA ** (-k),
        OMEGA ** (-2 * k),
        0.0,
    ], dtype=complex)
    return coeffs / math.sqrt(3)


def make_families():
    return {
        "A_matched_basis_0":  (basis_state(0),     basis_state(0)),
        "C_orthog_0_3":       (basis_state(0),     basis_state(3)),
        "alpha_Z3_1":         (z3_eigenstate(0),   z3_eigenstate(0)),
        "beta_Z3_omega":      (z3_eigenstate(1),   z3_eigenstate(1)),
        "gamma_Z3_omega2":    (z3_eigenstate(2),   z3_eigenstate(2)),
    }


def measure_single_horizon(u0, v0, n_periods, p_depol, n_repeats=10, shots=4096):
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

    periods = [2, 3, 5]
    noise = [0.0, 0.001, 0.002, 0.005]
    families = make_families()

    print("Protocol 4S-Z3-three | 5 families (A, C, alpha, beta, gamma)")
    print(f"periods={periods}  noise={noise}  n_repeats={args.n_repeats}  shots={args.shots}")

    results = {}
    for n_p in periods:
        results[str(n_p)] = {}
        for p in noise:
            print(f"\n[n_periods={n_p}, p_depol={p:.4f}]")
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
                print(f"  {fname:22s}  mean={cells[fname]['mean']:.4f}  "
                      f"sem={cells[fname]['sem']:.4f}")
            # Pairwise distances
            pairs = {}
            for a, b in combinations(families.keys(), 2):
                gap = cells[a]["mean"] - cells[b]["mean"]
                sem_tot = math.sqrt(cells[a]["sem"] ** 2 + cells[b]["sem"] ** 2)
                ratio = gap / max(sem_tot, 1e-9)
                pairs[f"{a}__vs__{b}"] = {
                    "gap":       gap,
                    "sem_total": sem_tot,
                    "gap_over_sem": ratio,
                }
            results[str(n_p)][str(p)] = {"cells": cells, "pairs": pairs}

            # Z_3-specific pairs at this cell
            print("  Z_3 ternary tests:")
            for a, b in [
                ("alpha_Z3_1",      "beta_Z3_omega"),
                ("alpha_Z3_1",      "gamma_Z3_omega2"),
                ("beta_Z3_omega",   "gamma_Z3_omega2"),
            ]:
                pkey = f"{a}__vs__{b}"
                pair = pairs[pkey]
                status = "PASS" if abs(pair["gap_over_sem"]) > 3 else "fail"
                print(f"    {a:22s} vs {b:22s}  "
                      f"gap={pair['gap']:+.4f}  sigma={pair['gap_over_sem']:+.2f}  [{status}]")

    # ===== Summary table: Z_3 ternary detection across (n, p) =====
    print("\n" + "=" * 78)
    print("  TERNARY MEMORY TEST: Are alpha, beta, gamma pairwise separable?")
    print("=" * 78)
    print(f"{'n_p':>4} {'p':>7} | {'|a-b|/sem':>11} {'|a-g|/sem':>11} {'|b-g|/sem':>11} | All > 3?")
    print("-" * 78)
    for n_p in periods:
        for p in noise:
            cell = results[str(n_p)][str(p)]["pairs"]
            ab = abs(cell["alpha_Z3_1__vs__beta_Z3_omega"]["gap_over_sem"])
            ag = abs(cell["alpha_Z3_1__vs__gamma_Z3_omega2"]["gap_over_sem"])
            bg = abs(cell["beta_Z3_omega__vs__gamma_Z3_omega2"]["gap_over_sem"])
            all_sep = min(ab, ag, bg) > 3
            print(f"{n_p:>4} {p:>7.4f} | {ab:>11.2f} {ag:>11.2f} {bg:>11.2f} | {'YES' if all_sep else 'no'}")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "stack":     "cirq",
        "n_repeats": args.n_repeats,
        "shots":     args.shots,
        "periods":   periods,
        "noise":     noise,
        "results":   results,
    }
    out = RESULTS_DIR / f"p4s_Z3_three_cirq_{datetime.now():%Y%m%dT%H%M%S}.json"
    out.write_text(json.dumps(payload, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
