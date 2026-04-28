#!/usr/bin/env python3
"""
Protocol 4S-Tunnel: cross-chiral tunnel between two tesseract merkabits.

All prior protocols in this repo test a single merkabit. The framework's
actual computational claims live at the inter-merkabit level: adjacent
merkabits share a permanent R_inter torsion axis (base paper, Paper 20),
and the resulting "tunnel" is trit-selective and cross-chiral --
the forward spinor of merkabit A couples to the inverse spinor of
merkabit B.

This experiment asks: does the tunnel carry ternary information that
neither merkabit holds alone? If yes, inter-merkabit correlation may
be a more robust computational primitive than single-merkabit memory.

## Setup

Two 4-spinor merkabits A and B. Eight data qubits: (u_A = q0,q1),
(v_A = q2,q3), (u_B = q4,q5), (v_B = q6,q7). One ancilla q8 for SWAP
test.

## Dynamics per internal step

1. Internal chiral step on A (cross + horizontal + diagonal + P gate)
2. Internal chiral step on B (same)
3. Tunnel step: partial SWAP between (u_A) and (v_B) with angle J
   -- cross-chiral exchange of forward-A and inverse-B spinors.

J = tunnel strength (0 = no tunnel, 1 = full SWAP). Default J = 0.1
models weak coupling between adjacent lattice sites (J/r ~ 0.1 for
r = 1 in natural units).

## Three overlap measurements per snapshot

The SWAP test destroys the state, so each snapshot needs three separate
circuit runs measuring:

  local_A   = |<u_A|v_A>|    -- does A remember its own input?
  local_B   = |<u_B|v_B>|    -- does B remember its own input?
  tunnel    = |<u_A|v_B>|    -- does the cross-chiral channel encode
                                 information?

## Hypothesis

If tunnel coherence distinguishes (beta, gamma) from (gamma, beta)
input pairs while local coherences do not, the tunnel encodes
directional ternary correlation that is inaccessible to either local
merkabit alone.

If tunnel coherence is also more robust to noise than local coherence,
the cross-chiral channel is a decoherence-protected subspace --
ternary computation may live in the tunnel, not in the tesseract.

## Families (6 input pairs)

  AA   (A, A)          both matched basis |0> -- baseline product state
  bb   (beta, beta)    both Z_3 = omega
  gg   (gamma, gamma)  both Z_3 = omega^2
  bg   (beta, gamma)   mixed Z_3 labels, B-then-C order
  gb   (gamma, beta)   mixed Z_3 labels, reversed
  aa   (alpha, alpha)  both Z_3 = 1 (real self-dual), reference

Usage:
  python run_p4s_tunnel_cirq.py --sim-only
  python run_p4s_tunnel_cirq.py --sim-only --J 0.2 --n-repeats 5
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
    inject_depolarize, overlap_from_swap, T_CYCLE,
)
from run_p4s_Z3_three_P_cirq import (
    p_gate_4, internal_step_angles_chiral,
)
from run_p4s_Z3_three_cirq import (
    basis_state, z3_eigenstate, OMEGA,
)
from run_p4s_Z3_cirq import state_prep_2q

RESULTS_DIR = SCRIPT_DIR.parent / "results"


# ============================================================================
#  Cross-chiral tunnel: partial SWAP between u_A and v_B
# ============================================================================
def tunnel_step(qc: cirq.Circuit, q_uA, q_vB, J: float):
    """Apply a J-weighted cross-chiral exchange between the u_A and v_B
    registers. For each qubit pair (u_A[i], v_B[i]), apply iSWAP^J,
    which is the coherent partial-SWAP with exchange angle J."""
    if J == 0.0:
        return
    # iSWAP^t applied qubit-wise between corresponding qubits of u_A and v_B
    for i in range(2):
        qc.append((cirq.ISWAP ** J).on(q_uA[i], q_vB[i]))


# ============================================================================
#  Build a dynamics circuit (state prep + internal + tunnel; no measurement)
# ============================================================================
def _append_internal_chiral_on(qc, q_u, q_v, step_idx, p_coupling=1.0):
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


def build_dynamics(u0_A, v0_A, u0_B, v0_B, steps_so_far: int,
                   J: float = 0.1, p_coupling: float = 1.0):
    """Build the 9-qubit circuit (8 data + 1 ancilla) up to the chosen
    step count, WITHOUT appending the SWAP test (so it can be combined
    with different SWAP-test choices)."""
    q = cirq.LineQubit.range(9)
    q_uA = (q[0], q[1]); q_vA = (q[2], q[3])
    q_uB = (q[4], q[5]); q_vB = (q[6], q[7])
    anc  = q[8]

    qc = cirq.Circuit()
    qc.append(state_prep_2q(u0_A, "uA").on(*q_uA))
    qc.append(state_prep_2q(v0_A, "vA").on(*q_vA))
    qc.append(state_prep_2q(u0_B, "uB").on(*q_uB))
    qc.append(state_prep_2q(v0_B, "vB").on(*q_vB))

    for k in range(steps_so_far):
        _append_internal_chiral_on(qc, q_uA, q_vA, k, p_coupling=p_coupling)
        _append_internal_chiral_on(qc, q_uB, q_vB, k, p_coupling=p_coupling)
        tunnel_step(qc, q_uA, q_vB, J)

    return qc, q_uA, q_vA, q_uB, q_vB, anc


def append_swap_test(qc: cirq.Circuit, q_left, q_right, anc):
    """SWAP test between two 2-qubit spinor registers, using one ancilla."""
    qc.append(cirq.H(anc))
    qc.append(cirq.CSWAP(anc, q_left[0], q_right[0]))
    qc.append(cirq.CSWAP(anc, q_left[1], q_right[1]))
    qc.append(cirq.H(anc))
    qc.append(cirq.measure(anc, key="anc"))


def measure_overlap(u0_A, v0_A, u0_B, v0_B, which: str, n_periods: int,
                    J: float, p_depol: float, p_coupling: float = 1.0,
                    shots: int = 4096) -> float:
    """which in {'local_A', 'local_B', 'tunnel'} selects the SWAP-test target.
       local_A = |<u_A|v_A>|, local_B = |<u_B|v_B>|, tunnel = |<u_A|v_B>|."""
    qc, q_uA, q_vA, q_uB, q_vB, anc = build_dynamics(
        u0_A, v0_A, u0_B, v0_B, n_periods * T_CYCLE,
        J=J, p_coupling=p_coupling)

    if which == "local_A":
        append_swap_test(qc, q_uA, q_vA, anc)
    elif which == "local_B":
        append_swap_test(qc, q_uB, q_vB, anc)
    elif which == "tunnel":
        append_swap_test(qc, q_uA, q_vB, anc)
    else:
        raise ValueError(f"unknown which: {which}")

    qc = inject_depolarize(qc, p_depol)
    sim = cirq.DensityMatrixSimulator() if p_depol > 0 else cirq.Simulator()
    res = sim.run(qc, repetitions=shots)
    zeros = int(res.histogram(key="anc").get(0, 0))
    return overlap_from_swap(zeros, shots)


# ============================================================================
#  Families (pairs of 4D states)
# ============================================================================
def make_pair_families():
    b0 = basis_state(0)
    b3 = basis_state(3)
    alpha = z3_eigenstate(0)
    beta  = z3_eigenstate(1)
    gamma = z3_eigenstate(2)

    def pair(uA, vA, uB, vB):
        return (uA, vA, uB, vB)

    return {
        "AA_matched":       pair(b0, b0, b0, b0),
        "aa_Z3_1_both":     pair(alpha, alpha, alpha, alpha),
        "bb_Z3_omega_both": pair(beta,  beta,  beta,  beta),
        "gg_Z3_w2_both":    pair(gamma, gamma, gamma, gamma),
        "bg_cross_fwd":     pair(beta,  beta,  gamma, gamma),
        "gb_cross_rev":     pair(gamma, gamma, beta,  beta),
    }


# ============================================================================
#  Main
# ============================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-repeats", type=int, default=6)
    ap.add_argument("--shots",     type=int, default=4096)
    ap.add_argument("--n-periods", type=int, default=2)
    ap.add_argument("--J",         type=float, default=0.1,
                    help="tunnel strength (iSWAP exponent per step)")
    ap.add_argument("--p-coupling", type=float, default=1.0)
    args = ap.parse_args()

    noise = [0.0, 0.005]
    families = make_pair_families()
    overlap_types = ["local_A", "local_B", "tunnel"]

    print(f"Protocol 4S-Tunnel | {len(families)} pairs | J={args.J} "
          f"n_periods={args.n_periods} n_repeats={args.n_repeats}")

    results = {}
    for p_depol in noise:
        print(f"\n=== p_depol = {p_depol:.4f} ===")
        results[str(p_depol)] = {}
        for fname, (uA, vA, uB, vB) in families.items():
            row = {}
            for which in overlap_types:
                vals = []
                for _ in range(args.n_repeats):
                    vals.append(measure_overlap(
                        uA, vA, uB, vB, which,
                        n_periods=args.n_periods, J=args.J,
                        p_depol=p_depol, p_coupling=args.p_coupling,
                        shots=args.shots))
                arr = np.array(vals)
                row[which] = {
                    "values": arr.tolist(),
                    "mean":   float(np.mean(arr)),
                    "std":    float(np.std(arr, ddof=1)),
                    "sem":    float(np.std(arr, ddof=1) / math.sqrt(args.n_repeats)),
                }
            results[str(p_depol)][fname] = row
            print(f"  {fname:22s}  "
                  f"local_A={row['local_A']['mean']:.3f}±{row['local_A']['sem']:.3f}  "
                  f"local_B={row['local_B']['mean']:.3f}±{row['local_B']['sem']:.3f}  "
                  f"tunnel ={row['tunnel' ]['mean']:.3f}±{row['tunnel' ]['sem']:.3f}")

    # === Directional tunnel asymmetry test (the key result) ===
    print("\n" + "=" * 78)
    print("  DIRECTIONAL TEST: does tunnel see (beta, gamma) vs (gamma, beta)?")
    print("=" * 78)
    print(f"{'p_depol':>8} | {'bg tunnel':>12} {'gb tunnel':>12} {'gap':>8} {'sigma':>7}")
    print("-" * 78)
    for p_depol in noise:
        bg = results[str(p_depol)]["bg_cross_fwd"]["tunnel"]
        gb = results[str(p_depol)]["gb_cross_rev"]["tunnel"]
        gap = bg["mean"] - gb["mean"]
        sem_tot = math.sqrt(bg["sem"] ** 2 + gb["sem"] ** 2)
        sig = gap / max(sem_tot, 1e-9)
        status = "DIRECTIONAL" if abs(sig) > 3 else "symmetric"
        print(f"{p_depol:>8.4f} | {bg['mean']:>12.4f} {gb['mean']:>12.4f} "
              f"{gap:>+8.4f} {sig:>+7.2f}  [{status}]")

    # === Tunnel-vs-local discrimination: compare how many classes each sees ===
    print("\n" + "=" * 78)
    print("  Classes visible to each observable (pairwise-separable @ 3 sigma)")
    print("=" * 78)
    for p_depol in noise:
        print(f"\n  p_depol = {p_depol}")
        for which in overlap_types:
            separated = 0
            total = 0
            for (a, b) in combinations(families.keys(), 2):
                ra = results[str(p_depol)][a][which]
                rb = results[str(p_depol)][b][which]
                gap = abs(ra["mean"] - rb["mean"])
                sem_tot = math.sqrt(ra["sem"] ** 2 + rb["sem"] ** 2)
                if gap / max(sem_tot, 1e-9) > 3:
                    separated += 1
                total += 1
            print(f"    {which:8s}  {separated}/{total} pairs separable")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp":  datetime.now().isoformat(timespec="seconds"),
        "stack":      "cirq",
        "n_repeats":  args.n_repeats,
        "shots":      args.shots,
        "n_periods":  args.n_periods,
        "J":          args.J,
        "p_coupling": args.p_coupling,
        "noise":      noise,
        "results":    results,
    }
    out = RESULTS_DIR / f"p4s_tunnel_cirq_{datetime.now():%Y%m%dT%H%M%S}.json"
    out.write_text(json.dumps(payload, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
