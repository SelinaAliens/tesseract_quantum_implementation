#!/usr/bin/env python3
"""
Protocol 4S-Compute-Store -- 22-qubit Cirq simulation of the three-layer
merkabit quantum computing architecture (Paper 35).

Minimum viable three-layer stack -- user specification:
    * a tunnel requires two merkabits (Paper 31)
    * the minimum compute cell is THREE merkabits in a closed triangle
      (Paper 32: this is Observable 16's topology; it has 3 cross-chiral
       tunnels forming the minimum closed loop for a Z_3 CA)

Qubit layout (22 qubits):
  COMPUTE (triangle of 3 merkabits, 12 qubits):
    A:  q0,q1   u_A      q2,q3   v_A
    B:  q4,q5   u_B      q6,q7   v_B
    C:  q8,q9   u_C      q10,q11 v_C
    Cross-chiral tunnels (Paper 31 rule u_X <-> v_Y on the triangle edges):
      AB edge:  u_A <-> v_B
      BC edge:  u_B <-> v_C
      CA edge:  u_C <-> v_A    (closes the triangle)

  COMMUNICATE (horizon-crossing tunnel, compute -> store):
    u_C  -iSWAP^J_inter-> u_env (left 2 qubits of envelope forward spinor)

  STORE (one 8-spinor octonion merkabit, 6 qubits):
    q12,q13,q14   u_env   (forward -- T_75-saturated interior)
    q15,q16,q17   v_env   (backward -- boundary record)

  READOUT (3 reference qubits + 1 ancilla):
    q18,q19,q20   reference (target label lifted to C^8)
    q21           SWAP-test ancilla

Write-compute-store-read cycle:
  1. Prepare compute A, B, C in labels L_A, L_B, L_C.
  2. Run compute triangle ouroboros with Paper 31 cross-chiral tunnels on
     all three edges for n_compute Coxeter periods. The Z_3 cellular
     automaton executes on the triangle.
  3. Inter-layer write: iSWAP^J_inter between u_C and u_env[0..1].
     The forward spinor of the last compute stage is captured into the
     envelope interior.
  4. Run envelope 8-spinor ouroboros for n_envelope Coxeter periods.
  5. Prepare reference from L_C (the compute cell's last-stage output label).
  6. SWAP test reference against u_env (direct) and v_env (boundary).

Falsifier: STORE (tunnel applied) > CONTROL (tunnel skipped) at both readouts.
Observable 21 strong pass: BOUNDARY gap >= 3 sigma with store fidelity >= 0.5.

Usage:
  python run_p4s_compute_store_cirq.py --label-C alpha
  python run_p4s_compute_store_cirq.py --label-A alpha --label-B beta --label-C gamma
  python run_p4s_compute_store_cirq.py --n-trials 10 --shots 2048
"""
from __future__ import annotations
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

from run_p4s_Z3_three_P_cirq import internal_step_angles_chiral, p_gate_4
from run_p4s_cirq import (
    cross_gate_4, horizontal_gate_4, diagonal_gate_4,
    overlap_from_swap, T_CYCLE,
)
from run_p4s_Z3_three_cirq import z3_eigenstate
from run_p4s_Z3_cirq import state_prep_2q
from run_p4s_octonion_cirq import (
    ouroboros_unitaries as octo_ouroboros_unitaries,
    state_prep_ops as octo_state_prep_ops,
    T_CYCLE as OCTO_T_CYCLE,
)

RESULTS_DIR = SCRIPT_DIR.parent / "results"

# 22-qubit layout
U_A, V_A = [0, 1], [2, 3]
U_B, V_B = [4, 5], [6, 7]
U_C, V_C = [8, 9], [10, 11]
U_ENV = [12, 13, 14]
V_ENV = [15, 16, 17]
REF   = [18, 19, 20]
ANCILLA = 21


def compute_merkabit_internal(q_u, q_v, step_index, p_coupling=1.0):
    th_c, th_h, th_d, phi_p = internal_step_angles_chiral(
        step_index % T_CYCLE, p_coupling=p_coupling)
    Pf, Pi = p_gate_4(phi_p)
    yield cirq.MatrixGate(Pf, qid_shape=(2, 2)).on(*q_u)
    yield cirq.MatrixGate(Pi, qid_shape=(2, 2)).on(*q_v)
    for gate_fn, theta in [(cross_gate_4, th_c),
                            (horizontal_gate_4, th_h),
                            (diagonal_gate_4, th_d)]:
        Uf, Ui = gate_fn(theta)
        yield cirq.MatrixGate(Uf, qid_shape=(2, 2)).on(*q_u)
        yield cirq.MatrixGate(Ui, qid_shape=(2, 2)).on(*q_v)


def cross_chiral_tunnel_2q(q_uX, q_vY, J):
    """Paper 31: iSWAP^J pairwise between u_X (2 qubits) and v_Y (2 qubits)."""
    for i in range(2):
        yield (cirq.ISWAP ** J).on(q_uX[i], q_vY[i])


def triangle_step(q_uA, q_vA, q_uB, q_vB, q_uC, q_vC, step_index, J_intra):
    """One step of the triangle compute cell:
       * internal chiral step on A, B, C
       * cross-chiral tunnels on the three edges: u_A<->v_B, u_B<->v_C, u_C<->v_A
    """
    yield from compute_merkabit_internal(q_uA, q_vA, step_index)
    yield from compute_merkabit_internal(q_uB, q_vB, step_index)
    yield from compute_merkabit_internal(q_uC, q_vC, step_index)
    if J_intra > 0:
        yield from cross_chiral_tunnel_2q(q_uA, q_vB, J_intra)
        yield from cross_chiral_tunnel_2q(q_uB, q_vC, J_intra)
        yield from cross_chiral_tunnel_2q(q_uC, q_vA, J_intra)


def envelope_step(q_u, q_v, step_index, cross_L1, cross_L2):
    U_u, U_v = octo_ouroboros_unitaries(step_index,
                                         cross_L1=cross_L1,
                                         cross_L2=cross_L2)
    yield cirq.MatrixGate(U_u, qid_shape=(2, 2, 2)).on(*q_u)
    yield cirq.MatrixGate(U_v, qid_shape=(2, 2, 2)).on(*q_v)


def inter_layer_write(q_uC, q_uenv, J_inter):
    """Horizon-crossing write: iSWAP^J_inter between compute-output u_C
    (2 qubits) and first two qubits of envelope's u register."""
    for i in range(2):
        yield (cirq.ISWAP ** J_inter).on(q_uC[i], q_uenv[i])


def three_qubit_swap_test(anc, q_a, q_b):
    yield cirq.H(anc)
    for qa, qb in zip(q_a, q_b):
        yield cirq.CSWAP(anc, qa, qb)
    yield cirq.H(anc)


def lift_4_to_8(vec4):
    vec8 = np.zeros(8, dtype=complex)
    vec8[:4] = vec4
    vec8 /= np.linalg.norm(vec8)
    return vec8


def build_circuit(label_A, label_B, label_C,
                   n_compute, n_envelope,
                   J_intra, J_inter, cross_L1, cross_L2,
                   apply_inter, readout,
                   env_u_seed=0, env_v_seed=1):
    qubits = cirq.LineQubit.range(22)
    q_uA = [qubits[i] for i in U_A]; q_vA = [qubits[i] for i in V_A]
    q_uB = [qubits[i] for i in U_B]; q_vB = [qubits[i] for i in V_B]
    q_uC = [qubits[i] for i in U_C]; q_vC = [qubits[i] for i in V_C]
    q_ue = [qubits[i] for i in U_ENV]; q_ve = [qubits[i] for i in V_ENV]
    q_ref = [qubits[i] for i in REF]
    anc = qubits[ANCILLA]

    qc = cirq.Circuit()

    # Prepare triangle compute cell
    lab_map = {'alpha': 0, 'beta': 1, 'gamma': 2}
    la = z3_eigenstate(lab_map[label_A])
    lb = z3_eigenstate(lab_map[label_B])
    lc = z3_eigenstate(lab_map[label_C])
    qc.append(state_prep_2q(la, "uA").on(*q_uA))
    qc.append(state_prep_2q(la, "vA").on(*q_vA))
    qc.append(state_prep_2q(lb, "uB").on(*q_uB))
    qc.append(state_prep_2q(lb, "vB").on(*q_vB))
    qc.append(state_prep_2q(lc, "uC").on(*q_uC))
    qc.append(state_prep_2q(lc, "vC").on(*q_vC))

    # Envelope initial random states
    rng_u = np.random.default_rng(env_u_seed)
    rng_v = np.random.default_rng(env_v_seed)
    ue_init = rng_u.normal(size=8) + 1j * rng_u.normal(size=8)
    ve_init = rng_v.normal(size=8) + 1j * rng_v.normal(size=8)
    ue_init /= np.linalg.norm(ue_init); ve_init /= np.linalg.norm(ve_init)
    qc.append(octo_state_prep_ops(q_ue, ue_init))
    qc.append(octo_state_prep_ops(q_ve, ve_init))

    # Triangle dynamics
    for s in range(n_compute * T_CYCLE):
        qc.append(triangle_step(q_uA, q_vA, q_uB, q_vB, q_uC, q_vC,
                                 s, J_intra))

    # Inter-layer write (or skip)
    if apply_inter:
        qc.append(inter_layer_write(q_uC, q_ue, J_inter))

    # Envelope dynamics
    for s in range(n_envelope * OCTO_T_CYCLE):
        qc.append(envelope_step(q_ue, q_ve, s, cross_L1, cross_L2))

    # Reference = label_C (the compute cell's last-stage output, which is what
    # the inter-layer tunnel writes)
    qc.append(octo_state_prep_ops(q_ref, lift_4_to_8(lc)))

    # SWAP test
    tgt = q_ue if readout == 'u_env' else q_ve
    qc.append(three_qubit_swap_test(anc, q_ref, tgt))
    qc.append(cirq.measure(anc, key='anc'))
    return qc


def run_trials(label_A, label_B, label_C, n_compute, n_envelope,
                J_intra, J_inter, cross_L1, cross_L2, shots, n_trials):
    sim = cirq.Simulator()
    per_trial = []
    for t in range(n_trials):
        row = {}
        for apply_inter in [True, False]:
            for readout in ['u_env', 'v_env']:
                qc = build_circuit(label_A, label_B, label_C,
                                     n_compute, n_envelope,
                                     J_intra, J_inter, cross_L1, cross_L2,
                                     apply_inter, readout,
                                     env_u_seed=10 * t,
                                     env_v_seed=10 * t + 1)
                r = sim.run(qc, repetitions=shots)
                zeros = int(r.histogram(key='anc').get(0, 0))
                key = f"{'store' if apply_inter else 'control'}_{readout}"
                row[key] = overlap_from_swap(zeros, shots)
        per_trial.append(row)
        print(f"  trial {t+1:2d}/{n_trials}  "
              f"u_env: store={row['store_u_env']:.3f} ctrl={row['control_u_env']:.3f} "
              f"d={row['store_u_env']-row['control_u_env']:+.3f}  |  "
              f"v_env: store={row['store_v_env']:.3f} ctrl={row['control_v_env']:.3f} "
              f"d={row['store_v_env']-row['control_v_env']:+.3f}")
    return per_trial


def agg(per_trial, key):
    arr = np.array([t[key] for t in per_trial])
    return float(arr.mean()), float(arr.std(ddof=1) / math.sqrt(len(arr)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--label-A',    default='alpha',
                     choices=['alpha', 'beta', 'gamma'])
    ap.add_argument('--label-B',    default='alpha',
                     choices=['alpha', 'beta', 'gamma'])
    ap.add_argument('--label-C',    default='alpha',
                     choices=['alpha', 'beta', 'gamma'])
    ap.add_argument('--n-compute',  type=int,   default=1)
    ap.add_argument('--n-envelope', type=int,   default=1)
    ap.add_argument('--J-intra',    type=float, default=0.1)
    ap.add_argument('--J-inter',    type=float, default=1.0)
    ap.add_argument('--cross-L1',   type=float, default=0.3)
    ap.add_argument('--cross-L2',   type=float, default=0.2)
    ap.add_argument('--shots',      type=int,   default=2048)
    ap.add_argument('--n-trials',   type=int,   default=10)
    args = ap.parse_args()

    print("Protocol 4S-Compute-Store -- 22-qubit three-layer stack prototype")
    print(f"  compute triangle:     A={args.label_A}  B={args.label_B}  C={args.label_C}")
    print(f"  compute periods:      n_c={args.n_compute} Coxeter periods")
    print(f"  envelope periods:     n_e={args.n_envelope} Coxeter periods")
    print(f"  J_intra (triangle):   {args.J_intra}")
    print(f"  J_inter (horizon):    {args.J_inter}")
    print(f"  cross L1 / L2:        {args.cross_L1} / {args.cross_L2}")
    print(f"  shots/circuit:        {args.shots}")
    print(f"  trials:               {args.n_trials}")
    print()
    print("Triangle topology: u_A<->v_B, u_B<->v_C, u_C<->v_A cross-chiral tunnels")
    print("Inter-layer write: u_C -iSWAP^{J_inter}-> u_env[0,1]")
    print("Reference prepared from label_C (triangle output stage).")
    print()

    per_trial = run_trials(args.label_A, args.label_B, args.label_C,
                            args.n_compute, args.n_envelope,
                            args.J_intra, args.J_inter,
                            args.cross_L1, args.cross_L2,
                            args.shots, args.n_trials)

    print()
    print("=" * 78)
    results_agg = {}
    for obs_name, readout in [('DIRECT (u_env)', 'u_env'),
                               ('BOUNDARY (v_env)', 'v_env')]:
        ms, ss = agg(per_trial, f'store_{readout}')
        mc, sc = agg(per_trial, f'control_{readout}')
        gap = ms - mc
        gap_sem = math.sqrt(ss ** 2 + sc ** 2)
        sigma = gap / gap_sem if gap_sem > 0 else float('inf')
        verdict = ("PASS" if sigma >= 3.0 else
                   "MARGINAL" if sigma >= 2.0 else "FAIL")
        results_agg[readout] = {
            'store_mean': ms, 'store_sem': ss,
            'control_mean': mc, 'control_sem': sc,
            'gap': gap, 'gap_sem': gap_sem, 'sigma': sigma,
            'verdict': verdict,
        }
        print(f"  {obs_name:18s}  store={ms:.4f}+/-{ss:.4f}  "
              f"control={mc:.4f}+/-{sc:.4f}  "
              f"gap={gap:+.4f}+/-{gap_sem:.4f}  ({sigma:+.1f} sigma) {verdict}")
    print("=" * 78)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp":  datetime.now().isoformat(timespec="seconds"),
        "protocol":   "P4S-Compute-Store (22-qubit, triangle compute cell)",
        "n_qubits":   22,
        "label_A":    args.label_A,
        "label_B":    args.label_B,
        "label_C":    args.label_C,
        "n_compute":  args.n_compute,
        "n_envelope": args.n_envelope,
        "J_intra":    args.J_intra,
        "J_inter":    args.J_inter,
        "cross_L1":   args.cross_L1,
        "cross_L2":   args.cross_L2,
        "shots":      args.shots,
        "n_trials":   args.n_trials,
        "per_trial":  per_trial,
        "aggregate":  results_agg,
    }
    out = RESULTS_DIR / f"p4s_compute_store_{datetime.now():%Y%m%dT%H%M%S}.json"
    out.write_text(json.dumps(payload, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
