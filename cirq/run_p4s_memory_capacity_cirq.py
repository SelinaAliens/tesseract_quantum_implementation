#!/usr/bin/env python3
"""
Protocol 4S-Memory-Capacity: how many mutually distinguishable memories
can the 4-square merkabit substrate hold?

Follow-up to the memory-persistence experiment. The persistence result
showed that six specific memories remain distinguishable for at least
ten Coxeter periods. This experiment asks the capacity question: across
the full space of 3^4 = 81 possible Z_3-eigenstate configurations on a
4-site ring, how many can be stored simultaneously with all pairs above
a specified distinguishability threshold?

The capacity is defined as N(D), where N is the maximum number of memories
that can be mutually separated by Euclidean bond-vector distance ≥ D.
A complete N(D) curve characterises the register's information capacity
vs SNR tradeoff.

Protocol:
  - Enumerate all 81 possible (site_0, site_1, site_2, site_3) assignments
    with each site in {alpha, beta, gamma}.
  - For each pattern, measure the 4-bond fingerprint at n = 3 Coxeter
    periods (peak distinguishability from the persistence study).
  - State-vector simulation (p_depol = 0); 4,096 shots per bond per
    pattern (shot noise only, no unitary variance).
  - Analyse: pairwise distance distribution, greedy maximum-distance
    packing for each threshold.

Usage: python run_p4s_memory_capacity_cirq.py
"""
import argparse
import json
import math
import sys
from datetime import datetime
from pathlib import Path
from itertools import product, combinations

import numpy as np
import cirq

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))
from run_p4s_memory_persistence_cirq import (
    build_square_dynamics, _append_swap_test, BOND_PAIRS, states_for_labels,
)
from run_p4s_cirq import overlap_from_swap

RESULTS_DIR = SCRIPT_DIR.parent / "results"

N_SITES = 4
LABELS  = ["alpha", "beta", "gamma"]
SHORT   = {"alpha": "a", "beta": "b", "gamma": "g"}


def measure_bond(states, bond_name, n_periods, J=0.1, shots=4096):
    qc, regs, anc = build_square_dynamics(states, n_periods, J)
    pair = next(p for p in BOND_PAIRS if p[0] == bond_name)
    _append_swap_test(qc, regs[pair[1]], regs[pair[2]], anc)
    sim = cirq.Simulator()
    res = sim.run(qc, repetitions=shots)
    zeros = int(res.histogram(key="anc").get(0, 0))
    return overlap_from_swap(zeros, shots)


def enumerate_patterns():
    patterns = []
    for combo in product(LABELS, repeat=N_SITES):
        patterns.append(list(combo))
    return patterns


def pattern_name(labels):
    return "".join(SHORT[l] for l in labels)


# ============================================================================
#  Capacity analysis
# ============================================================================
def greedy_max_packing(distance_matrix, threshold):
    """Greedy selection of patterns with all pairwise distances >= threshold.

    Starts from the pair with the largest distance, then greedily adds the
    pattern whose minimum distance to the selected set is as large as
    possible, provided that minimum is >= threshold.
    Returns the selected index set.
    """
    n = distance_matrix.shape[0]
    # Start from the globally max pair
    flat = distance_matrix.copy(); np.fill_diagonal(flat, -1)
    i, j = divmod(int(np.argmax(flat)), n)
    if distance_matrix[i, j] < threshold:
        return []
    selected = [i, j]
    remaining = set(range(n)) - set(selected)
    while remaining:
        best, best_mindist = None, -1
        for k in remaining:
            mindist = min(distance_matrix[k, s] for s in selected)
            if mindist >= threshold and mindist > best_mindist:
                best, best_mindist = k, mindist
        if best is None:
            break
        selected.append(best)
        remaining.discard(best)
    return selected


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots",     type=int,   default=4096)
    ap.add_argument("--n-periods", type=int,   default=3)
    ap.add_argument("--J",         type=float, default=0.1)
    args = ap.parse_args()

    patterns = enumerate_patterns()
    bonds = [b[0] for b in BOND_PAIRS]
    total = len(patterns) * len(bonds)
    print(f"Protocol 4S-Memory-Capacity  n={args.n_periods}, J={args.J}, "
          f"shots={args.shots}")
    print(f"Patterns to measure: {len(patterns)}  "
          f"× {len(bonds)} bonds = {total} circuit runs\n")

    fingerprints = np.zeros((len(patterns), len(bonds)))
    for i, labels in enumerate(patterns):
        states = states_for_labels(labels)
        for j, bond in enumerate(bonds):
            fingerprints[i, j] = measure_bond(states, bond,
                                              n_periods=args.n_periods,
                                              J=args.J, shots=args.shots)
        if (i + 1) % 10 == 0 or i == len(patterns) - 1:
            print(f"  [{i+1:3d}/{len(patterns)}] {pattern_name(labels):>4} "
                  f"-> bond vector {np.round(fingerprints[i], 3).tolist()}")

    # Pairwise distance matrix
    D = np.linalg.norm(fingerprints[:, None, :] - fingerprints[None, :, :], axis=2)

    # Distribution of pairwise distances
    upper = D[np.triu_indices(len(patterns), k=1)]
    print(f"\nPairwise distance distribution over {len(upper)} unordered pairs:")
    print(f"  min     : {upper.min():.4f}")
    print(f"  median  : {np.median(upper):.4f}")
    print(f"  mean    : {upper.mean():.4f}")
    print(f"  max     : {upper.max():.4f}")
    print(f"  std     : {upper.std():.4f}")

    # Capacity at several thresholds
    print(f"\nCapacity N(D): maximum-packing size with all pairs >= distance D")
    print(f"{'threshold D':>12} | {'capacity N':>12} | "
          f"{'example memories (first 10)':<40}")
    thresholds = [0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.00]
    capacity_table = []
    selected_examples = {}
    for D_thresh in thresholds:
        selected = greedy_max_packing(D, D_thresh)
        capacity = len(selected)
        names = [pattern_name(patterns[i]) for i in selected[:10]]
        capacity_table.append({"D": D_thresh, "N": capacity,
                               "examples": [pattern_name(patterns[i])
                                            for i in selected]})
        if D_thresh in (0.30, 0.50, 0.70):
            selected_examples[f"D={D_thresh}"] = [pattern_name(patterns[i])
                                                   for i in selected]
        print(f"{D_thresh:>12.2f} | {capacity:>12d} | "
              f"{' '.join(names):<40}")

    # Save
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp":     datetime.now().isoformat(timespec="seconds"),
        "stack":         "cirq",
        "J":             args.J,
        "n_periods":     args.n_periods,
        "shots":         args.shots,
        "n_patterns":    len(patterns),
        "patterns":      [pattern_name(p) for p in patterns],
        "bonds":         bonds,
        "fingerprints":  fingerprints.tolist(),
        "distance_stats": {
            "min":    float(upper.min()),
            "median": float(np.median(upper)),
            "mean":   float(upper.mean()),
            "max":    float(upper.max()),
            "std":    float(upper.std()),
        },
        "capacity_table": capacity_table,
    }
    out = RESULTS_DIR / f"p4s_memory_capacity_cirq_{datetime.now():%Y%m%dT%H%M%S}.json"
    out.write_text(json.dumps(payload, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
