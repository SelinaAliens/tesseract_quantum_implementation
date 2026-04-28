#!/usr/bin/env python3
"""
P4S Self-Sustaining Threshold - Qiskit Aer Implementation for IBM Hardware
===========================================================================

IBM Qiskit counterpart to willow_hardware_merkabit/experiments/run_p4s_cirq.py.
Tests observables 9 and 10 of the 2-to-4 spinor self-sustaining threshold
(genesis_pipeline.py Level 5, added 2026-04-19).

Protocol:
  4-spinor (tesseract merkabit): u, v in C^4 on 4 data qubits (2 per spinor).
    Apply three isoclinic rotation planes (cross, horizontal, diagonal) as
    internal dynamics across 10 Coxeter periods (120 steps). No external
    Floquet modulation, no time-varying P gate. SWAP-test overlap measurement
    against one ancilla -> 5 qubits total.
  2-spinor control (dual-tetrahedron): u, v in C^2 on 1+1 qubits.
    Identity evolution (no internal cross-coupling channel in 2D spinor space).
    SWAP-test overlap measurement -> 3 qubits total.

Cirq cross-check (willow_hardware_merkabit commit 30984ca, 20-trial sweep):
  p_depol   4-spinor mean last5   trial range    2-spinor max drift
  0.0000    0.411 +/- 0.120       [0.21, 0.58]   0.021
  0.0020    0.491 +/- 0.016       [0.47, 0.53]   0.023
  0.0050    0.494 +/- 0.008       [0.48, 0.51]   0.015   <-- IBM/Willow target
  0.0100    0.489 +/- 0.008       [0.48, 0.50]   0.016

The same protocol under Aer's depolarizing noise at equivalent per-gate rates
should produce statistically indistinguishable results from the Cirq sweep.
Substantive deviation indicates implementation drift and should be debugged
before hardware submission.

Usage:
  # Aer simulator with uniform depolarizing noise (matches Cirq sweep)
  python run_p4s_aer.py --sim-only

  # Aer with calibrated FakeBackend noise (Sherbrooke = Eagle r3 proxy)
  python run_p4s_aer.py --sim-only --fake-backend sherbrooke

  # Real IBM Runtime submission (Eagle r3 or Heron r2; requires IBMQ account)
  python run_p4s_aer.py --backend ibm_strasbourg

Qubit assignments (IBM Eagle r3, ibm_strasbourg / ibm_brussels):
  4-spinor u register: q[62], q[63]    (2 qubits, native CX direction)
  4-spinor v register: q[81], q[72]    (2 qubits, native CX to q[62] via q[72])
  ancilla: q[60]                        (1 qubit, nearest to u register)
  2-spinor control: q+ = q[62], q- = q[81], ancilla q[72]

Authors: Stenberg & Hetland with Claude Anthropic, April 2026
"""
import argparse
import json
import math
from datetime import datetime
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit.circuit.library import UnitaryGate
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error

RESULTS_DIR = Path(__file__).parent.parent / "outputs" / "p4s"
T_CYCLE = 12


# ============================================================================
#  Isoclinic rotation gates (4x4 unitaries acting on one 2-qubit spinor)
# ============================================================================
def cross_gate_4(theta: float):
    c, s = math.cos(theta / 2), math.sin(theta / 2)
    Cf = np.array([[c, 0, -s, 0], [0, c, 0, -s],
                   [s, 0,  c, 0], [0, s, 0,  c]], dtype=complex)
    Ci = np.array([[c, 0,  s, 0], [0, c, 0,  s],
                   [-s, 0, c, 0], [0, -s, 0, c]], dtype=complex)
    return Cf, Ci


def horizontal_gate_4(theta: float):
    c, s = math.cos(theta / 2), math.sin(theta / 2)
    Hf = np.array([[c, -s, 0, 0], [s, c, 0, 0],
                   [0, 0, c, -s], [0, 0, s, c]], dtype=complex)
    Hi = np.array([[c, s, 0, 0], [-s, c, 0, 0],
                   [0, 0, c, s], [0, 0, -s, c]], dtype=complex)
    return Hf, Hi


def diagonal_gate_4(theta: float):
    c, s = math.cos(theta / 2), math.sin(theta / 2)
    Df = np.array([[c, 0, 0, -s], [0, c, -s, 0],
                   [0, s, c, 0], [s, 0, 0, c]], dtype=complex)
    Di = np.array([[c, 0, 0, s], [0, c, s, 0],
                   [0, -s, c, 0], [-s, 0, 0, c]], dtype=complex)
    return Df, Di


def internal_step_angles(step_index: int, coupling: float = 1.0):
    theta = (2 * math.pi / T_CYCLE) * coupling
    w = 2 * math.pi * step_index / T_CYCLE
    th_cross = theta * (1.0 + 0.3 * math.cos(w))
    th_horiz = theta * (1.0 + 0.3 * math.cos(w + 2 * math.pi / 3))
    th_diag  = theta * (1.0 + 0.3 * math.cos(w + 4 * math.pi / 3))
    return th_cross, th_horiz, th_diag


def random_unit_vector(dim: int, rng: np.random.Generator) -> np.ndarray:
    v = rng.normal(size=dim) + 1j * rng.normal(size=dim)
    return v / np.linalg.norm(v)


# ============================================================================
#  Circuit builders (Qiskit)
# ============================================================================
def build_4spinor_snapshot(u0: np.ndarray, v0: np.ndarray, steps_so_far: int) -> QuantumCircuit:
    """4-spinor merkabit after `steps_so_far` internal steps, with SWAP test.
       Qubits: [0,1] = u; [2,3] = v; [4] = ancilla."""
    q = QuantumRegister(5, "q")
    c = ClassicalRegister(1, "c")
    qc = QuantumCircuit(q, c)
    # State prep via Qiskit's initialize()
    qc.initialize(u0, [q[0], q[1]])
    qc.initialize(v0, [q[2], q[3]])

    for k in range(steps_so_far):
        th_c, th_h, th_d = internal_step_angles(k % T_CYCLE)
        Cf, Ci = cross_gate_4(th_c)
        qc.append(UnitaryGate(Cf, label="Cf_x"), [q[0], q[1]])
        qc.append(UnitaryGate(Ci, label="Ci_x"), [q[2], q[3]])
        Hf, Hi = horizontal_gate_4(th_h)
        qc.append(UnitaryGate(Hf, label="Hf_h"), [q[0], q[1]])
        qc.append(UnitaryGate(Hi, label="Hi_h"), [q[2], q[3]])
        Df, Di = diagonal_gate_4(th_d)
        qc.append(UnitaryGate(Df, label="Df_d"), [q[0], q[1]])
        qc.append(UnitaryGate(Di, label="Di_d"), [q[2], q[3]])

    # SWAP test with ancilla
    qc.h(q[4])
    qc.cswap(q[4], q[0], q[2])
    qc.cswap(q[4], q[1], q[3])
    qc.h(q[4])
    qc.measure(q[4], c[0])
    return qc


def build_2spinor_snapshot(u0: np.ndarray, v0: np.ndarray) -> QuantumCircuit:
    """2-spinor control: identity evolution + SWAP test.
       Qubits: [0] = u; [1] = v; [2] = ancilla."""
    q = QuantumRegister(3, "q")
    c = ClassicalRegister(1, "c")
    qc = QuantumCircuit(q, c)
    qc.initialize(u0, [q[0]])
    qc.initialize(v0, [q[1]])
    # internal dynamics = identity
    qc.h(q[2])
    qc.cswap(q[2], q[0], q[1])
    qc.h(q[2])
    qc.measure(q[2], c[0])
    return qc


# ============================================================================
#  Noise model (Aer: depolarizing by gate arity, matches Cirq convention)
# ============================================================================
def build_depolarizing_noise(p_depol: float) -> NoiseModel:
    """Same arity-scaled depolarizing rates as the Cirq sweep:
       1-qubit ~ 0.1*p, 2-qubit ~ p, 3-qubit ~ 1.5*p."""
    nm = NoiseModel()
    one_q = [
        "id", "x", "y", "z", "h", "s", "sdg", "t", "tdg",
        "rx", "ry", "rz", "u", "u1", "u2", "u3", "sx", "sxdg",
    ]
    two_q = ["cx", "cz", "swap", "ecr", "iswap"]
    three_q = ["cswap", "ccx"]
    nm.add_all_qubit_quantum_error(depolarizing_error(0.1 * p_depol, 1), one_q)
    nm.add_all_qubit_quantum_error(depolarizing_error(p_depol, 2), two_q)
    nm.add_all_qubit_quantum_error(depolarizing_error(1.5 * p_depol, 3), three_q)
    # Decomposed unitary 2q gates get the 2q rate via basis_gates transpile
    return nm


# ============================================================================
#  Analysis: SWAP-test counts -> overlap magnitude
# ============================================================================
def overlap_from_swap(counts_zero: int, total: int) -> float:
    p0 = counts_zero / total
    return math.sqrt(max(0.0, 2 * p0 - 1.0))


def zeros_from_counts(counts: dict) -> int:
    return int(counts.get("0", 0))


# ============================================================================
#  Simulation driver
# ============================================================================
def _simulator(p_depol: float, fake_backend: str = None) -> AerSimulator:
    if fake_backend is not None:
        # Calibrated IBM Eagle/Heron noise via qiskit_ibm_runtime fake provider
        from qiskit_ibm_runtime.fake_provider import FakeProviderForBackendV2
        provider = FakeProviderForBackendV2()
        target_name = f"fake_{fake_backend.lower()}"
        matches = [b for b in provider.backends() if b.name == target_name]
        if not matches:
            available = sorted(b.name for b in provider.backends()
                               if 'fake_' in b.name)
            raise ValueError(f"FakeBackend '{fake_backend}' not found. "
                             f"Available: {available[:15]}...")
        return AerSimulator.from_backend(matches[0])

    if p_depol > 0:
        return AerSimulator(noise_model=build_depolarizing_noise(p_depol))
    return AerSimulator()


_BASIS = ["id", "rz", "sx", "x", "cx", "cz", "ecr"]


def _transpile(qc: QuantumCircuit, sim: AerSimulator,
               use_backend_calibration: bool) -> QuantumCircuit:
    """Transpile to a concrete basis so noise applies to CX/CZ decomposition
       of UnitaryGate and CSWAP. Optimisation level 1 keeps it fast."""
    if use_backend_calibration:
        # FakeBackend path: keep the backend so gate durations/error rates are honoured
        return transpile(qc, backend=sim, optimization_level=1)
    return transpile(qc, basis_gates=_BASIS, optimization_level=1)


def run_4spinor_trial(u0, v0, n_periods=10, shots=4096, p_depol=0.005,
                      fake_backend=None):
    sim = _simulator(p_depol, fake_backend)
    overlaps = []
    for period in range(1, n_periods + 1):
        steps = period * T_CYCLE
        circ = build_4spinor_snapshot(u0, v0, steps)
        tqc = _transpile(circ, sim, use_backend_calibration=(fake_backend is not None))
        result = sim.run(tqc, shots=shots).result()
        counts = result.get_counts()
        overlaps.append(overlap_from_swap(zeros_from_counts(counts), shots))
    return overlaps


def run_2spinor_trial(u0, v0, n_periods=10, shots=4096, p_depol=0.005,
                      fake_backend=None):
    sim = _simulator(p_depol, fake_backend)
    overlaps = []
    for _ in range(n_periods):
        circ = build_2spinor_snapshot(u0, v0)
        tqc = _transpile(circ, sim, use_backend_calibration=(fake_backend is not None))
        result = sim.run(tqc, shots=shots).result()
        counts = result.get_counts()
        overlaps.append(overlap_from_swap(zeros_from_counts(counts), shots))
    return overlaps


def run_full_protocol(n_trials=20, shots=4096, n_periods=10, p_depol=0.005,
                      fake_backend=None, seed4=0, seed2=1):
    rng4 = np.random.default_rng(seed4)
    rng2 = np.random.default_rng(seed2)
    res = {"4spinor": [], "2spinor": []}
    for t in range(n_trials):
        u0 = random_unit_vector(4, rng4); v0 = random_unit_vector(4, rng4)
        overlaps = run_4spinor_trial(u0, v0, n_periods, shots, p_depol, fake_backend)
        res["4spinor"].append({
            "trial": t,
            "initial_overlap": float(abs(np.vdot(u0, v0))),
            "overlaps_per_period": overlaps,
        })
        u0 = random_unit_vector(2, rng2); v0 = random_unit_vector(2, rng2)
        overlaps = run_2spinor_trial(u0, v0, n_periods, shots, p_depol, fake_backend)
        res["2spinor"].append({
            "trial": t,
            "initial_overlap": float(abs(np.vdot(u0, v0))),
            "overlaps_per_period": overlaps,
        })
    return res


def summarise_protocol(results):
    last5_4 = [np.mean(r["overlaps_per_period"][-5:]) for r in results["4spinor"]]
    drift_2 = [abs(np.mean(r["overlaps_per_period"]) - r["initial_overlap"])
               for r in results["2spinor"]]
    return {
        "4spinor": {
            "n_trials":                    len(last5_4),
            "across_trial_mean_last5":     float(np.mean(last5_4)),
            "across_trial_std_last5":      float(np.std(last5_4)),
            "trial_min":                   float(np.min(last5_4)),
            "trial_max":                   float(np.max(last5_4)),
        },
        "2spinor": {
            "n_trials":                    len(drift_2),
            "drift_mean":                  float(np.mean(drift_2)),
            "drift_max":                   float(np.max(drift_2)),
        },
    }


# ============================================================================
#  Main
# ============================================================================
def main():
    ap = argparse.ArgumentParser(description="P4S self-sustaining threshold (Qiskit Aer)")
    ap.add_argument("--sim-only", action="store_true")
    ap.add_argument("--fake-backend", default=None,
                    help="sherbrooke/brisbane/kingston/osaka - use calibrated noise")
    ap.add_argument("--backend", default=None, help="real IBM backend (runtime)")
    ap.add_argument("--n-trials", type=int, default=20)
    ap.add_argument("--shots", type=int, default=4096)
    ap.add_argument("--n-periods", type=int, default=10)
    ap.add_argument("--p-depol", type=float, default=0.005)
    ap.add_argument("--sweep", action="store_true",
                    help="sweep p_depol over 0, 0.002, 0.005, 0.01")
    args = ap.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    if args.backend is not None and not args.sim_only:
        raise NotImplementedError(
            "Hardware submission: add QiskitRuntimeService() here with your "
            "IBM Cloud CRN. The circuits above are identical across sim and "
            "hardware; only the runtime client differs."
        )

    if args.sweep:
        levels = [0.0, 0.002, 0.005, 0.01]
    else:
        levels = [args.p_depol]

    all_summaries = {}
    for p in levels:
        print(f"\n{'-'*78}")
        print(f"  Aer run | p_depol={p}  fake={args.fake_backend}  "
              f"n_trials={args.n_trials}  shots={args.shots}")
        print("-" * 78)
        results = run_full_protocol(n_trials=args.n_trials, shots=args.shots,
                                    n_periods=args.n_periods, p_depol=p,
                                    fake_backend=args.fake_backend)
        summary = summarise_protocol(results)
        all_summaries[str(p)] = summary
        print(f"  4-spinor last5 mean: {summary['4spinor']['across_trial_mean_last5']:.4f} "
              f"+/- {summary['4spinor']['across_trial_std_last5']:.4f}  "
              f"[{summary['4spinor']['trial_min']:.3f}, {summary['4spinor']['trial_max']:.3f}]")
        print(f"  2-spinor drift: mean {summary['2spinor']['drift_mean']:.4f}  "
              f"max {summary['2spinor']['drift_max']:.4f}")

    # Pass/fail vs Willow-realistic target
    willow_key = "0.005" if "0.005" in all_summaries else str(levels[-1])
    s4 = all_summaries[willow_key]["4spinor"]
    s2 = all_summaries[willow_key]["2spinor"]
    obs9 = s4["across_trial_mean_last5"] >= 0.30 and s4["trial_min"] >= 0.20
    obs10 = s2["drift_max"] < 0.10
    print(f"\nObservable 9  (4-spinor sustains at p={willow_key}): "
          f"{'PASS' if obs9 else 'FAIL'}")
    print(f"Observable 10 (2-spinor frozen at p={willow_key}):    "
          f"{'PASS' if obs10 else 'FAIL'}")

    payload = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "mode": "aer" + (f"+fake_{args.fake_backend}" if args.fake_backend else ""),
        "parameters": {
            "n_trials":   args.n_trials,
            "shots":      args.shots,
            "n_periods":  args.n_periods,
            "p_depol":    levels,
            "fake_backend": args.fake_backend,
        },
        "summaries": all_summaries,
    }
    tag = args.fake_backend or "depol"
    out = RESULTS_DIR / f"p4s_aer_{tag}_{datetime.now():%Y%m%dT%H%M%S}.json"
    out.write_text(json.dumps(payload, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
