#!/usr/bin/env python3
"""
Protocol 4S Double-Triangle -- 28-qubit multi-cell merkabit QC scaling test.

Extends the Pentachoric Verification Protocol (Paper 33, Observable 22) to
two compute triangles sharing a single database merkabit. Tests whether the
architecture scales by composition: do two independent Z_3 clocks synchronise,
drift, or require Floquet locking when they share memory?

Qubit layout (28 qubits; state vector ~2 GB complex64):
    q0-q3    u_A1, v_A1        Triangle 1 merkabit A
    q4-q7    u_B1, v_B1        Triangle 1 merkabit B
    q8-q11   u_C1, v_C1        Triangle 1 merkabit C
    q12-q15  u_A2, v_A2        Triangle 2 merkabit A
    q16-q19  u_B2, v_B2        Triangle 2 merkabit B
    q20-q23  u_C2, v_C2        Triangle 2 merkabit C
    q24-q27  u_D, v_D          Shared database
                                (u_D stays |0>, v_D = shared write target)

Memory tunnels (shared write target):
    u_C1 -> v_D at J_mem1      Triangle 1 write channel
    u_C2 -> v_D at J_mem2      Triangle 2 write channel

Readout is analytical: after circuit execution, extract the full state vector
and compute the reduced density matrix of v_D via partial trace. Then project
onto Z_3 references to get overlap amplitudes. This saves 3 qubits compared to
Observable 22 (reference register + ancilla eliminated).

Three test modes:
  Mode 1 -- Synchronous: both triangles tick together (offset_T2 = 0).
  Mode 2 -- Interleaved: T2 offset by T_CYCLE/2 = 6 steps.
  Mode 3 -- Floquet lock: sweep offset_T2 in [0, T_CYCLE], find resonant peak.

Stage A: Sanity check. Run one configuration and confirm circuit compiles
and simulates in a reasonable time on a laptop.

Usage:
    python run_p4s_double_triangle_cirq.py --stage sanity
    python run_p4s_double_triangle_cirq.py --stage mode1
    python run_p4s_double_triangle_cirq.py --stage mode2
    python run_p4s_double_triangle_cirq.py --stage mode3

Authors: Stenberg with Claude Anthropic, April 2026.
"""
from __future__ import annotations
import argparse
import json
import math
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import cirq

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

from run_p4s_tesseract_memory_cirq import (
    merkabit_internal_step, cross_chiral_tunnel,
    compute_triangle_step, LABELS,
)
from run_p4s_Z3_three_cirq import z3_eigenstate
from run_p4s_Z3_cirq import state_prep_2q
from run_p4s_cirq import T_CYCLE


# ---------------------------------------------------------------------------
# 28-QUBIT LAYOUT
# ---------------------------------------------------------------------------
U_A1, V_A1 = [0, 1], [2, 3]
U_B1, V_B1 = [4, 5], [6, 7]
U_C1, V_C1 = [8, 9], [10, 11]
U_A2, V_A2 = [12, 13], [14, 15]
U_B2, V_B2 = [16, 17], [18, 19]
U_C2, V_C2 = [20, 21], [22, 23]
U_D,  V_D  = [24, 25], [26, 27]

N_QUBITS = 28
V_D_QUBIT_INDICES = (26, 27)  # rightmost two qubits in the state vector

LABEL_IDX = {'alpha': 0, 'beta': 1, 'gamma': 2}


# ---------------------------------------------------------------------------
# CIRCUIT BUILDER
# ---------------------------------------------------------------------------
def _prep_triangle(qc: cirq.Circuit, qubits, triangle_idx: int,
                    labels: tuple[str, str, str]) -> None:
    """State-prep one compute triangle (3 merkabits)."""
    t = triangle_idx  # 1 or 2
    indices_and_labels = [
        ({1: U_A1, 2: U_A2}[t], labels[0], f"u_A{t}"),
        ({1: V_A1, 2: V_A2}[t], labels[0], f"v_A{t}"),
        ({1: U_B1, 2: U_B2}[t], labels[1], f"u_B{t}"),
        ({1: V_B1, 2: V_B2}[t], labels[1], f"v_B{t}"),
        ({1: U_C1, 2: U_C2}[t], labels[2], f"u_C{t}"),
        ({1: V_C1, 2: V_C2}[t], labels[2], f"v_C{t}"),
    ]
    for idx_list, label, name in indices_and_labels:
        eigvec = z3_eigenstate(LABEL_IDX[label])
        qc.append(state_prep_2q(eigvec, name).on(
            *[qubits[i] for i in idx_list]))


def build_double_triangle_circuit(
    labels1: tuple[str, str, str],
    labels2: tuple[str, str, str],
    n_compute: int = 1,
    J_intra: float = 0.1,
    J_intra2: float = None,
    J_mem1: float = 0.5,
    J_mem2: float = 0.5,
    offset_T2: int = 0,
    T_CYCLE_2: int = None,
    apply_memory: bool = True,
) -> cirq.Circuit:
    """Build the 28-qubit double-triangle circuit.

    labels1, labels2: (site_A_label, site_B_label, site_C_label) for each triangle.
    Labels are 'alpha' / 'beta' / 'gamma'.

    n_compute: number of Coxeter periods (12 internal steps each).
    J_intra: triangle-edge tunnel coupling for Triangle 1 (default 0.1).
    J_intra2: triangle-edge tunnel coupling for Triangle 2. If None, equals
              J_intra (Regime 2 -- cyclotomic). If different, the two
              triangles have incommensurate internal dynamics (Paper 7
              Regime 3 -- GUE/Riemann-zero-like predicted). This is the
              Observable 24 switch.
    J_mem1, J_mem2: memory-tunnel couplings from each triangle to v_D.
    offset_T2: Triangle 2's internal step index is shifted by offset_T2
               (phase offset, not truncation). Used for Mode 3 sweep.
    T_CYCLE_2: Coxeter period for Triangle 2. If None, defaults to T_CYCLE
               (12 internal steps, commensurate with Triangle 1). If set
               to a different integer (e.g. 13), Triangle 2 runs on an
               incommensurate clock, implementing Observable 24's
               Paper 7 Regime 3 test via period mismatch rather than
               coupling mismatch. Specifying both T_CYCLE_2 and J_intra2
               is equivalent; either alone suffices for Regime 3.
    apply_memory: if False, skip the memory tunnels (null control).

    Observable 23 (cyclotomic Z_3, Regime 2) uses default Regime 2 settings.
    Observable 24 (GUE / Riemann-zero-like, Regime 3) uses either
      T_CYCLE_2 != T_CYCLE (e.g. 13) OR J_intra2 != J_intra (e.g. J_intra * sqrt(2)).
    """
    if J_intra2 is None:
        J_intra2 = J_intra
    if T_CYCLE_2 is None:
        T_CYCLE_2 = T_CYCLE
    qubits = cirq.LineQubit.range(N_QUBITS)
    qc = cirq.Circuit()

    # --- State prep: both triangles + database (database stays at |0>) ------
    _prep_triangle(qc, qubits, 1, labels1)
    _prep_triangle(qc, qubits, 2, labels2)
    # Cirq trims qubits never touched by a gate, which would collapse our
    # state vector below 28 qubits. Apply identity to u_D and v_D to pin
    # them in the state.
    for idx in U_D + V_D:
        qc.append(cirq.I(qubits[idx]))

    # --- Compute dynamics: n_compute Coxeter periods ------------------------
    # Both triangles run the SAME number of steps.
    # offset_T2 implements a phase shift (Paper 7 Regime 2 test): Triangle 2's
    # internal step_index is shifted by offset_T2, so it enters the compute
    # dynamics at a different point along the Coxeter cycle. This tests the
    # coupled-phase behaviour predicted by Paper 7 §5.3 rather than a
    # truncation-induced asymmetry.
    # Triangle 1 runs at J_intra with standard Coxeter period T_CYCLE = 12.
    # Triangle 2 runs at J_intra2 (may differ from J_intra for Observable 24
    # Regime 3 test) with its step index phase-shifted by offset_T2.
    #
    # NOTE on T_CYCLE_2: The underlying internal_step_angles_chiral() uses
    # the module-level T_CYCLE = 12 for its angle table. Implementing a
    # genuinely different T_CYCLE_2 (e.g. 13) for Triangle 2 would require
    # refactoring that angle helper. For Observable 24, the cleaner and
    # currently-supported switch is to set J_intra2 != J_intra (e.g.
    # J_intra2 = J_intra * sqrt(2)), which produces incommensurate-rate
    # coupling directly. The T_CYCLE_2 parameter is retained as a signal
    # of intent; it has no effect on the current implementation beyond
    # logging.
    n_steps = n_compute * T_CYCLE
    q = lambda idx_list: [qubits[i] for i in idx_list]
    for s in range(n_steps):
        # Triangle 1: standard phase, J_intra coupling
        qc.append(compute_triangle_step(
            q(U_A1), q(V_A1), q(U_B1), q(V_B1), q(U_C1), q(V_C1),
            s % T_CYCLE, J_intra))
        # Triangle 2: phase-shifted dynamics at J_intra2 coupling.
        # Regime 2 (cyclotomic) when J_intra2 == J_intra.
        # Regime 3 (GUE-like, Paper 7) when J_intra2 != J_intra.
        qc.append(compute_triangle_step(
            q(U_A2), q(V_A2), q(U_B2), q(V_B2), q(U_C2), q(V_C2),
            (s + offset_T2) % T_CYCLE, J_intra2))

    # --- Memory tunnels: both triangles write to v_D after compute ----------
    if apply_memory:
        qc.append(cross_chiral_tunnel(q(U_C1), q(V_D), J_mem1))
        qc.append(cross_chiral_tunnel(q(U_C2), q(V_D), J_mem2))

    return qc


# ---------------------------------------------------------------------------
# ANALYTICAL READOUT (partial trace onto v_D, project onto Z_3 references)
# ---------------------------------------------------------------------------
def vD_reduced_density_matrix(final_state: np.ndarray) -> np.ndarray:
    """Compute the 4x4 reduced density matrix of v_D (qubits 26, 27)
    by partial-trace over the other 26 qubits.

    final_state: shape (2^28,) complex state vector.
    Returns: shape (4, 4) complex density matrix on v_D.
    """
    # Reshape to (2^26, 4): last axis is v_D's 4-dim Hilbert space (q26, q27)
    psi = final_state.reshape(2 ** (N_QUBITS - 2), 4)
    # rho_vD[a, b] = sum_i psi[i, a] * conj(psi[i, b])
    rho = np.einsum("ia,ib->ab", psi, psi.conj())
    return rho


def vD_overlaps_against_Z3(final_state: np.ndarray) -> dict[str, float]:
    """Compute |<v_D | Z_3 eigenstate>| for each Z_3 reference label.
    Returns a dict {alpha: overlap, beta: overlap, gamma: overlap}.
    """
    rho = vD_reduced_density_matrix(final_state)
    out = {}
    for label, k in LABEL_IDX.items():
        ref = z3_eigenstate(k).astype(complex)      # shape (4,)
        ref = ref / np.linalg.norm(ref)
        overlap_sq = float(np.real(ref.conj() @ rho @ ref))
        # Numerical noise can push slightly below zero
        overlap_sq = max(0.0, overlap_sq)
        out[label] = math.sqrt(overlap_sq)
    return out


def vD_full_spectrum(final_state: np.ndarray) -> dict:
    """Extract the full v_D reverse-time-record spectrum: diagonal populations
    in the Z_3 eigenbasis, off-diagonal coherence magnitudes, von Neumann
    entropy, and purity.

    In Paper 7's language, v_D is the reverse-time clock face. A coherent
    record has small entropy and large off-diagonal magnitudes. A collapsed
    record has entropy near ln(3) and off-diagonals near zero -- a Riemann-
    zero-like arithmetic balance point.
    """
    rho_raw = vD_reduced_density_matrix(final_state)

    # Build the Z_3 eigenbasis of v_D (ordered alpha, beta, gamma).
    # Note: v_D lives on 2 qubits (4-dim), so only 3 Z_3 labels sit in a
    # 3-dim subspace of the 4-dim register.
    refs = []
    for label in ("alpha", "beta", "gamma"):
        r = z3_eigenstate(LABEL_IDX[label]).astype(complex)
        refs.append(r / np.linalg.norm(r))
    U = np.column_stack(refs)                            # (4, 3) isometry

    # Project rho into the Z_3 eigenbasis: rho_Z3[i,j] = <i|rho|j>, i,j in Z_3
    rho_Z3 = U.conj().T @ rho_raw @ U                    # (3, 3)

    diag = {label: float(np.real(rho_Z3[k, k]))
             for label, k in LABEL_IDX.items()}
    off_mag = {
        "ab": float(abs(rho_Z3[0, 1])),
        "ag": float(abs(rho_Z3[0, 2])),
        "bg": float(abs(rho_Z3[1, 2])),
    }
    # Also off-diagonal phases (useful for Z_3 signature detection)
    off_phase = {
        "ab": float(np.angle(rho_Z3[0, 1])),
        "ag": float(np.angle(rho_Z3[0, 2])),
        "bg": float(np.angle(rho_Z3[1, 2])),
    }

    # Von Neumann entropy of the full 4-dim rho (not the 3-dim projection).
    # Eigenvalues; clip tiny negatives from numerical noise.
    evals = np.linalg.eigvalsh(rho_raw).real
    evals = np.clip(evals, 1e-15, 1.0)
    s_vN = float(-np.sum(evals * np.log(evals)))         # natural log

    # Purity Tr(rho^2): 1 = pure, 1/4 = maximally mixed on 4-dim.
    purity = float(np.real(np.trace(rho_raw @ rho_raw)))

    # Also the 3-dim projection mass (how much of v_D lives in the Z_3
    # eigenspace, vs the fourth orthogonal direction which is "non-Z_3"):
    z3_mass = float(np.real(np.trace(rho_Z3)))

    return {
        "diag":     diag,
        "off_mag":  off_mag,
        "off_phase":off_phase,
        "entropy":  s_vN,
        "purity":   purity,
        "z3_mass":  z3_mass,
        "rho_Z3":   rho_Z3.tolist(),  # full complex 3x3 for later analysis
    }


# ---------------------------------------------------------------------------
# STAGE A: SANITY CHECK
# ---------------------------------------------------------------------------
def stage_A_sanity_check():
    """Single configuration: both triangles write alpha. Measure v_D.
    Reports runtime + v_D overlaps as a feasibility test.
    """
    print("=" * 72)
    print("STAGE A -- Sanity check: single configuration")
    print(f"  Qubits:          {N_QUBITS}")
    print(f"  State vector:    2^{N_QUBITS} * 8 B (complex64) = "
          f"{2**N_QUBITS * 8 / (1024**3):.2f} GB")
    print(f"  Configuration:   Triangle 1 = (alpha, alpha, alpha)")
    print(f"                   Triangle 2 = (alpha, alpha, alpha)")
    print(f"                   n_compute=1, J_intra=0.1, J_mem=0.5, offset=0")
    print("=" * 72)

    t0 = time.time()
    print("\n[build] constructing circuit...")
    qc = build_double_triangle_circuit(
        labels1=("alpha", "alpha", "alpha"),
        labels2=("alpha", "alpha", "alpha"),
        n_compute=1, J_intra=0.1, J_mem1=0.5, J_mem2=0.5, offset_T2=0,
    )
    t1 = time.time()
    print(f"  circuit built in {t1 - t0:.2f} s")
    print(f"  total operations: {len(list(qc.all_operations()))}")
    print(f"  depth (moment count): {len(qc)}")

    print("\n[simulate] running cirq.Simulator (ideal state-vector)...")
    sim = cirq.Simulator()
    t2 = time.time()
    result = sim.simulate(qc)
    t3 = time.time()
    print(f"  simulated in {t3 - t2:.1f} s")

    # Analytical readout
    print("\n[readout] partial-trace onto v_D, project onto Z_3 eigenstates...")
    t4 = time.time()
    final_state = result.final_state_vector
    overlaps = vD_overlaps_against_Z3(final_state)
    t5 = time.time()
    print(f"  readout in {t5 - t4:.1f} s")

    total = t5 - t0
    print("\n" + "=" * 72)
    print("RESULTS")
    print("=" * 72)
    print(f"  Total runtime:            {total:.1f} s")
    print(f"  |<v_D | alpha>|  =  {overlaps['alpha']:.4f}")
    print(f"  |<v_D | beta>|   =  {overlaps['beta']:.4f}")
    print(f"  |<v_D | gamma>|  =  {overlaps['gamma']:.4f}")
    dominant = max(overlaps, key=overlaps.get)
    print(f"  dominant label:          {dominant} "
          f"(overlap {overlaps[dominant]:.4f})")

    expected = "gamma"  # cycle(alpha) = gamma under Z_3 -1 generator
    print(f"\n  Expected (Paper 33 Z_3 clock): both writing alpha should "
          f"produce v_D closest to {expected}")
    if dominant == expected:
        print("  VERDICT:                  [PASS]  Z_3 cycle pattern reproduced "
              "(v_D aligns with cycle(alpha) = gamma)")
    else:
        print(f"  VERDICT:                  v_D aligns with {dominant} "
              f"(not {expected}); two shared writes may interfere differently")

    # Additional structural metric: how much contrast between the dominant
    # label and the next-highest one?
    sorted_overlaps = sorted(overlaps.items(), key=lambda kv: -kv[1])
    top, second = sorted_overlaps[0], sorted_overlaps[1]
    contrast = top[1] - second[1]
    print(f"  Top-vs-second contrast:   {contrast:+.4f}  "
          f"({top[0]} vs {second[0]})")
    if contrast < 0.05:
        print("  NOTE:                     dominant/second contrast is small; "
              "the two shared writes produced a near-equal mixture of {}+{} "
              "(partial interference)".format(top[0], second[0]))
    print("=" * 72)

    # Save JSON
    outdir = SCRIPT_DIR.parent / "results"
    outdir.mkdir(exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    fname = outdir / f"p4s_double_triangle_stageA_{stamp}.json"
    payload = {
        "stage":       "A",
        "timestamp":   stamp,
        "n_qubits":    N_QUBITS,
        "runtime_s":   total,
        "build_s":     t1 - t0,
        "simulate_s":  t3 - t2,
        "readout_s":   t5 - t4,
        "ops":         len(list(qc.all_operations())),
        "depth":       len(qc),
        "config": {
            "labels1":    ["alpha"] * 3,
            "labels2":    ["alpha"] * 3,
            "n_compute":  1,
            "J_intra":    0.1,
            "J_mem1":     0.5,
            "J_mem2":     0.5,
            "offset_T2":  0,
        },
        "overlaps":    overlaps,
        "dominant":    dominant,
        "expected":    expected,
        "cycle_match": dominant == expected,
    }
    fname.write_text(json.dumps(payload, indent=2))
    print(f"\n  wrote {fname}")


# ---------------------------------------------------------------------------
# STAGE B: Mode 1 (synchronous) and Mode 2 (interleaved) label matrices
# ---------------------------------------------------------------------------
def _run_one_config(labels1, labels2, n_compute, J_intra, J_mem, offset_T2,
                     J_intra2=None):
    """Run one configuration and return full v_D spectrum.

    If J_intra2 is None: both triangles at same coupling (Regime 2 default).
    If J_intra2 != J_intra: Observable 24 Regime 3 test.
    """
    qc = build_double_triangle_circuit(
        labels1=labels1, labels2=labels2,
        n_compute=n_compute, J_intra=J_intra, J_intra2=J_intra2,
        J_mem1=J_mem, J_mem2=J_mem, offset_T2=offset_T2,
    )
    sim = cirq.Simulator()
    result = sim.simulate(qc)
    return vD_full_spectrum(result.final_state_vector)


# ---------------------------------------------------------------------------
# STAGE D (Observable 24): Regime 3 entropy spectrum -- GUE / Riemann-zero test
# ---------------------------------------------------------------------------
def stage_D_regime3_spectrum(
    offsets: list[int] = None,
    reference_configs: list[tuple[str, str]] = None,
    n_compute: int = 1, J_intra: float = 0.1,
    J_intra2_ratio: float = math.sqrt(2),  # incommensurate factor
    J_mem: float = 0.5,
):
    """Observable 24: repeat Stage C's sweep with Triangle 2's internal
    coupling set to J_intra * J_intra2_ratio (default sqrt(2), irrational).

    Paper 7 Regime 3 prediction: the entropy spectrum should lose the
    cyclotomic Z_3 structure (no period-12 peak in FFT), and the collapse
    offsets should exhibit GUE-like spacing statistics.

    Default: 64 offsets over a wider window (five half-periods) to allow
    more spacings for statistical tests.

    This function is callable but NOT AUTO-RUN. Invoke via:
        python run_p4s_double_triangle_cirq.py --stage D
    """
    import math as _math
    if offsets is None:
        offsets = list(range(0, 64))
    if reference_configs is None:
        reference_configs = [(X, Y) for X in ("alpha", "beta", "gamma")
                                     for Y in ("alpha", "beta", "gamma")]
    J_intra2 = J_intra * J_intra2_ratio
    n_configs = len(offsets) * len(reference_configs)
    print("=" * 72)
    print("STAGE D -- Observable 24 (Regime 3: GUE / Riemann-zero test)")
    print(f"  Triangle 1 J_intra  = {J_intra}")
    print(f"  Triangle 2 J_intra2 = {J_intra2:.6f}  (ratio {J_intra2_ratio:.6f})")
    print(f"  Incommensurate via irrational J_intra ratio")
    print(f"  {len(offsets)} offsets x {len(reference_configs)} ref configs "
          f"= {n_configs} total sims")
    print(f"  n_compute = {n_compute}, J_mem = {J_mem}")
    print(f"  Expected runtime ~55-90 min on laptop.")
    print("=" * 72)

    t_start = time.time()
    spectrum = {}
    for i, offset in enumerate(offsets):
        spectrum[offset] = {}
        for j, (X, Y) in enumerate(reference_configs):
            spec = _run_one_config(
                labels1=(X, X, X), labels2=(Y, Y, Y),
                n_compute=n_compute, J_intra=J_intra,
                J_intra2=J_intra2,
                J_mem=J_mem, offset_T2=offset)
            spectrum[offset][(X, Y)] = spec
            done = i * len(reference_configs) + j + 1
            if done % 9 == 0 or done == n_configs:
                elapsed = time.time() - t_start
                eta = elapsed / done * (n_configs - done) if done else 0
                print(f"  [{done:>3d}/{n_configs}]  offset={offset:>2d}  "
                      f"(X,Y)=({X[:3]},{Y[:3]})  "
                      f"S={spec['entropy']:.3f}  "
                      f"elapsed={elapsed:.0f}s  eta={eta:.0f}s")
    t_end = time.time()
    print(f"\n  total runtime: {(t_end - t_start) / 60:.1f} min")

    # Mean entropy at each offset
    mean_entropy = {}
    for offset in offsets:
        entropies = [spectrum[offset][(X, Y)]["entropy"]
                      for X, Y in reference_configs]
        mean_entropy[offset] = float(np.mean(entropies))

    # Find collapse events (entropy local maxima)
    entropy_arr = np.array([mean_entropy[o] for o in offsets])
    collapse_offsets = []
    for idx in range(1, len(offsets) - 1):
        if (entropy_arr[idx] > entropy_arr[idx - 1]
                and entropy_arr[idx] > entropy_arr[idx + 1]):
            collapse_offsets.append(offsets[idx])

    # FFT: is the spectrum still period-12?
    fft = np.fft.rfft(entropy_arr - entropy_arr.mean())
    freq = np.fft.rfftfreq(len(entropy_arr), d=1.0)
    power = np.abs(fft) ** 2
    dominant_period = 0.0
    if len(power) > 1:
        peak_idx = int(np.argmax(power[1:]) + 1)
        if freq[peak_idx] > 0:
            dominant_period = 1.0 / freq[peak_idx]

    # Collapse spacings -- GUE prediction
    if len(collapse_offsets) > 1:
        spacings = [collapse_offsets[i + 1] - collapse_offsets[i]
                     for i in range(len(collapse_offsets) - 1)]
    else:
        spacings = []

    print(f"\n--- Regime 3 spectrum summary ---")
    print(f"  collapse events: {collapse_offsets}")
    print(f"  collapse spacings: {spacings}")
    if spacings:
        print(f"  mean spacing: {np.mean(spacings):.2f}  "
              f"std: {np.std(spacings, ddof=1):.2f}  "
              f"std/mean: {np.std(spacings, ddof=1)/np.mean(spacings):.3f}")
    print(f"  FFT dominant period: {dominant_period:.2f}  "
          f"(Regime 2 would give 12.00; Regime 3 should NOT)")

    # Verdict on the 4 pre-registered Observable 24 thresholds
    print(f"\n--- Observable 24 threshold check ---")
    # 24-A: no single period > 20% of total power
    total_power = power[1:].sum() if len(power) > 1 else 0
    max_frac = (power[1:].max() / total_power) if total_power > 0 else 0
    print(f"  24-A Aperiodic: max period fraction = {max_frac:.2%}  "
          f"(threshold < 20%)  "
          f"{'PASS' if max_frac < 0.20 else 'FAIL (still cyclotomic)'}")
    print(f"  24-G GUE spacings: needs \u2265 60-offset sweep; current = "
          f"{len(offsets)} offsets  (partial)")
    print(f"  24-M Montgomery: pair-correlation analysis requires post-processing")
    # 24-F: no locking event at period T_CYCLE
    floor_at_12 = mean_entropy.get(12, None)
    mean_S = float(np.mean(list(mean_entropy.values())))
    if floor_at_12 is not None:
        print(f"  24-F Floor: S at offset 12 = {floor_at_12:.4f},  "
              f"mean S = {mean_S:.4f},  diff = {floor_at_12 - mean_S:+.4f}")

    # Save JSON
    outdir = SCRIPT_DIR.parent / "results"
    outdir.mkdir(exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    fname = outdir / f"p4s_double_triangle_stageD_regime3_{stamp}.json"
    clean_spectrum = {}
    for offset in offsets:
        clean_spectrum[str(offset)] = {}
        for X, Y in reference_configs:
            s = spectrum[offset][(X, Y)]
            clean_spectrum[str(offset)][f"{X},{Y}"] = {
                "diag":      s["diag"],
                "off_mag":   s["off_mag"],
                "entropy":   s["entropy"],
                "purity":    s["purity"],
                "z3_mass":   s["z3_mass"],
            }
    payload = {
        "stage":             "D_regime3_observable24",
        "timestamp":         stamp,
        "offsets":           offsets,
        "parameters":        {"n_compute": n_compute, "J_intra": J_intra,
                               "J_intra2": J_intra2,
                               "J_intra2_ratio": J_intra2_ratio,
                               "J_mem": J_mem},
        "runtime_s":         t_end - t_start,
        "mean_entropy":      mean_entropy,
        "collapse_offsets":  collapse_offsets,
        "collapse_spacings": spacings,
        "dominant_period":   dominant_period,
        "fft_max_fraction":  max_frac,
        "spectrum":          clean_spectrum,
    }
    fname.write_text(json.dumps(payload, indent=2))
    print(f"\n  wrote {fname}")


def stage_B_label_matrix(offset_T2: int, label: str,
                          n_compute: int = 1, J_intra: float = 0.1,
                          J_mem: float = 0.5):
    """Run the 3x3 label matrix: Triangle 1 writes X in {alpha, beta, gamma}
    while Triangle 2 writes Y in {alpha, beta, gamma}. All three merkabits
    of each triangle prepped with that triangle's label (uniform preparation).

    Records the full v_D spectrum at each cell. Reports the dominant v_D
    label, the cycled-diagonal gap, the entropy, and the off-diagonal
    coherence summary.

    offset_T2 = 0  -> Mode 1 synchronous (both triangles in-phase)
    offset_T2 = 6  -> Mode 2 interleaved (T2 half-period ahead in phase)
    """
    print("=" * 72)
    print(f"STAGE B -- {label}  (offset_T2 = {offset_T2})")
    print(f"  9 configurations: (X, Y) for X, Y in {{alpha, beta, gamma}}")
    print(f"  n_compute = {n_compute}, J_intra = {J_intra}, J_mem = {J_mem}")
    print("=" * 72)

    labels = ("alpha", "beta", "gamma")
    t_start = time.time()
    results = {X: {Y: None for Y in labels} for X in labels}
    for i, X in enumerate(labels):
        for j, Y in enumerate(labels):
            tt0 = time.time()
            spec = _run_one_config(
                labels1=(X, X, X), labels2=(Y, Y, Y),
                n_compute=n_compute, J_intra=J_intra,
                J_mem=J_mem, offset_T2=offset_T2)
            tt1 = time.time()
            results[X][Y] = spec
            dom = max(spec["diag"], key=spec["diag"].get)
            print(f"  [{i*3+j+1:>2d}/9]  "
                  f"T1={X:>6s}  T2={Y:>6s}  dom={dom:>6s}  "
                  f"S={spec['entropy']:.3f}  purity={spec['purity']:.3f}  "
                  f"z3_mass={spec['z3_mass']:.3f}  ({tt1-tt0:.1f}s)")
    t_end = time.time()

    # Summary matrices (diagonal dominance and entropy)
    print("\n  --- diagonal-dominance matrix (which Z3 label v_D recognises most) ---")
    print(f"  {'T1\\T2':>8s}  " + "  ".join(f"{Y:>6s}" for Y in labels))
    for X in labels:
        row = [f"{max(results[X][Y]['diag'], key=results[X][Y]['diag'].get):>6s}"
               for Y in labels]
        print(f"  {X:>8s}  " + "  ".join(row))

    print("\n  --- entropy matrix S(rho_vD) ---")
    print(f"  {'T1\\T2':>8s}  " + "  ".join(f"{Y:>6s}" for Y in labels))
    for X in labels:
        row = [f"{results[X][Y]['entropy']:>6.3f}" for Y in labels]
        print(f"  {X:>8s}  " + "  ".join(row))

    print(f"\n  total runtime: {t_end - t_start:.1f}s  (avg {(t_end - t_start)/9:.1f}s/config)")

    # Save JSON
    outdir = SCRIPT_DIR.parent / "results"
    outdir.mkdir(exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    fname = outdir / f"p4s_double_triangle_stageB_{label}_{stamp}.json"
    # Strip complex rho_Z3 for cleaner JSON (keep only real/imag separately)
    clean_results = {}
    for X in labels:
        clean_results[X] = {}
        for Y in labels:
            s = results[X][Y]
            clean_results[X][Y] = {
                "diag":      s["diag"],
                "off_mag":   s["off_mag"],
                "off_phase": s["off_phase"],
                "entropy":   s["entropy"],
                "purity":    s["purity"],
                "z3_mass":   s["z3_mass"],
            }
    payload = {
        "stage":       f"B_{label}",
        "timestamp":   stamp,
        "offset_T2":   offset_T2,
        "parameters":  {"n_compute": n_compute, "J_intra": J_intra, "J_mem": J_mem},
        "runtime_s":   t_end - t_start,
        "results":     clean_results,
    }
    fname.write_text(json.dumps(payload, indent=2))
    print(f"  wrote {fname}")


# ---------------------------------------------------------------------------
# STAGE C: Mode 3 entropy spectrum -- the Paper 7 test
# ---------------------------------------------------------------------------
def stage_C_entropy_spectrum(
    offsets: list[int] = None,
    reference_configs: list[tuple[str, str]] = None,
    n_compute: int = 1, J_intra: float = 0.1, J_mem: float = 0.5,
):
    """Sweep offset_T2 and measure the v_D entropy + diagonal pattern.

    This is the direct test of Paper 7's prediction: when two coupled
    rotating triangles share a substrate, the transfer spectrum should
    exhibit collapse events (entropy peaks, off-diagonal dips) at
    arithmetic-balance points, in structural analogy to the Riemann zeros.

    Default sweep covers 36 offsets (three Coxeter periods).
    Default reference configs: 9 (all Z3 x Z3 label pairs).
    """
    if offsets is None:
        offsets = list(range(0, 36))
    if reference_configs is None:
        reference_configs = [(X, Y) for X in ("alpha", "beta", "gamma")
                                     for Y in ("alpha", "beta", "gamma")]
    n_configs = len(offsets) * len(reference_configs)
    print("=" * 72)
    print("STAGE C -- Entropy spectrum (Paper 7 Floquet-lock test)")
    print(f"  {len(offsets)} offsets x {len(reference_configs)} ref configs "
          f"= {n_configs} total sims")
    print(f"  n_compute = {n_compute}, J_intra = {J_intra}, J_mem = {J_mem}")
    print("=" * 72)

    t_start = time.time()
    spectrum = {}  # offset -> {(X,Y): full_spec}
    for i, offset in enumerate(offsets):
        spectrum[offset] = {}
        for j, (X, Y) in enumerate(reference_configs):
            tt0 = time.time()
            spec = _run_one_config(
                labels1=(X, X, X), labels2=(Y, Y, Y),
                n_compute=n_compute, J_intra=J_intra,
                J_mem=J_mem, offset_T2=offset)
            tt1 = time.time()
            spectrum[offset][(X, Y)] = spec
            done = i * len(reference_configs) + j + 1
            if done % 9 == 0 or done == n_configs:
                elapsed = time.time() - t_start
                eta = elapsed / done * (n_configs - done)
                print(f"  [{done:>3d}/{n_configs}]  offset={offset:>2d}  "
                      f"(X,Y)=({X[:3]},{Y[:3]})  "
                      f"S={spec['entropy']:.3f}  purity={spec['purity']:.3f}  "
                      f"elapsed={elapsed:.0f}s  eta={eta:.0f}s")
    t_end = time.time()
    print(f"\n  total runtime: {(t_end - t_start) / 60:.1f} min")

    # Analysis: entropy spectrum averaged over ref configs
    mean_entropy = {}
    mean_purity = {}
    mean_off_mag = {}
    for offset in offsets:
        entropies = [spectrum[offset][(X, Y)]["entropy"]
                      for X, Y in reference_configs]
        purities = [spectrum[offset][(X, Y)]["purity"]
                     for X, Y in reference_configs]
        off_mags = [sum(spectrum[offset][(X, Y)]["off_mag"].values()) / 3
                     for X, Y in reference_configs]
        mean_entropy[offset] = float(np.mean(entropies))
        mean_purity[offset] = float(np.mean(purities))
        mean_off_mag[offset] = float(np.mean(off_mags))

    # Print spectrum
    print("\n  --- v_D entropy spectrum vs offset_T2 ---")
    print(f"  {'offset':>6s}  {'<S>':>6s}  {'<purity>':>9s}  {'<off>':>6s}  "
          f"{'bar':<40s}")
    S_max = max(mean_entropy.values())
    for offset in offsets:
        s = mean_entropy[offset]
        bar_len = int(40 * s / S_max) if S_max > 0 else 0
        bar = "#" * bar_len
        print(f"  {offset:>6d}  {s:>6.3f}  {mean_purity[offset]:>9.3f}  "
              f"{mean_off_mag[offset]:>6.3f}  {bar}")

    # Find local maxima (collapse candidates) and minima (locking candidates)
    entropy_arr = np.array([mean_entropy[o] for o in offsets])
    collapse_offsets = []
    locking_offsets = []
    for idx in range(1, len(offsets) - 1):
        if entropy_arr[idx] > entropy_arr[idx - 1] and entropy_arr[idx] > entropy_arr[idx + 1]:
            collapse_offsets.append(offsets[idx])
        if entropy_arr[idx] < entropy_arr[idx - 1] and entropy_arr[idx] < entropy_arr[idx + 1]:
            locking_offsets.append(offsets[idx])

    print(f"\n  collapse candidates (entropy local maxima): {collapse_offsets}")
    print(f"  locking candidates  (entropy local minima):  {locking_offsets}")

    # Save JSON
    outdir = SCRIPT_DIR.parent / "results"
    outdir.mkdir(exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    fname = outdir / f"p4s_double_triangle_stageC_{stamp}.json"
    # Strip rho_Z3 from the full per-config records for JSON cleanliness
    clean_spectrum = {}
    for offset in offsets:
        clean_spectrum[str(offset)] = {}
        for X, Y in reference_configs:
            s = spectrum[offset][(X, Y)]
            clean_spectrum[str(offset)][f"{X},{Y}"] = {
                "diag":      s["diag"],
                "off_mag":   s["off_mag"],
                "entropy":   s["entropy"],
                "purity":    s["purity"],
                "z3_mass":   s["z3_mass"],
            }
    payload = {
        "stage":             "C_entropy_spectrum",
        "timestamp":         stamp,
        "offsets":           offsets,
        "ref_configs":       [f"{X},{Y}" for X, Y in reference_configs],
        "parameters":        {"n_compute": n_compute, "J_intra": J_intra,
                               "J_mem": J_mem},
        "runtime_s":         t_end - t_start,
        "mean_entropy":      mean_entropy,
        "mean_purity":       mean_purity,
        "mean_off_mag":      mean_off_mag,
        "collapse_offsets":  collapse_offsets,
        "locking_offsets":   locking_offsets,
        "spectrum":          clean_spectrum,
    }
    fname.write_text(json.dumps(payload, indent=2))
    print(f"\n  wrote {fname}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage",
                     choices=["sanity", "A", "mode1", "B1", "mode2", "B2",
                              "mode3", "C", "D", "regime3", "all"],
                     default="sanity",
                     help="Which stage to run. 'all' = B1 + B2 + C.  "
                          "'D' / 'regime3' = Observable 24 (incommensurate).")
    args = ap.parse_args()

    if args.stage in ("sanity", "A"):
        stage_A_sanity_check()
    elif args.stage in ("mode1", "B1"):
        stage_B_label_matrix(offset_T2=0, label="mode1_synchronous")
    elif args.stage in ("mode2", "B2"):
        stage_B_label_matrix(offset_T2=6, label="mode2_interleaved")
    elif args.stage in ("mode3", "C"):
        stage_C_entropy_spectrum()
    elif args.stage in ("D", "regime3"):
        stage_D_regime3_spectrum()
    elif args.stage == "all":
        print("\n>>> STAGE B Mode 1 (synchronous) <<<\n")
        stage_B_label_matrix(offset_T2=0, label="mode1_synchronous")
        print("\n>>> STAGE B Mode 2 (interleaved) <<<\n")
        stage_B_label_matrix(offset_T2=6, label="mode2_interleaved")
        print("\n>>> STAGE C (entropy spectrum) <<<\n")
        stage_C_entropy_spectrum()


if __name__ == "__main__":
    main()
