#!/usr/bin/env python3
"""
Protocol 4S-Tesseract-Memory -- Full five-stage simulation of the
tesseract-only merkabit QC memory architecture (Paper 35 Option A).

Architecture (no octonion layer, no 8-spinor):

  COMPUTE CELL           3 tesseract merkabits in triangle (Paper 32)
    A(u_A, v_A), B(u_B, v_B), C(u_C, v_C)
    Cross-chiral tunnels on triangle edges (Paper 31):
      u_A <-> v_B,  u_B <-> v_C,  u_C <-> v_A  at J_intra
    Runs Protocol 4S internal chiral step (three isoclinic rotations + P
    gate) on each merkabit.

  MEMORY TUNNEL         cross-chiral tunnel u_C <-> v_D at J_mem
    "one spinor always in the tunnel": the content at u_C entangles with
    v_D; v_D holds the stored content after the write. Paper 31 tunnel
    primitive, no new gate engineering.

  DATABASE MERKABIT     tesseract D (u_D, v_D)
    v_D = the read handle (what gets measured from outside)
    u_D = forward partner, may be used in internal dynamics

  READ                  SWAP test between v_D and a reference register
    reference prepared in a target Z_3 label (alpha, beta, or gamma)
    overlap |<ref | v_D>| = recognition fidelity

Qubit layout (19 qubits total):
    q0, q1     u_A
    q2, q3     v_A
    q4, q5     u_B
    q6, q7     v_B
    q8, q9     u_C
    q10, q11   v_C
    q12, q13   u_D  (database forward)
    q14, q15   v_D  (database backward == memory readout)
    q16, q17   reference register (2 qubits in C^4)
    q18        SWAP-test ancilla

State vector: 2^19 x 16 bytes = 8 MB. Negligible.

The tesseract-only architecture has NO 1/3 attractor because there is no
octonion layer. All dynamics are 4-spinor Protocol 4S; all couplings are
Paper 31 cross-chiral tunnels. The 1/3 thermalisation ceiling that
washed out v_env readouts in the 26-qubit compute+store architecture
does NOT apply here.

Usage:
  python run_p4s_tesseract_memory_cirq.py --stage all
  python run_p4s_tesseract_memory_cirq.py --stage 2 --n-trials 20
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

RESULTS_DIR = SCRIPT_DIR.parent / "results"

# 19-qubit layout
U_A, V_A = [0, 1], [2, 3]
U_B, V_B = [4, 5], [6, 7]
U_C, V_C = [8, 9], [10, 11]
U_D, V_D = [12, 13], [14, 15]
REF      = [16, 17]
ANCILLA  = 18

LABELS = ['alpha', 'beta', 'gamma']
LABEL_IDX = {'alpha': 0, 'beta': 1, 'gamma': 2}


# ---------------------------------------------------------------------------
# PRIMITIVES (all Paper 31, field-tested)
# ---------------------------------------------------------------------------
def merkabit_internal_step(q_u, q_v, step_index):
    """One step of Protocol 4S internal chiral dynamics on a 4-spinor
    merkabit. Returns the four substeps in sequence."""
    th_c, th_h, th_d, phi_p = internal_step_angles_chiral(
        step_index % T_CYCLE)
    # Chiral P gate: forward on u, inverse on v
    Pf, Pi = p_gate_4(phi_p)
    yield cirq.MatrixGate(Pf, qid_shape=(2, 2)).on(*q_u)
    yield cirq.MatrixGate(Pi, qid_shape=(2, 2)).on(*q_v)
    # Three isoclinic rotations
    for gate_fn, theta in [(cross_gate_4, th_c),
                            (horizontal_gate_4, th_h),
                            (diagonal_gate_4, th_d)]:
        Uf, Ui = gate_fn(theta)
        yield cirq.MatrixGate(Uf, qid_shape=(2, 2)).on(*q_u)
        yield cirq.MatrixGate(Ui, qid_shape=(2, 2)).on(*q_v)


def cross_chiral_tunnel(q_uX, q_vY, J):
    """Paper 31 cross-chiral tunnel: pairwise iSWAP^J between u_X and v_Y."""
    if J == 0:
        return
    for i in range(2):
        yield (cirq.ISWAP ** J).on(q_uX[i], q_vY[i])


def compute_triangle_step(q_uA, q_vA, q_uB, q_vB, q_uC, q_vC,
                           step_index, J_intra):
    """One Coxeter step of the 3-merkabit compute triangle."""
    yield from merkabit_internal_step(q_uA, q_vA, step_index)
    yield from merkabit_internal_step(q_uB, q_vB, step_index)
    yield from merkabit_internal_step(q_uC, q_vC, step_index)
    # Triangle edges (Paper 32 topology)
    yield from cross_chiral_tunnel(q_uA, q_vB, J_intra)
    yield from cross_chiral_tunnel(q_uB, q_vC, J_intra)
    yield from cross_chiral_tunnel(q_uC, q_vA, J_intra)


def swap_test_2q(anc, q_a, q_b):
    """2-qubit SWAP test: H - CSWAP - CSWAP - H - measure."""
    yield cirq.H(anc)
    for qa, qb in zip(q_a, q_b):
        yield cirq.CSWAP(anc, qa, qb)
    yield cirq.H(anc)


# ---------------------------------------------------------------------------
# FULL WRITE-READ CIRCUIT
# ---------------------------------------------------------------------------
def build_write_read_circuit(label_A, label_B, label_C, ref_label,
                               n_compute, J_intra, J_mem,
                               apply_memory_tunnel=True,
                               readout='v_D'):
    """Build the full write+read circuit.

    readout: 'v_D' (memory read) or 'u_C' (compute direct check)
             or 'u_D' (database forward register)
    """
    qubits = cirq.LineQubit.range(19)
    q_uA = [qubits[i] for i in U_A]; q_vA = [qubits[i] for i in V_A]
    q_uB = [qubits[i] for i in U_B]; q_vB = [qubits[i] for i in V_B]
    q_uC = [qubits[i] for i in U_C]; q_vC = [qubits[i] for i in V_C]
    q_uD = [qubits[i] for i in U_D]; q_vD = [qubits[i] for i in V_D]
    q_ref = [qubits[i] for i in REF]
    anc = qubits[ANCILLA]

    qc = cirq.Circuit()

    # Prepare compute triangle with input labels
    la = z3_eigenstate(LABEL_IDX[label_A])
    lb = z3_eigenstate(LABEL_IDX[label_B])
    lc = z3_eigenstate(LABEL_IDX[label_C])
    qc.append(state_prep_2q(la, "uA").on(*q_uA))
    qc.append(state_prep_2q(la, "vA").on(*q_vA))
    qc.append(state_prep_2q(lb, "uB").on(*q_uB))
    qc.append(state_prep_2q(lb, "vB").on(*q_vB))
    qc.append(state_prep_2q(lc, "uC").on(*q_uC))
    qc.append(state_prep_2q(lc, "vC").on(*q_vC))

    # Database D starts at |0000> (blank memory) -- no state prep needed,
    # default |0> on initialisation.

    # Compute: n_compute Coxeter periods on the triangle
    for s in range(n_compute * T_CYCLE):
        qc.append(compute_triangle_step(q_uA, q_vA, q_uB, q_vB,
                                          q_uC, q_vC, s, J_intra))

    # Memory tunnel: u_C <-> v_D at J_mem (Paper 31 cross-chiral)
    if apply_memory_tunnel:
        qc.append(cross_chiral_tunnel(q_uC, q_vD, J_mem))

    # Prepare reference register in ref_label
    lref = z3_eigenstate(LABEL_IDX[ref_label])
    qc.append(state_prep_2q(lref, "ref").on(*q_ref))

    # Readout selection
    if readout == 'v_D':
        target = q_vD
    elif readout == 'u_D':
        target = q_uD
    elif readout == 'u_C':
        target = q_uC
    elif readout == 'v_C':
        target = q_vC
    else:
        raise ValueError(readout)

    qc.append(swap_test_2q(anc, q_ref, target))
    qc.append(cirq.measure(anc, key='anc'))
    return qc


def build_compute_sustain_circuit(label_A, label_B, label_C,
                                     n_compute, J_intra, merkabit='A'):
    """Stage 1 helper: build a circuit that runs the triangle and measures
    |<u_X|v_X>| for merkabit X in {A, B, C}. No database, no memory tunnel.
    """
    qubits = cirq.LineQubit.range(13)  # use only 13 qubits for stage 1
    q_uA = [qubits[0], qubits[1]]; q_vA = [qubits[2], qubits[3]]
    q_uB = [qubits[4], qubits[5]]; q_vB = [qubits[6], qubits[7]]
    q_uC = [qubits[8], qubits[9]]; q_vC = [qubits[10], qubits[11]]
    anc = qubits[12]

    qc = cirq.Circuit()
    la = z3_eigenstate(LABEL_IDX[label_A])
    lb = z3_eigenstate(LABEL_IDX[label_B])
    lc = z3_eigenstate(LABEL_IDX[label_C])
    qc.append(state_prep_2q(la, "uA").on(*q_uA))
    qc.append(state_prep_2q(la, "vA").on(*q_vA))
    qc.append(state_prep_2q(lb, "uB").on(*q_uB))
    qc.append(state_prep_2q(lb, "vB").on(*q_vB))
    qc.append(state_prep_2q(lc, "uC").on(*q_uC))
    qc.append(state_prep_2q(lc, "vC").on(*q_vC))

    for s in range(n_compute * T_CYCLE):
        qc.append(compute_triangle_step(q_uA, q_vA, q_uB, q_vB,
                                          q_uC, q_vC, s, J_intra))

    # Pick the target merkabit for SWAP test
    if merkabit == 'A':   q_u, q_v = q_uA, q_vA
    elif merkabit == 'B': q_u, q_v = q_uB, q_vB
    elif merkabit == 'C': q_u, q_v = q_uC, q_vC
    else: raise ValueError(merkabit)

    qc.append(swap_test_2q(anc, q_u, q_v))
    qc.append(cirq.measure(anc, key='anc'))
    return qc


# ---------------------------------------------------------------------------
# STAGES
# ---------------------------------------------------------------------------
def stage1_compute_baseline(n_compute, J_intra, shots, n_trials):
    """Stage 1: verify the compute triangle self-sustains at |<u|v>| ~ 0.47.
    Runs each label through the triangle, measures all three merkabits."""
    sim = cirq.Simulator()
    results = {L: {m: [] for m in 'ABC'} for L in LABELS}
    print(f"\n>>> STAGE 1: compute triangle self-sustain")
    print(f"    (expect |<u|v>|_mean ~ 0.47 from Paper 33)")
    for label in LABELS:
        for merkabit in 'ABC':
            for t in range(n_trials):
                qc = build_compute_sustain_circuit(
                    label, label, label, n_compute, J_intra, merkabit)
                r = sim.run(qc, repetitions=shots)
                zeros = int(r.histogram(key='anc').get(0, 0))
                results[label][merkabit].append(overlap_from_swap(zeros, shots))
    # Summary
    for label in LABELS:
        means = {m: float(np.mean(results[label][m])) for m in 'ABC'}
        sems = {m: float(np.std(results[label][m], ddof=1) / math.sqrt(n_trials))
                for m in 'ABC'}
        print(f"  [{label}] A={means['A']:.3f}+/-{sems['A']:.3f}  "
              f"B={means['B']:.3f}+/-{sems['B']:.3f}  "
              f"C={means['C']:.3f}+/-{sems['C']:.3f}")
    return results


def stage2_write_verification(n_compute, J_intra, J_mem, shots, n_trials):
    """Stage 2: 3x3 write-read cross-fidelity matrix on v_D (memory tunnel).
    Write label X to all three compute sites, read v_D against each
    reference label Y.
    Expected: diagonal dominance (X = Y matches best)."""
    sim = cirq.Simulator()
    F = {X: {Y: [] for Y in LABELS} for X in LABELS}
    print(f"\n>>> STAGE 2: 3x3 write-read on v_D (tesseract memory tunnel)")
    print(f"    J_mem = {J_mem}, expect diagonal dominance")
    for X in LABELS:
        for Y in LABELS:
            for t in range(n_trials):
                qc = build_write_read_circuit(
                    X, X, X, Y, n_compute, J_intra, J_mem,
                    apply_memory_tunnel=True, readout='v_D')
                r = sim.run(qc, repetitions=shots)
                zeros = int(r.histogram(key='anc').get(0, 0))
                F[X][Y].append(overlap_from_swap(zeros, shots))
    # Summary
    matrix = np.array([[np.mean(F[X][Y]) for Y in LABELS] for X in LABELS])
    matrix_sem = np.array([[np.std(F[X][Y], ddof=1) / math.sqrt(n_trials)
                             for Y in LABELS] for X in LABELS])
    print("    v_D cross-fidelity matrix (mean +/- SEM):")
    print(f"    {'write\\ref':>12s} " + " ".join(f"{Y:>18s}" for Y in LABELS))
    for i, X in enumerate(LABELS):
        row = " ".join(f"{matrix[i,j]:7.3f}+/-{matrix_sem[i,j]:.3f}"
                        for j in range(3))
        print(f"    write={X:>6s} | {row}")
    diag = np.array([matrix[i, i] for i in range(3)])
    off = np.array([matrix[i, j] for i in range(3) for j in range(3) if i != j])
    gap = float(diag.mean() - off.mean())
    gap_sem = float(math.sqrt(diag.std(ddof=1)**2 / 3 + off.std(ddof=1)**2 / 6))
    sigma = gap / gap_sem if gap_sem > 0 else float('inf')
    print(f"    diagonal mean = {diag.mean():.4f}")
    print(f"    off-diagonal mean = {off.mean():.4f}")
    print(f"    gap (diag - off) = {gap:+.4f} +/- {gap_sem:.4f}  ({sigma:+.1f} sigma)")
    return {'raw': F,
            'matrix': matrix.tolist(), 'matrix_sem': matrix_sem.tolist(),
            'diag_mean': float(diag.mean()),
            'off_mean': float(off.mean()),
            'gap': gap, 'gap_sem': gap_sem, 'sigma': sigma}


def stage3_null_control(n_compute, J_intra, J_mem, shots, n_trials):
    """Stage 3: null control. Same as stage 2 but WITHOUT the memory tunnel.
    Expected: diagonal gap ~ 0 (v_D stays at |0> without the tunnel, so
    overlap with any Z_3 reference is approximately random)."""
    sim = cirq.Simulator()
    F = {X: {Y: [] for Y in LABELS} for X in LABELS}
    print(f"\n>>> STAGE 3: null control (no memory tunnel applied)")
    print(f"    expect gap ~ 0 (v_D never receives content)")
    for X in LABELS:
        for Y in LABELS:
            for t in range(n_trials):
                qc = build_write_read_circuit(
                    X, X, X, Y, n_compute, J_intra, J_mem,
                    apply_memory_tunnel=False, readout='v_D')
                r = sim.run(qc, repetitions=shots)
                zeros = int(r.histogram(key='anc').get(0, 0))
                F[X][Y].append(overlap_from_swap(zeros, shots))
    matrix = np.array([[np.mean(F[X][Y]) for Y in LABELS] for X in LABELS])
    matrix_sem = np.array([[np.std(F[X][Y], ddof=1) / math.sqrt(n_trials)
                             for Y in LABELS] for X in LABELS])
    diag = np.array([matrix[i, i] for i in range(3)])
    off = np.array([matrix[i, j] for i in range(3) for j in range(3) if i != j])
    gap = float(diag.mean() - off.mean())
    gap_sem = float(math.sqrt(diag.std(ddof=1)**2 / 3 + off.std(ddof=1)**2 / 6))
    sigma = gap / gap_sem if gap_sem > 0 else float('inf')
    print(f"    (control) diagonal mean = {diag.mean():.4f}")
    print(f"    (control) off-diagonal mean = {off.mean():.4f}")
    print(f"    (control) gap = {gap:+.4f} +/- {gap_sem:.4f}  ({sigma:+.1f} sigma)")
    return {'raw': F,
            'matrix': matrix.tolist(), 'matrix_sem': matrix_sem.tolist(),
            'diag_mean': float(diag.mean()),
            'off_mean': float(off.mean()),
            'gap': gap, 'gap_sem': gap_sem, 'sigma': sigma}


def stage4_Jmem_sweep(n_compute, J_intra, shots, n_trials,
                        J_values=(0.0, 0.25, 0.5, 0.75, 1.0)):
    """Stage 4: sweep memory tunnel strength J_mem from 0 to 1.
    For each J_mem, measure the 3x3 write-read diagonal gap.
    Expected: monotone increase with J_mem, saturating near J_mem = 1."""
    sim = cirq.Simulator()
    sweep = []
    print(f"\n>>> STAGE 4: J_mem sweep over {J_values}")
    for J_mem in J_values:
        F = {X: {Y: [] for Y in LABELS} for X in LABELS}
        for X in LABELS:
            for Y in LABELS:
                for t in range(n_trials):
                    qc = build_write_read_circuit(
                        X, X, X, Y, n_compute, J_intra, J_mem,
                        apply_memory_tunnel=True, readout='v_D')
                    r = sim.run(qc, repetitions=shots)
                    zeros = int(r.histogram(key='anc').get(0, 0))
                    F[X][Y].append(overlap_from_swap(zeros, shots))
        matrix = np.array([[np.mean(F[X][Y]) for Y in LABELS] for X in LABELS])
        diag = np.array([matrix[i, i] for i in range(3)])
        off = np.array([matrix[i, j] for i in range(3) for j in range(3) if i != j])
        gap = float(diag.mean() - off.mean())
        sweep.append({'J_mem': J_mem,
                      'diag_mean': float(diag.mean()),
                      'off_mean': float(off.mean()),
                      'gap': gap})
        print(f"  J_mem={J_mem:.2f}  diag={diag.mean():.3f}  "
              f"off={off.mean():.3f}  gap={gap:+.3f}")
    return sweep


def stage5_direct_u_D(n_compute, J_intra, J_mem, shots, n_trials):
    """Stage 5: read u_D (database forward register) directly after the write.
    At J_mem = 1 full SWAP, u_D should hold v_D's prior state (|0>), so
    reading u_D against a label should give LOW overlap. This is a sanity
    check on the cross-chiral nature of the memory tunnel: only v_D picks
    up the content, u_D does NOT."""
    sim = cirq.Simulator()
    F = {X: {Y: [] for Y in LABELS} for X in LABELS}
    print(f"\n>>> STAGE 5: direct u_D readout (sanity: should be flat)")
    for X in LABELS:
        for Y in LABELS:
            for t in range(n_trials):
                qc = build_write_read_circuit(
                    X, X, X, Y, n_compute, J_intra, J_mem,
                    apply_memory_tunnel=True, readout='u_D')
                r = sim.run(qc, repetitions=shots)
                zeros = int(r.histogram(key='anc').get(0, 0))
                F[X][Y].append(overlap_from_swap(zeros, shots))
    matrix = np.array([[np.mean(F[X][Y]) for Y in LABELS] for X in LABELS])
    diag = np.array([matrix[i, i] for i in range(3)])
    off = np.array([matrix[i, j] for i in range(3) for j in range(3) if i != j])
    gap = float(diag.mean() - off.mean())
    gap_sem = float(math.sqrt(diag.std(ddof=1)**2 / 3 + off.std(ddof=1)**2 / 6))
    sigma = gap / gap_sem if gap_sem > 0 else float('inf')
    print(f"    (u_D direct) diagonal = {diag.mean():.4f}")
    print(f"    (u_D direct) off-diagonal = {off.mean():.4f}")
    print(f"    (u_D direct) gap = {gap:+.4f} +/- {gap_sem:.4f}  ({sigma:+.1f} sigma)")
    print(f"    (expect ~0 gap: cross-chiral tunnel sends content to v_D only)")
    return {'diag_mean': float(diag.mean()),
            'off_mean': float(off.mean()),
            'gap': gap, 'gap_sem': gap_sem, 'sigma': sigma}


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage',     default='all',
                     choices=['all', '1', '2', '3', '4', '5'])
    ap.add_argument('--n-compute', type=int,   default=1)
    ap.add_argument('--J-intra',   type=float, default=0.1)
    ap.add_argument('--J-mem',     type=float, default=1.0)
    ap.add_argument('--shots',     type=int,   default=2048)
    ap.add_argument('--n-trials',  type=int,   default=10)
    args = ap.parse_args()

    print("=" * 78)
    print("  Protocol 4S-Tesseract-Memory  (Paper 35 Option A)")
    print("  19-qubit tesseract-only architecture, no octonion layer")
    print("=" * 78)
    print(f"  compute: 3-merkabit triangle, Paper 32 topology")
    print(f"  memory:  cross-chiral tunnel u_C <-> v_D (Paper 31)")
    print(f"  read:    SWAP test v_D vs reference register")
    print(f"  n_compute = {args.n_compute} Coxeter periods, J_intra = {args.J_intra}")
    print(f"  J_mem = {args.J_mem}, shots = {args.shots}, trials/cell = {args.n_trials}")

    out = {
        'timestamp': datetime.now().isoformat(timespec='seconds'),
        'protocol':  'P4S-Tesseract-Memory (19-qubit Option A)',
        'n_qubits':  19,
        'args':      vars(args),
    }

    if args.stage in ('all', '1'):
        out['stage1'] = stage1_compute_baseline(
            args.n_compute, args.J_intra, args.shots, args.n_trials)
    if args.stage in ('all', '2'):
        out['stage2'] = stage2_write_verification(
            args.n_compute, args.J_intra, args.J_mem, args.shots, args.n_trials)
    if args.stage in ('all', '3'):
        out['stage3'] = stage3_null_control(
            args.n_compute, args.J_intra, args.J_mem, args.shots, args.n_trials)
    if args.stage in ('all', '4'):
        out['stage4'] = stage4_Jmem_sweep(
            args.n_compute, args.J_intra, args.shots, args.n_trials)
    if args.stage in ('all', '5'):
        out['stage5'] = stage5_direct_u_D(
            args.n_compute, args.J_intra, args.J_mem, args.shots, args.n_trials)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_file = RESULTS_DIR / f"p4s_tesseract_memory_{datetime.now():%Y%m%dT%H%M%S}.json"
    out_file.write_text(json.dumps(out, indent=2))
    print(f"\nWrote {out_file}")


if __name__ == "__main__":
    main()
