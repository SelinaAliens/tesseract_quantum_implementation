#!/usr/bin/env python3
"""
Protocol 4S-Memory: does the 4-square substrate preserve content-specific
memory across many Coxeter periods?

Protocol 4S established that a single 4-spinor sustains |<u|v>| ~ 0.47
under internal dynamics alone. Protocol 4S-Tunnel established that the
2-merkabit tunnel carries directional ternary information. Protocol
4S-NGon established that each bond in a lattice is an independent 2-trit
gate with a universal lookup table.

All of those establish COHERENCE sustain. None of them establishes whether
specific INPUT CONTENT (a "memory") is preserved across many Coxeter
periods.

This experiment tests the content-memory claim:

  1. Prepare the 4-square lattice in a specific Z_3 label configuration
     (a "memory", e.g. (alpha, beta, gamma, alpha)).
  2. Let the internal chiral + tunnel dynamics run for n Coxeter periods.
  3. At each horizon n, measure all four perimeter bond values.
  4. Compare bond-pattern vectors across different memories.

If the bond patterns remain DISTINGUISHABLE across memories at large n,
content-memory persists and the substrate acts as a quantum
associative-memory register.

If bond patterns converge to a Haar-random-like common value across all
memories at large n, content is forgotten while coherence continues to
sustain — a partial result that would refine the self-sustaining claim
to "self-sustaining attractor, not self-sustaining memory."

Tested memories:
  M1  (alpha, beta,  gamma, alpha)
  M2  (alpha, gamma, beta,  alpha)    <- reversed interior
  M3  (beta,  gamma, alpha, beta)     <- shifted phase
  M4  (gamma, beta,  alpha, gamma)    <- third phase

Baseline: Haar-random initial states (same as Protocol 4S reference).

Usage:
  python run_p4s_memory_persistence_cirq.py

Output: per-horizon bond-pattern matrix + cross-memory distinguishability
metric + null baseline comparison.
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
from run_p4s_cirq import (
    cross_gate_4, horizontal_gate_4, diagonal_gate_4,
    overlap_from_swap, T_CYCLE,
)
from run_p4s_Z3_three_P_cirq import (
    p_gate_4, internal_step_angles_chiral,
)
from run_p4s_Z3_three_cirq import (
    basis_state, z3_eigenstate,
)
from run_p4s_Z3_cirq import state_prep_2q

RESULTS_DIR = SCRIPT_DIR.parent / "results"


# ============================================================================
#  4-square dynamics (reuse the ngon / 4square infrastructure)
# ============================================================================
def _append_internal_chiral(qc, q_u, q_v, step_idx, p_coupling=1.0):
    th_c, th_h, th_d, phi_p = internal_step_angles_chiral(
        step_idx % T_CYCLE, p_coupling=p_coupling)
    Cf, Ci = cross_gate_4(th_c)
    qc.append(cirq.MatrixGate(Cf, name="Cf").on(*q_u))
    qc.append(cirq.MatrixGate(Ci, name="Ci").on(*q_v))
    Hf, Hi = horizontal_gate_4(th_h)
    qc.append(cirq.MatrixGate(Hf, name="Hf").on(*q_u))
    qc.append(cirq.MatrixGate(Hi, name="Hi").on(*q_v))
    Df, Di = diagonal_gate_4(th_d)
    qc.append(cirq.MatrixGate(Df, name="Df").on(*q_u))
    qc.append(cirq.MatrixGate(Di, name="Di").on(*q_v))
    Pf, Pi = p_gate_4(phi_p)
    qc.append(cirq.MatrixGate(Pf, name="Pf").on(*q_u))
    qc.append(cirq.MatrixGate(Pi, name="Pi").on(*q_v))


def _tunnel_step(qc, q_u_from, q_v_to, J):
    if J == 0.0: return
    for i in range(2):
        qc.append((cirq.ISWAP ** J).on(q_u_from[i], q_v_to[i]))


def build_square_dynamics(states, n_periods, J=0.1, p_coupling=1.0):
    q = cirq.LineQubit.range(17)
    regs = {
        "uA": (q[0],  q[1]),  "vA": (q[2],  q[3]),
        "uB": (q[4],  q[5]),  "vB": (q[6],  q[7]),
        "uC": (q[8],  q[9]),  "vC": (q[10], q[11]),
        "uD": (q[12], q[13]), "vD": (q[14], q[15]),
    }
    anc = q[16]

    qc = cirq.Circuit()
    names = ["uA", "vA", "uB", "vB", "uC", "vC", "uD", "vD"]
    for nm, st in zip(names, states):
        qc.append(state_prep_2q(st, nm).on(*regs[nm]))

    steps = n_periods * T_CYCLE
    for k in range(steps):
        _append_internal_chiral(qc, regs["uA"], regs["vA"], k, p_coupling)
        _append_internal_chiral(qc, regs["uB"], regs["vB"], k, p_coupling)
        _append_internal_chiral(qc, regs["uC"], regs["vC"], k, p_coupling)
        _append_internal_chiral(qc, regs["uD"], regs["vD"], k, p_coupling)
        _tunnel_step(qc, regs["uA"], regs["vB"], J)
        _tunnel_step(qc, regs["uB"], regs["vC"], J)
        _tunnel_step(qc, regs["uC"], regs["vD"], J)
        _tunnel_step(qc, regs["uD"], regs["vA"], J)

    return qc, regs, anc


def _append_swap_test(qc, left_reg, right_reg, anc):
    qc.append(cirq.H(anc))
    qc.append(cirq.CSWAP(anc, left_reg[0], right_reg[0]))
    qc.append(cirq.CSWAP(anc, left_reg[1], right_reg[1]))
    qc.append(cirq.H(anc))
    qc.append(cirq.measure(anc, key="anc"))


BOND_PAIRS = [
    ("bond_AB", "uA", "vB"),
    ("bond_BC", "uB", "vC"),
    ("bond_CD", "uC", "vD"),
    ("bond_DA", "uD", "vA"),
]


def measure_bond(states, bond_name, n_periods, J=0.1, shots=2048):
    qc, regs, anc = build_square_dynamics(states, n_periods, J)
    pair = next(p for p in BOND_PAIRS if p[0] == bond_name)
    _append_swap_test(qc, regs[pair[1]], regs[pair[2]], anc)
    sim = cirq.Simulator()
    res = sim.run(qc, repetitions=shots)
    zeros = int(res.histogram(key="anc").get(0, 0))
    return overlap_from_swap(zeros, shots)


# ============================================================================
#  Memory patterns
# ============================================================================
def states_for_labels(labels):
    lookup = {
        "alpha": z3_eigenstate(0),
        "beta":  z3_eigenstate(1),
        "gamma": z3_eigenstate(2),
    }
    states = []
    for lab in labels:
        st = lookup[lab]
        states.append(st); states.append(st)   # u = v = same state (matched)
    return states


MEMORIES = {
    "M1_aβγa": ["alpha", "beta",  "gamma", "alpha"],
    "M2_aγβa": ["alpha", "gamma", "beta",  "alpha"],
    "M3_bγab": ["beta",  "gamma", "alpha", "beta"],
    "M4_gβag": ["gamma", "beta",  "alpha", "gamma"],
    "M5_aaaa": ["alpha", "alpha", "alpha", "alpha"],       # trivial uniform
    "M6_bβbβ": ["beta",  "beta",  "beta",  "beta"],         # uniform beta
}


# ============================================================================
#  Main
# ============================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-repeats", type=int, default=4)
    ap.add_argument("--shots",     type=int, default=2048)
    ap.add_argument("--J",         type=float, default=0.1)
    args = ap.parse_args()

    horizons = [1, 2, 3, 5, 10]
    memories = list(MEMORIES.keys())
    bonds    = [b[0] for b in BOND_PAIRS]

    total = len(horizons) * len(memories) * len(bonds) * args.n_repeats
    print(f"Protocol 4S-Memory  N=4, J={args.J}, n_repeats={args.n_repeats}, "
          f"shots={args.shots}, total circuits={total}")

    # [horizon][memory][bond] = {"mean": float, "sem": float, "values": [...]}
    results = {}
    for n_p in horizons:
        print(f"\n=== horizon n = {n_p} Coxeter period(s) ===")
        results[str(n_p)] = {}
        for mname in memories:
            labels = MEMORIES[mname]
            states = states_for_labels(labels)
            row = {}
            for bond in bonds:
                vals = []
                for _ in range(args.n_repeats):
                    vals.append(measure_bond(states, bond, n_p,
                                             J=args.J, shots=args.shots))
                arr = np.array(vals)
                row[bond] = {
                    "values": arr.tolist(),
                    "mean":   float(np.mean(arr)),
                    "sem":    float(np.std(arr, ddof=1) / math.sqrt(args.n_repeats))
                                if len(arr) > 1 else 0.0,
                }
            results[str(n_p)][mname] = row
            vals_str = "  ".join(f"{row[b]['mean']:.3f}" for b in bonds)
            print(f"  {mname}  {labels}  bonds = [{vals_str}]")

    # -----------------------------------------------------------------
    # Analysis: per-horizon memory discriminability
    # -----------------------------------------------------------------
    print("\n" + "=" * 78)
    print("  MEMORY DISCRIMINABILITY ANALYSIS")
    print("=" * 78)
    print("For each horizon, compute Euclidean distance between the 4-dim")
    print("bond-pattern vectors of every pair of memories.")
    print("Large pairwise distances => memories still distinguishable.\n")

    print(f"{'horizon':>8} | {'pair':<28} {'bond gap':>10} {'|Δ|':>6}")
    print("-" * 78)
    discriminability = {}
    for n_p in horizons:
        all_pairs = []
        for (m1, m2) in combinations(memories, 2):
            v1 = np.array([results[str(n_p)][m1][b]["mean"] for b in bonds])
            v2 = np.array([results[str(n_p)][m2][b]["mean"] for b in bonds])
            dist = float(np.linalg.norm(v1 - v2))
            all_pairs.append((m1, m2, dist))
        all_pairs.sort(key=lambda x: -x[2])
        # print the top 3 and bottom 3
        mean_dist = float(np.mean([p[2] for p in all_pairs]))
        max_dist  = float(max(p[2] for p in all_pairs))
        min_dist  = float(min(p[2] for p in all_pairs))
        discriminability[str(n_p)] = {
            "mean_pairwise_distance": mean_dist,
            "max_pairwise_distance":  max_dist,
            "min_pairwise_distance":  min_dist,
            "all_pairs": [{"m1": p[0], "m2": p[1], "dist": p[2]}
                          for p in all_pairs],
        }
        print(f"{n_p:>8} | {'(mean over pairs)':<28} "
              f"{mean_dist:>10.4f} {'':>6}")
        print(f"{'':>8} | {'largest':<28} "
              f"{max_dist:>10.4f}  ({all_pairs[0][0]} vs {all_pairs[0][1]})")
        print(f"{'':>8} | {'smallest':<28} "
              f"{min_dist:>10.4f}  ({all_pairs[-1][0]} vs {all_pairs[-1][1]})")
        print()

    # Discriminability vs horizon
    print("  Mean pairwise distance vs horizon:")
    print(f"  {'n':>4} : {'mean |Δ|':>10}   {'max |Δ|':>10}   {'min |Δ|':>10}")
    for n_p in horizons:
        d = discriminability[str(n_p)]
        print(f"  {n_p:>4} : {d['mean_pairwise_distance']:>10.4f}   "
              f"{d['max_pairwise_distance']:>10.4f}   "
              f"{d['min_pairwise_distance']:>10.4f}")

    # -----------------------------------------------------------------
    # Verdict
    # -----------------------------------------------------------------
    print("\n  VERDICT")
    d1   = discriminability[str(horizons[0])]["mean_pairwise_distance"]
    dlast = discriminability[str(horizons[-1])]["mean_pairwise_distance"]
    decay_ratio = dlast / d1 if d1 > 0 else 0
    print(f"  Distance at n={horizons[0]}: {d1:.4f}")
    print(f"  Distance at n={horizons[-1]}: {dlast:.4f}")
    print(f"  Ratio (late/early): {decay_ratio:.3f}")
    if decay_ratio > 0.5:
        print("  MEMORY PERSISTS:  content carried through to late horizon")
    elif decay_ratio > 0.15:
        print("  MEMORY PARTIAL:   content decays but not lost")
    else:
        print("  MEMORY LOST:      content washed out by late horizon")

    # -----------------------------------------------------------------
    # Save
    # -----------------------------------------------------------------
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp":  datetime.now().isoformat(timespec="seconds"),
        "stack":      "cirq",
        "J":          args.J,
        "n_repeats":  args.n_repeats,
        "shots":      args.shots,
        "horizons":   horizons,
        "memories":   {m: MEMORIES[m] for m in memories},
        "results":    results,
        "discriminability": discriminability,
    }
    out = RESULTS_DIR / f"p4s_memory_cirq_{datetime.now():%Y%m%dT%H%M%S}.json"
    out.write_text(json.dumps(payload, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
