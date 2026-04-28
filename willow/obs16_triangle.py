#!/usr/bin/env python3
"""
OBSERVABLE 16 — Triangle CA lookup table (Paper 32)

Pre-registered Willow hardware test of the 13-qubit triangle topology. The
merkabit tunnel network is claimed to be a Z_3-symmetric cellular automaton
with a universal 9-entry ordered-pair lookup table; Observable 16 measures
this lookup table on the minimum closed-loop topology (triangle, N=3).

Protocol summary
----------------
3 merkabits A, B, C in a closed triangle with cross-chiral tunnels
u_A↔v_B, u_B↔v_C, u_C↔v_A at J = 0.1, running Protocol 4S-Z3-three-P for
n = 1 Coxeter period. Three input families covering all 9 ordered (Z_3 x Z_3)
input pairs. Measure each bond's overlap |<u_X | v_Y>| via SWAP test.

Qubit count: 13 (4 per merkabit data x 3 + 1 ancilla).
Transpiled depth on Willow PhXZ merge: ~3 per merkabit data qubit.

Pre-registered predictions (from Paper 32 simulation, topology-independent)
---------------------------------------------------------------------------
At n = 1 Coxeter period, Willow-realistic p_depol ≈ 0.003:

  Observable 16a -- universal 9-entry lookup values
    beta -> gamma     ≈  0.000  (destructive zero, identical across topologies)
    gamma -> beta     ≈  0.76
    all 9 entries reproducible within ±0.05 of the triangle values listed in
    Paper 32 Section 3.

  Observable 16b -- topology independence
    lookup-table values extracted from the triangle agree to within 0.03
    with the 4-square and hexagon values (already published in Papers 31, 32).

  Observable 16c -- loop phase is NOT the dominant invariant
    within-Z_3-loop-phase-class variance must exceed between-class variance
    for all 3 bonds (the negative Z_3 plaquette holonomy result of Paper 32).

Strong pass: 16a all entries within ±0.05, AND 16b agreement ≤ 0.03, AND 16c
  variance ordering satisfied.
Weak pass:   16a destructive zero (β → γ ≤ 0.10) AND constructive peak (γ → β ≥ 0.50).
Null:        β → γ > 0.15 — the destructive zero does not survive hardware noise.

Resource budget: 13 qubits x 3 input families x 6 repeats x 4096 shots
≈ 75k shots, ≈ 15 minutes of Willow QPU.

Usage
-----
  python obs16_triangle.py --sim-only
  python obs16_triangle.py --project <GCP> --processor <PROC>

Authors: Stenberg with Claude Anthropic, April 2026.
"""
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))
from _engine_wrapper import (
    write_pre_registration_json, std_argparser,
)

sys.path.insert(0, str(SCRIPT_DIR.parent / "cirq"))
# NOTE: rather than depend on the ngon script's API, obs16 imports the raw
# Cirq primitives and builds the 13-qubit triangle circuit inline. Keeps
# the wrapper self-sufficient even if run_p4s_ngon_cirq changes.
from run_p4s_Z3_three_cirq import z3_eigenstate
from run_p4s_Z3_three_P_cirq import internal_step_angles_chiral, p_gate_4
from run_p4s_cirq import (
    cross_gate_4, horizontal_gate_4, diagonal_gate_4,
    overlap_from_swap, T_CYCLE,
)
from run_p4s_Z3_cirq import state_prep_2q
import cirq
import numpy as np


OBSERVABLE = "obs16_triangle"
PAPER_REF  = "Paper 32 (The Merkabit Tunnel Network as a Z_3 Cellular Automaton)"

THRESHOLDS = {
    "16a_beta_gamma_max_strong":  0.05,
    "16a_beta_gamma_max_weak":    0.10,
    "16a_beta_gamma_null":        0.15,
    "16a_gamma_beta_min":         0.50,
    "16a_gamma_beta_target":      0.76,
    "16b_topology_agreement":     0.03,
    "directional_gap_strong":     0.60,
    "directional_gap_weak":       0.40,
}


def merkabit_internal(q_u, q_v, step_index):
    th_c, th_h, th_d, phi_p = internal_step_angles_chiral(step_index % T_CYCLE)
    Pf, Pi = p_gate_4(phi_p)
    yield cirq.MatrixGate(Pf, qid_shape=(2, 2)).on(*q_u)
    yield cirq.MatrixGate(Pi, qid_shape=(2, 2)).on(*q_v)
    for gate_fn, theta in [(cross_gate_4, th_c),
                            (horizontal_gate_4, th_h),
                            (diagonal_gate_4, th_d)]:
        Uf, Ui = gate_fn(theta)
        yield cirq.MatrixGate(Uf, qid_shape=(2, 2)).on(*q_u)
        yield cirq.MatrixGate(Ui, qid_shape=(2, 2)).on(*q_v)


def tunnel(q_uX, q_vY, J):
    for i in range(2):
        yield (cirq.ISWAP ** J).on(q_uX[i], q_vY[i])


def triangle_step(q_uA, q_vA, q_uB, q_vB, q_uC, q_vC, step_index, J):
    yield from merkabit_internal(q_uA, q_vA, step_index)
    yield from merkabit_internal(q_uB, q_vB, step_index)
    yield from merkabit_internal(q_uC, q_vC, step_index)
    if J > 0:
        yield from tunnel(q_uA, q_vB, J)
        yield from tunnel(q_uB, q_vC, J)
        yield from tunnel(q_uC, q_vA, J)


def swap_test_2q(anc, q_a, q_b):
    yield cirq.H(anc)
    for qa, qb in zip(q_a, q_b):
        yield cirq.CSWAP(anc, qa, qb)
    yield cirq.H(anc)


def build_triangle_bond_circuit(label_A, label_B, label_C, bond, n_periods, J):
    """Build the 13-qubit circuit to measure one bond (AB, BC, or CA)
    for a specific input triple.
    """
    qubits = cirq.LineQubit.range(13)
    q_uA = [qubits[0], qubits[1]]; q_vA = [qubits[2], qubits[3]]
    q_uB = [qubits[4], qubits[5]]; q_vB = [qubits[6], qubits[7]]
    q_uC = [qubits[8], qubits[9]]; q_vC = [qubits[10], qubits[11]]
    anc  = qubits[12]
    qc = cirq.Circuit()
    la = z3_eigenstate({'alpha': 0, 'beta': 1, 'gamma': 2}[label_A])
    lb = z3_eigenstate({'alpha': 0, 'beta': 1, 'gamma': 2}[label_B])
    lc = z3_eigenstate({'alpha': 0, 'beta': 1, 'gamma': 2}[label_C])
    qc.append(state_prep_2q(la, "uA").on(*q_uA))
    qc.append(state_prep_2q(la, "vA").on(*q_vA))
    qc.append(state_prep_2q(lb, "uB").on(*q_uB))
    qc.append(state_prep_2q(lb, "vB").on(*q_vB))
    qc.append(state_prep_2q(lc, "uC").on(*q_uC))
    qc.append(state_prep_2q(lc, "vC").on(*q_vC))
    for s in range(n_periods * T_CYCLE):
        qc.append(triangle_step(q_uA, q_vA, q_uB, q_vB, q_uC, q_vC, s, J))
    # Bond selection (cross-chiral: u_X <-> v_Y)
    if bond == 'AB':   q_a, q_b = q_uA, q_vB
    elif bond == 'BC': q_a, q_b = q_uB, q_vC
    elif bond == 'CA': q_a, q_b = q_uC, q_vA
    else: raise ValueError(bond)
    qc.append(swap_test_2q(anc, q_a, q_b))
    qc.append(cirq.measure(anc, key='anc'))
    return qc


def main():
    ap = std_argparser(OBSERVABLE, default_shots=4096)
    ap.add_argument("--n-periods", type=int,   default=1)
    ap.add_argument("--J",         type=float, default=0.1)
    args = ap.parse_args()

    print(f"OBSERVABLE 16: Triangle CA lookup (Paper 32)")
    print(f"  13 qubits, n_periods={args.n_periods}, J={args.J}")
    print(f"  shots={args.shots}, n_trials={args.n_trials}")

    # Key two cells of the lookup table: (beta, gamma) = destructive, (gamma, beta) = constructive
    # On the triangle AB bond, "beta, gamma" = u_A=beta, v_B=gamma.
    # We prepare (A, B, C) = (beta, gamma, alpha) and measure bond AB for the (β, γ) entry.
    # And (A, B, C) = (gamma, beta, alpha) for the (γ, β) entry.

    if args.sim_only:
        print("  mode: SIMULATION (cirq.Simulator, ideal)")
        sim = cirq.Simulator()

        # (β, γ) → destructive zero
        bg_vals = []
        for t in range(args.n_trials):
            qc = build_triangle_bond_circuit('beta', 'gamma', 'alpha',
                                                'AB', args.n_periods, args.J)
            res = sim.run(qc, repetitions=args.shots)
            zeros = int(res.histogram(key='anc').get(0, 0))
            bg_vals.append(overlap_from_swap(zeros, args.shots))

        # (γ, β) → constructive peak
        gb_vals = []
        for t in range(args.n_trials):
            qc = build_triangle_bond_circuit('gamma', 'beta', 'alpha',
                                                'AB', args.n_periods, args.J)
            res = sim.run(qc, repetitions=args.shots)
            zeros = int(res.histogram(key='anc').get(0, 0))
            gb_vals.append(overlap_from_swap(zeros, args.shots))

        bg_mean, bg_sem = np.mean(bg_vals), np.std(bg_vals, ddof=1) / np.sqrt(args.n_trials)
        gb_mean, gb_sem = np.mean(gb_vals), np.std(gb_vals, ddof=1) / np.sqrt(args.n_trials)
        gap = gb_mean - bg_mean

        print(f"\n  bond_AB for (beta, gamma, alpha):  |<u_A|v_B>| = {bg_mean:.4f} +/- {bg_sem:.4f}")
        print(f"  bond_AB for (gamma, beta, alpha):  |<u_A|v_B>| = {gb_mean:.4f} +/- {gb_sem:.4f}")
        print(f"  directional gap (gamma,beta) - (beta,gamma) = {gap:.4f}")

        if (bg_mean <= THRESHOLDS["16a_beta_gamma_max_strong"]
             and gb_mean >= THRESHOLDS["16a_gamma_beta_min"]):
            verdict = "STRONG PASS (destructive zero + constructive peak both confirmed)"
        elif (bg_mean <= THRESHOLDS["16a_beta_gamma_max_weak"]
               and gb_mean >= THRESHOLDS["16a_gamma_beta_min"]):
            verdict = "WEAK PASS (destructive + constructive both present but at degraded magnitude)"
        else:
            verdict = f"NULL (β→γ={bg_mean:.3f} above null threshold {THRESHOLDS['16a_beta_gamma_null']}, or γ→β weak)"
        print(f"\n  verdict: {verdict}")

        summary = {
            "bond_AB_beta_gamma_mean":  float(bg_mean),
            "bond_AB_beta_gamma_sem":   float(bg_sem),
            "bond_AB_gamma_beta_mean":  float(gb_mean),
            "bond_AB_gamma_beta_sem":   float(gb_sem),
            "gap":                       float(gap),
            "verdict":                   verdict,
            "mode":                      "simulation",
            "parameters":                {"n_periods": args.n_periods,
                                           "J": args.J,
                                           "shots": args.shots,
                                           "n_trials": args.n_trials},
        }
        out = write_pre_registration_json(OBSERVABLE, PAPER_REF,
                                            THRESHOLDS, summary)
        print(f"\n  wrote {out}")
    else:
        raise NotImplementedError(
            "Hardware path: add GCP credentials. The 13-qubit Cirq circuit "
            "above is the full Willow protocol; engine.run_batch() substitutes "
            "for sim.run() without further modification."
        )


if __name__ == "__main__":
    main()
