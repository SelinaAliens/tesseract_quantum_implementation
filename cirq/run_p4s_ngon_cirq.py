#!/usr/bin/env python3
"""
Protocol 4S-NGon: N tesseract merkabits on a closed ring with N cross-chiral
perimeter tunnels.

Generalizes the 4-square experiment to arbitrary ring size N. Primary
targets: N=3 (triangle, Eisenstein-native unit) and N=6 (hexagon, the
natural cell on the hexagonal/Eisenstein lattice).

Topology (ring of N merkabits, oriented):
  A_0 -> A_1 -> A_2 -> ... -> A_{N-1} -> A_0

Each tunnel: u_{A_i} <-> v_{A_{i+1 mod N}} (cross-chiral)

Qubits: 4N + 1 (ancilla). N=3 -> 13, N=4 -> 17, N=6 -> 25.

State vector sim is used (p_depol=0 only for this script). For noise,
density-matrix sim at N >= 5 is computationally prohibitive.

Observables:
  * N local coherences  |<u_i|v_i>|
  * N perimeter tunnels |<u_i|v_{i+1}>|

(Diagonals omitted for simplicity; they could be added.)

Families: parametrized by a Z_3 label sequence over N sites.

Usage:
  python run_p4s_ngon_cirq.py --N 3 --n-repeats 4 --shots 2048
  python run_p4s_ngon_cirq.py --N 6 --n-repeats 3 --shots 1024
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


def build_ngon_circuit(states, N, n_periods, J=0.1, p_coupling=1.0):
    """states: list of 2N 4-vectors [u_0, v_0, u_1, v_1, ..., u_{N-1}, v_{N-1}]."""
    assert len(states) == 2 * N
    q = cirq.LineQubit.range(4 * N + 1)
    regs = {}
    for i in range(N):
        regs[f"u{i}"] = (q[4 * i],     q[4 * i + 1])
        regs[f"v{i}"] = (q[4 * i + 2], q[4 * i + 3])
    anc = q[4 * N]

    qc = cirq.Circuit()
    for i in range(N):
        qc.append(state_prep_2q(states[2 * i],     f"u{i}").on(*regs[f"u{i}"]))
        qc.append(state_prep_2q(states[2 * i + 1], f"v{i}").on(*regs[f"v{i}"]))

    steps = n_periods * T_CYCLE
    for k in range(steps):
        for i in range(N):
            _append_internal_chiral(qc, regs[f"u{i}"], regs[f"v{i}"], k, p_coupling)
        for i in range(N):
            j = (i + 1) % N
            _tunnel_step(qc, regs[f"u{i}"], regs[f"v{j}"], J)

    return qc, regs, anc


def _append_swap_test(qc, left, right, anc):
    qc.append(cirq.H(anc))
    qc.append(cirq.CSWAP(anc, left[0], right[0]))
    qc.append(cirq.CSWAP(anc, left[1], right[1]))
    qc.append(cirq.H(anc))
    qc.append(cirq.measure(anc, key="anc"))


def measure_observable(states, N, which, n_periods=1, J=0.1, shots=4096):
    qc, regs, anc = build_ngon_circuit(states, N, n_periods, J)
    if which.startswith("local_"):
        i = int(which.split("_")[1])
        _append_swap_test(qc, regs[f"u{i}"], regs[f"v{i}"], anc)
    elif which.startswith("tunnel_"):
        i = int(which.split("_")[1])
        j = (i + 1) % N
        _append_swap_test(qc, regs[f"u{i}"], regs[f"v{j}"], anc)
    else:
        raise ValueError(f"bad observable {which}")
    sim = cirq.Simulator()
    res = sim.run(qc, repetitions=shots)
    zeros = int(res.histogram(key="anc").get(0, 0))
    return overlap_from_swap(zeros, shots)


# ============================================================================
#  Family definitions (parametrised by Z_3 label sequence over N sites)
# ============================================================================
def states_for_labels(labels):
    """labels: list of 'alpha'/'beta'/'gamma'/'basis0' of length N.
    Returns 2N 4-vectors [u_0, v_0, u_1, v_1, ..., u_{N-1}, v_{N-1}]
    where u_i = v_i = the site's eigenstate (matched)."""
    lookup = {
        "alpha": z3_eigenstate(0),
        "beta":  z3_eigenstate(1),
        "gamma": z3_eigenstate(2),
        "basis0": basis_state(0),
    }
    states = []
    for lab in labels:
        st = lookup[lab]
        states.append(st); states.append(st)
    return states


def z3_sum(labels):
    Z3 = {"alpha": 0, "beta": 1, "gamma": 2, "basis0": None}
    vals = [Z3[l] for l in labels]
    if any(v is None for v in vals):
        return None
    return sum(vals) % 3


def triangle_families():
    """N=3: all three bonds see distinct (u, v) pairs. Tests ordered Z_3 labels on triangle."""
    return {
        "aaa":   ["alpha", "alpha", "alpha"],
        "bbb":   ["beta",  "beta",  "beta"],
        "ggg":   ["gamma", "gamma", "gamma"],
        "abg":   ["alpha", "beta",  "gamma"],  # forward Z_3 rotation
        "gba":   ["gamma", "beta",  "alpha"],  # reversed
        "bga":   ["beta",  "gamma", "alpha"],  # cyclic forward
        "agb":   ["alpha", "gamma", "beta"],   # cyclic reverse
    }


def hexagon_families():
    """N=6: natural Eisenstein cell. Tests hexagonal Z_3 labelings."""
    return {
        "aaaaaa":   ["alpha"] * 6,
        "bbbbbb":   ["beta"]  * 6,
        "gggggg":   ["gamma"] * 6,
        "abgabg":   ["alpha", "beta", "gamma", "alpha", "beta", "gamma"],
        "gbagba":   ["gamma", "beta", "alpha", "gamma", "beta", "alpha"],
        "bgbgbg":   ["beta", "gamma"] * 3,
        "bgabga":   ["beta", "gamma", "alpha", "beta", "gamma", "alpha"],
    }


# ============================================================================
#  Main
# ============================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--N",         type=int,   required=True, choices=[3, 4, 6])
    ap.add_argument("--n-repeats", type=int,   default=4)
    ap.add_argument("--shots",     type=int,   default=2048)
    ap.add_argument("--n-periods", type=int,   default=1)
    ap.add_argument("--J",         type=float, default=0.1)
    args = ap.parse_args()

    if args.N == 3:
        families = triangle_families()
    elif args.N == 6:
        families = hexagon_families()
    else:
        raise ValueError(f"Supply N=3 or N=6 (got {args.N})")

    # observables: N local + N perimeter tunnels
    observables = [f"local_{i}" for i in range(args.N)] + \
                  [f"tunnel_{i}" for i in range(args.N)]

    print(f"Protocol 4S-NGon  N={args.N}  ({4*args.N+1} qubits)  "
          f"J={args.J}  n_periods={args.n_periods}  "
          f"n_repeats={args.n_repeats}  shots={args.shots}")
    print(f"families = {len(families)}   observables = {len(observables)}   "
          f"total circuits = {len(families) * len(observables) * args.n_repeats}\n")

    results = {}
    for fname, labels in families.items():
        states = states_for_labels(labels)
        row = {
            "labels": labels,
            "z3_sum_mod_3": z3_sum(labels),
            "observables": {},
        }
        for which in observables:
            vals = []
            for _ in range(args.n_repeats):
                vals.append(measure_observable(
                    states, args.N, which,
                    n_periods=args.n_periods, J=args.J, shots=args.shots))
            arr = np.array(vals)
            row["observables"][which] = {
                "values": arr.tolist(),
                "mean":   float(np.mean(arr)),
                "sem":    float(np.std(arr, ddof=1) / math.sqrt(args.n_repeats)) if len(arr) > 1 else 0.0,
            }
        results[fname] = row
        print(f"  [{fname:10s} labels {labels} Z₃ sum {row['z3_sum_mod_3']}]")
        perim = ", ".join(f"{row['observables'][f'tunnel_{i}']['mean']:.3f}"
                          for i in range(args.N))
        locs  = ", ".join(f"{row['observables'][f'local_{i}']['mean']:.3f}"
                          for i in range(args.N))
        print(f"    local:    [{locs}]")
        print(f"    tunnels:  [{perim}]")

    # Bond analysis: for each bond i, which families produce zeros?
    print("\n" + "=" * 78)
    print("  BOND-LEVEL DIRECTIONAL ANALYSIS")
    print("=" * 78)
    print(f"{'family':>12} " +
          "".join(f"| bond_{i}→{(i+1)%args.N}(u:v)       " for i in range(args.N)))
    for fname, row in results.items():
        labels = row["labels"]
        cells = []
        for i in range(args.N):
            j = (i + 1) % args.N
            pair_desc = f"{labels[i][0]}->{labels[j][0]}"
            val = row["observables"][f"tunnel_{i}"]["mean"]
            marker = "*" if val < 0.05 else ""
            cells.append(f"{pair_desc:>6}={val:.2f}{marker} ")
        print(f"{fname:>12} " + " ".join(cells))
    print("\n  * = zero-class bond (|overlap| < 0.05)")

    # Save
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp":  datetime.now().isoformat(timespec="seconds"),
        "stack":      "cirq",
        "topology":   f"{args.N}-gon ring with cross-chiral perimeter tunnels",
        "N":          args.N,
        "n_qubits":   4 * args.N + 1,
        "n_periods":  args.n_periods,
        "J":          args.J,
        "n_repeats":  args.n_repeats,
        "shots":      args.shots,
        "results":    results,
    }
    out = RESULTS_DIR / f"p4s_{args.N}gon_cirq_{datetime.now():%Y%m%dT%H%M%S}.json"
    out.write_text(json.dumps(payload, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
