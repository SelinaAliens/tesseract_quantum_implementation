#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PROTOCOL 4S - Cirq simulation of the 2-to-4 spinor self-sustaining threshold.

Tests the Level 5 prediction of genesis_pipeline.py in actual quantum circuits
(Cirq simulator) rather than numpy matrix multiplication. If Cirq reproduces
the pipeline's |<u|v>| ~ 0.47 self-sustaining result at 4-spinor and freezing
at 2-spinor under no external drive, the protocol is ready for hardware
pre-registration on IBM or Google Willow.

Architecture:
  - 4-spinor merkabit: u, v in C^4 each, encoded on 2+2=4 physical qubits
  - Three isoclinic rotation planes applied as internal dynamics (no Floquet
    modulation, no time-varying angles)
  - Overlap |<u|v>| measured via SWAP test with one ancilla -> 5 qubits total
  - 2-spinor control: u, v in C^2 each, 1 qubit each, no internal
    cross-coupling available -> frozen under no-drive condition

The 4x4 isoclinic gate matrices are the same objects from internal_step_4 in
genesis_pipeline.py, here installed as cirq.MatrixGate 2-qubit gates.

Usage: python protocol_4S_cirq.py
"""
from __future__ import annotations
import math
import numpy as np
import cirq


# -------------------------------------------------------------------------
# Isoclinic rotation gates (copied from genesis_pipeline.internal_step_4)
# -------------------------------------------------------------------------
def cross_gate_4(theta: float):
    c, s = math.cos(theta / 2), math.sin(theta / 2)
    Cf = np.array([[c, 0, -s, 0], [0, c, 0, -s],
                   [s, 0,  c, 0], [0, s, 0,  c]], dtype=complex)
    Ci = np.array([[c, 0,  s, 0], [0, c, 0,  s],
                   [-s, 0, c, 0], [0, -s, 0, c]], dtype=complex)
    return Cf, Ci


def cross_gate_horizontal_4(theta: float):
    c, s = math.cos(theta / 2), math.sin(theta / 2)
    Cf = np.array([[c, -s, 0, 0], [s, c, 0, 0],
                   [0, 0, c, -s], [0, 0, s, c]], dtype=complex)
    Ci = np.array([[c, s, 0, 0], [-s, c, 0, 0],
                   [0, 0, c, s], [0, 0, -s, c]], dtype=complex)
    return Cf, Ci


def cross_gate_diagonal_4(theta: float):
    c, s = math.cos(theta / 2), math.sin(theta / 2)
    Cf = np.array([[c, 0, 0, -s], [0, c, -s, 0],
                   [0, s, c, 0], [s, 0, 0, c]], dtype=complex)
    Ci = np.array([[c, 0, 0, s], [0, c, s, 0],
                   [0, -s, c, 0], [-s, 0, 0, c]], dtype=complex)
    return Cf, Ci


def internal_step_angles(step_index: int, coupling: float = 1.0, coxeter_h: int = 12):
    """Three isoclinic rotation angles for one internal step."""
    theta = (2 * math.pi / coxeter_h) * coupling
    omega_k = 2 * math.pi * step_index / coxeter_h
    th_cross = theta * (1.0 + 0.3 * math.cos(omega_k))
    th_horiz = theta * (1.0 + 0.3 * math.cos(omega_k + 2 * math.pi / 3))
    th_diag  = theta * (1.0 + 0.3 * math.cos(omega_k + 4 * math.pi / 3))
    return th_cross, th_horiz, th_diag


def random_unit_vector(dim: int, rng: np.random.Generator) -> np.ndarray:
    v = rng.normal(size=dim) + 1j * rng.normal(size=dim)
    return v / np.linalg.norm(v)


# -------------------------------------------------------------------------
# Cirq circuit builders
# -------------------------------------------------------------------------
def state_prep_2q(u: np.ndarray, qubits, label: str) -> cirq.Gate:
    """Prepare the 2-qubit state |u> starting from |00>, via a 4x4 unitary
    whose first column is u. We fill the remaining columns with a Gram-Schmidt
    completion so the overall matrix is unitary."""
    assert len(u) == 4
    M = np.zeros((4, 4), dtype=complex)
    M[:, 0] = u
    for k in range(1, 4):
        e = np.zeros(4, dtype=complex); e[k] = 1.0
        for j in range(k):
            e = e - np.vdot(M[:, j], e) * M[:, j]
        M[:, k] = e / np.linalg.norm(e)
    return cirq.MatrixGate(M, name=f"Prep_{label}")


def build_4spinor_circuit(u0: np.ndarray, v0: np.ndarray, n_periods: int = 10,
                          coxeter_h: int = 12, measure_every_period: bool = True):
    """
    Build a Cirq circuit for the 4-spinor self-sustaining test with SWAP-test
    overlap measurement.

    Qubits: q0, q1 = u register; q2, q3 = v register; q4 = ancilla.
    Each 'internal period' is coxeter_h steps; each step applies the three
    isoclinic rotations in sequence (no external Floquet modulation).
    """
    qubits = cirq.LineQubit.range(5)
    q_u = (qubits[0], qubits[1])
    q_v = (qubits[2], qubits[3])
    anc = qubits[4]

    circuits = []
    total_steps = coxeter_h * n_periods

    base = cirq.Circuit()
    base.append(state_prep_2q(u0, q_u, "u").on(*q_u))
    base.append(state_prep_2q(v0, q_v, "v").on(*q_v))

    for step in range(total_steps):
        th_cross, th_horiz, th_diag = internal_step_angles(step % coxeter_h)

        Cf, Ci = cross_gate_4(th_cross)
        base.append(cirq.MatrixGate(Cf, name="Cf_x").on(*q_u))
        base.append(cirq.MatrixGate(Ci, name="Ci_x").on(*q_v))

        Hf, Hi = cross_gate_horizontal_4(th_horiz)
        base.append(cirq.MatrixGate(Hf, name="Hf_h").on(*q_u))
        base.append(cirq.MatrixGate(Hi, name="Hi_h").on(*q_v))

        Df, Di = cross_gate_diagonal_4(th_diag)
        base.append(cirq.MatrixGate(Df, name="Df_d").on(*q_u))
        base.append(cirq.MatrixGate(Di, name="Di_d").on(*q_v))

        if measure_every_period and (step + 1) % coxeter_h == 0:
            snapshot = base.copy()
            # SWAP test: apply H on ancilla, controlled-SWAP u <-> v, H on ancilla,
            # measure ancilla. P(0) = (1 + |<u|v>|^2) / 2.
            snapshot.append(cirq.H(anc))
            snapshot.append(cirq.CSWAP(anc, q_u[0], q_v[0]))
            snapshot.append(cirq.CSWAP(anc, q_u[1], q_v[1]))
            snapshot.append(cirq.H(anc))
            snapshot.append(cirq.measure(anc, key=f"anc_p{(step+1)//coxeter_h}"))
            circuits.append(((step + 1) // coxeter_h, snapshot))

    return circuits, qubits


def build_2spinor_control_circuit(u0: np.ndarray, v0: np.ndarray,
                                  n_periods: int = 10, coxeter_h: int = 12):
    """
    2-spinor control: u, v in C^2 each, 1 qubit each. No internal cross-coupling
    channel available in 2D spinor space, so internal dynamics = identity.
    Measured overlap should be frozen at initial value across all periods.
    """
    q0, q1, anc = cirq.LineQubit.range(3)

    def prep_1q(u: np.ndarray, qubit):
        assert len(u) == 2
        M = np.zeros((2, 2), dtype=complex)
        M[:, 0] = u
        e = np.array([-u[1].conjugate(), u[0].conjugate()])
        e = e / np.linalg.norm(e)
        M[:, 1] = e
        return cirq.MatrixGate(M, name="Prep").on(qubit)

    circuits = []
    for period in range(1, n_periods + 1):
        c = cirq.Circuit()
        c.append(prep_1q(u0, q0))
        c.append(prep_1q(v0, q1))
        # internal dynamics = identity (no isoclinic channel in 2D)
        c.append(cirq.H(anc))
        c.append(cirq.CSWAP(anc, q0, q1))
        c.append(cirq.H(anc))
        c.append(cirq.measure(anc, key=f"anc_p{period}"))
        circuits.append((period, c))
    return circuits


def overlap_from_swap_counts(counts_zero: int, total: int) -> float:
    """P(0) = (1 + |<u|v>|^2) / 2  =>  |<u|v>| = sqrt(2 * P(0) - 1)."""
    p0 = counts_zero / total
    inner_sq = max(0.0, 2 * p0 - 1.0)
    return math.sqrt(inner_sq)


# -------------------------------------------------------------------------
# Main
# -------------------------------------------------------------------------
def _with_noise(circuit: cirq.Circuit, p_depol: float) -> cirq.Circuit:
    """Insert a depolarizing channel after each operation. Per-gate error
    approximates Willow's typical 2-qubit gate error p ~ 0.005."""
    if p_depol <= 0:
        return circuit
    noisy = cirq.Circuit()
    for moment in circuit:
        noisy.append(moment, strategy=cirq.InsertStrategy.NEW_THEN_INLINE)
        for op in moment.operations:
            if isinstance(op.gate, cirq.MeasurementGate):
                continue
            n = len(op.qubits)
            if n == 1:
                noisy.append(cirq.depolarize(p_depol * 0.1).on(*op.qubits))
            elif n == 2:
                noisy.append(cirq.depolarize(p_depol).on_each(*op.qubits))
            elif n == 3:
                noisy.append(cirq.depolarize(p_depol * 1.5).on_each(*op.qubits))
    return noisy


def _simulator(p_depol: float) -> cirq.SimulatesSamples:
    """Return a density-matrix simulator when noise is non-zero, otherwise
    the state-vector simulator for speed."""
    if p_depol > 0:
        return cirq.DensityMatrixSimulator()
    return cirq.Simulator()


def run_4spinor(n_trials: int = 3, shots: int = 8192, n_periods: int = 10,
                p_depol: float = 0.0, rng_seed: int = 0):
    rng = np.random.default_rng(rng_seed)
    sim = _simulator(p_depol)
    trial_results = []

    for trial in range(n_trials):
        u0 = random_unit_vector(4, rng)
        v0 = random_unit_vector(4, rng)
        ideal_initial = abs(np.vdot(u0, v0))
        circuits, _ = build_4spinor_circuit(u0, v0, n_periods=n_periods)

        overlaps = []
        for period, circ in circuits:
            key = f"anc_p{period}"
            noisy = _with_noise(circ, p_depol)
            result = sim.run(noisy, repetitions=shots)
            hist = result.histogram(key=key)
            zeros = int(hist.get(0, 0))
            overlaps.append(overlap_from_swap_counts(zeros, shots))

        trial_results.append({
            "trial": trial,
            "ideal_initial_overlap": ideal_initial,
            "overlaps_per_period": overlaps,
        })
    return trial_results


def run_2spinor_control(n_trials: int = 3, shots: int = 8192, n_periods: int = 10,
                        p_depol: float = 0.0, rng_seed: int = 1):
    rng = np.random.default_rng(rng_seed)
    sim = _simulator(p_depol)
    trial_results = []

    for trial in range(n_trials):
        u0 = random_unit_vector(2, rng)
        v0 = random_unit_vector(2, rng)
        ideal_initial = abs(np.vdot(u0, v0))
        circuits = build_2spinor_control_circuit(u0, v0, n_periods=n_periods)

        overlaps = []
        for period, circ in circuits:
            key = f"anc_p{period}"
            noisy = _with_noise(circ, p_depol)
            result = sim.run(noisy, repetitions=shots)
            hist = result.histogram(key=key)
            zeros = int(hist.get(0, 0))
            overlaps.append(overlap_from_swap_counts(zeros, shots))

        trial_results.append({
            "trial": trial,
            "ideal_initial_overlap": ideal_initial,
            "overlaps_per_period": overlaps,
        })
    return trial_results


def report(results, label: str):
    print(f"\n{'='*78}\n  {label}\n{'='*78}")
    for r in results:
        print(f"\n  Trial {r['trial']}:")
        print(f"    ideal initial |<u|v>|   = {r['ideal_initial_overlap']:.4f}")
        print(f"    measured per period     = "
              + ", ".join(f"{x:.3f}" for x in r['overlaps_per_period']))
        last5 = r['overlaps_per_period'][-5:]
        print(f"    mean of last 5 periods  = {np.mean(last5):.4f}")
        print(f"    min of last 5 periods   = {np.min(last5):.4f}")


def run_pipeline_reference_numpy(n_trials: int = 3, n_periods: int = 10, coxeter_h: int = 12):
    """Numpy reference (exact state evolution) - sanity check vs Cirq."""
    rng = np.random.default_rng(0)
    results = []
    for trial in range(n_trials):
        u = random_unit_vector(4, rng); v = random_unit_vector(4, rng)
        overlaps = []
        for step in range(coxeter_h * n_periods):
            th_c, th_h, th_d = internal_step_angles(step % coxeter_h)
            Cf, Ci = cross_gate_4(th_c);               u = Cf @ u; v = Ci @ v
            Hf, Hi = cross_gate_horizontal_4(th_h);    u = Hf @ u; v = Hi @ v
            Df, Di = cross_gate_diagonal_4(th_d);      u = Df @ u; v = Di @ v
            u /= np.linalg.norm(u); v /= np.linalg.norm(v)
            if (step + 1) % coxeter_h == 0:
                overlaps.append(abs(np.vdot(u, v)))
        results.append({"trial": trial, "overlaps": overlaps})
    return results


def summarise(results, label: str):
    m = [np.mean(r['overlaps_per_period'][-5:]) for r in results]
    return {
        "label": label,
        "n_trials": len(results),
        "across_trial_mean": float(np.mean(m)),
        "across_trial_std":  float(np.std(m)),
        "min_of_means":      float(np.min(m)),
        "max_of_means":      float(np.max(m)),
    }


def run_full_sweep(n_trials: int = 20, shots: int = 4096, n_periods: int = 10,
                   noise_levels=(0.0, 0.002, 0.005, 0.01)):
    """Run 4-spinor and 2-spinor protocols across several Willow-realistic
    depolarizing rates. Returns a dict keyed by p_depol."""
    out = {}
    for p in noise_levels:
        tag = f"p={p}"
        print(f"\n{'-'*78}\n  Running at depolarizing p_depol = {p}  (n_trials={n_trials}, shots={shots})\n{'-'*78}")
        r4 = run_4spinor(n_trials=n_trials, shots=shots, n_periods=n_periods,
                         p_depol=p, rng_seed=0)
        r2 = run_2spinor_control(n_trials=n_trials, shots=shots, n_periods=n_periods,
                                 p_depol=p, rng_seed=1)
        s4 = summarise(r4, f"4-spinor {tag}")
        s2 = summarise(r2, f"2-spinor {tag}")
        # also measure 2-spinor drift (distance between mean and initial)
        drifts = [abs(np.mean(r['overlaps_per_period']) - r['ideal_initial_overlap'])
                  for r in r2]
        s2["drift_mean"] = float(np.mean(drifts))
        s2["drift_max"]  = float(np.max(drifts))
        out[p] = {"4spinor": s4, "2spinor": s2, "raw_4": r4, "raw_2": r2}
        print(f"    4-spinor mean last-5 (across {n_trials} trials): "
              f"{s4['across_trial_mean']:.4f} +/- {s4['across_trial_std']:.4f}  "
              f"[min {s4['min_of_means']:.3f}, max {s4['max_of_means']:.3f}]")
        print(f"    2-spinor drift from initial: mean {s2['drift_mean']:.4f}, "
              f"max {s2['drift_max']:.4f}")
    return out


if __name__ == "__main__":
    import sys, json
    print("PROTOCOL 4S - Cirq simulation (noise-modeled, 20 trials)")
    print("="*78)
    print("Genesis pipeline Level 5 predicts:")
    print("  4-spinor: |<u|v>| sustains, mean of last 5 periods ~0.47")
    print("             (trial-dependent band, predicted range [0.30, 0.65])")
    print("  2-spinor: |<u|v>| frozen at initial value (no internal channel)")
    print()

    noise_levels = (0.0, 0.002, 0.005, 0.01)
    n_trials = 20
    shots = 4096
    sweep = run_full_sweep(n_trials=n_trials, shots=shots, noise_levels=noise_levels)

    print("\n" + "="*78 + "\n  SUMMARY TABLE\n" + "="*78)
    header = f"  {'p_depol':>10} {'4S mean last5':>15} {'+/- std':>10} "
    header += f"{'min':>7} {'max':>7} | {'2C drift avg':>14} {'max':>7}"
    print(header)
    print("  " + "-" * (len(header) - 2))
    for p in noise_levels:
        s4 = sweep[p]["4spinor"]; s2 = sweep[p]["2spinor"]
        print(f"  {p:>10.4f} {s4['across_trial_mean']:>15.4f} "
              f"{s4['across_trial_std']:>10.4f} {s4['min_of_means']:>7.3f} "
              f"{s4['max_of_means']:>7.3f} | {s2['drift_mean']:>14.4f} "
              f"{s2['drift_max']:>7.4f}")

    # pass/fail against Willow-realistic p_depol=0.005
    willow_p = 0.005
    s4_w = sweep[willow_p]["4spinor"]
    s2_w = sweep[willow_p]["2spinor"]
    sustains = s4_w["across_trial_mean"] >= 0.25 and s4_w["min_of_means"] >= 0.10
    frozen = s2_w["drift_max"] < 0.10
    verdict = sustains and frozen

    print("\n" + "="*78 + "\n  WILLOW PRE-REGISTRATION PREDICTION (p_depol = 0.005)\n" + "="*78)
    print(f"  4-spinor mean of last 5 periods across 20 initial states: "
          f"{s4_w['across_trial_mean']:.3f} +/- {s4_w['across_trial_std']:.3f}")
    print(f"  4-spinor trial range: [{s4_w['min_of_means']:.3f}, {s4_w['max_of_means']:.3f}]")
    print(f"  2-spinor drift from initial (max across trials): {s2_w['drift_max']:.3f}")
    print(f"  Protocol 4S: {'READY for hardware pre-registration' if verdict else 'NEEDS DEBUG'}")

    # write JSON summary for the experiments/ directory
    if len(sys.argv) > 1 and sys.argv[1] == "--json":
        summary = {
            "n_trials": n_trials,
            "shots": shots,
            "n_periods": 10,
            "sweep": {
                str(p): {"4spinor": sweep[p]["4spinor"], "2spinor": sweep[p]["2spinor"]}
                for p in noise_levels
            },
        }
        with open("protocol_4S_sim_summary.json", "w") as f:
            json.dump(summary, f, indent=2)
        print("\n  Wrote protocol_4S_sim_summary.json")
