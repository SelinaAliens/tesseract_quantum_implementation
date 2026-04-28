#!/usr/bin/env python3
"""
P4S Self-Sustaining Threshold — Cirq Implementation for Google Hardware
========================================================================

Tests the 2-to-4 spinor self-sustaining prediction (observables 9 and 10 of the
Willow pre-registration, added 2026-04-19 from genesis_pipeline.py Level 5).

Protocol:
  4-spinor (tesseract merkabit): u, v in C^4, encoded on 4 data qubits.
    Apply three isoclinic rotation planes (cross, horizontal, diagonal) as
    internal dynamics for 10 Coxeter periods (120 steps). No external Floquet
    modulation, no time-varying P gate. Measure |<u|v>| via SWAP test.
  2-spinor (dual-tetrahedron control): u, v in C^2, one qubit each.
    No internal cross-coupling channel available in 2D spinor space; internal
    dynamics reduce to identity. Measure |<u|v>| via SWAP test.

Prediction (from 20-trial, 4-noise-level Cirq sweep at p_depol in {0, 2e-3,
5e-3, 1e-2}; protocol_4S_sim_summary.json):
  4-spinor mean |<u|v>| over last 5 periods across 10+ random initial states:
    0.49 +/- 0.03 at Willow-realistic p_depol = 0.005
  2-spinor max drift from initial overlap: < 0.05

Hardware resource budget: 4 data qubits + 1 ancilla, ~200 circuits at 4,096
shots each, under 1 QPU-hour. No two-qubit gates beyond those required by the
isoclinic rotations themselves (~6 CZ-equivalents per internal step).

Usage:
  python run_p4s_cirq.py --sim-only
  python run_p4s_cirq.py --project YOUR_PROJECT --processor PROCESSOR_ID

Authors: Stenberg & Hetland with Claude Anthropic, April 2026
"""
import argparse
import json
import math
from datetime import datetime
from pathlib import Path

import numpy as np
import cirq

RESULTS_DIR = Path(__file__).parent.parent / "outputs" / "p4s"
T_CYCLE = 12

# ============================================================================
#  Isoclinic rotation gates (4x4 unitaries acting on one 2-qubit spinor)
# ============================================================================
def cross_gate_4(theta: float):
    """Isoclinic rotation in the (0,2)+(1,3) plane pair."""
    c, s = math.cos(theta / 2), math.sin(theta / 2)
    Cf = np.array([[c, 0, -s, 0], [0, c, 0, -s],
                   [s, 0,  c, 0], [0, s, 0,  c]], dtype=complex)
    Ci = np.array([[c, 0,  s, 0], [0, c, 0,  s],
                   [-s, 0, c, 0], [0, -s, 0, c]], dtype=complex)
    return Cf, Ci


def horizontal_gate_4(theta: float):
    """Isoclinic rotation in the (0,1)+(2,3) plane pair."""
    c, s = math.cos(theta / 2), math.sin(theta / 2)
    Hf = np.array([[c, -s, 0, 0], [s, c, 0, 0],
                   [0, 0, c, -s], [0, 0, s, c]], dtype=complex)
    Hi = np.array([[c, s, 0, 0], [-s, c, 0, 0],
                   [0, 0, c, s], [0, 0, -s, c]], dtype=complex)
    return Hf, Hi


def diagonal_gate_4(theta: float):
    """Isoclinic rotation in the (0,3)+(1,2) plane pair."""
    c, s = math.cos(theta / 2), math.sin(theta / 2)
    Df = np.array([[c, 0, 0, -s], [0, c, -s, 0],
                   [0, s, c, 0], [s, 0, 0, c]], dtype=complex)
    Di = np.array([[c, 0, 0, s], [0, c, s, 0],
                   [0, -s, c, 0], [-s, 0, 0, c]], dtype=complex)
    return Df, Di


def internal_step_angles(step_index: int, coupling: float = 1.0):
    """Three triality-phased rotation angles for one internal step."""
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
#  State preparation as a 2-qubit MatrixGate (Gram-Schmidt completion)
# ============================================================================
def state_prep_2q(u: np.ndarray, label: str) -> cirq.MatrixGate:
    assert len(u) == 4
    M = np.zeros((4, 4), dtype=complex)
    M[:, 0] = u
    for k in range(1, 4):
        e = np.zeros(4, dtype=complex); e[k] = 1.0
        for j in range(k):
            e = e - np.vdot(M[:, j], e) * M[:, j]
        M[:, k] = e / np.linalg.norm(e)
    return cirq.MatrixGate(M, name=f"Prep_{label}")


def state_prep_1q(u: np.ndarray) -> cirq.MatrixGate:
    assert len(u) == 2
    M = np.zeros((2, 2), dtype=complex)
    M[:, 0] = u
    M[:, 1] = np.array([-u[1].conjugate(), u[0].conjugate()])
    M[:, 1] /= np.linalg.norm(M[:, 1])
    return cirq.MatrixGate(M, name="Prep")


# ============================================================================
#  Circuit builders
# ============================================================================
def build_4spinor_snapshot(u0: np.ndarray, v0: np.ndarray, steps_so_far: int):
    """4-spinor circuit at one snapshot time (end of steps_so_far internal steps).
    Qubits: 0,1 = u register; 2,3 = v register; 4 = SWAP-test ancilla."""
    q = cirq.LineQubit.range(5)
    q_u, q_v, anc = (q[0], q[1]), (q[2], q[3]), q[4]
    c = cirq.Circuit()
    c.append(state_prep_2q(u0, "u").on(*q_u))
    c.append(state_prep_2q(v0, "v").on(*q_v))
    for k in range(steps_so_far):
        th_c, th_h, th_d = internal_step_angles(k % T_CYCLE)
        Cf, Ci = cross_gate_4(th_c)
        c.append(cirq.MatrixGate(Cf, name="Cf_x").on(*q_u))
        c.append(cirq.MatrixGate(Ci, name="Ci_x").on(*q_v))
        Hf, Hi = horizontal_gate_4(th_h)
        c.append(cirq.MatrixGate(Hf, name="Hf_h").on(*q_u))
        c.append(cirq.MatrixGate(Hi, name="Hi_h").on(*q_v))
        Df, Di = diagonal_gate_4(th_d)
        c.append(cirq.MatrixGate(Df, name="Df_d").on(*q_u))
        c.append(cirq.MatrixGate(Di, name="Di_d").on(*q_v))
    # SWAP test against ancilla
    c.append(cirq.H(anc))
    c.append(cirq.CSWAP(anc, q_u[0], q_v[0]))
    c.append(cirq.CSWAP(anc, q_u[1], q_v[1]))
    c.append(cirq.H(anc))
    c.append(cirq.measure(anc, key="anc"))
    return c


def build_2spinor_snapshot(u0: np.ndarray, v0: np.ndarray):
    """2-spinor control: no internal dynamics (identity), SWAP-test only."""
    q0, q1, anc = cirq.LineQubit.range(3)
    c = cirq.Circuit()
    c.append(state_prep_1q(u0).on(q0))
    c.append(state_prep_1q(v0).on(q1))
    # internal dynamics = identity; no isoclinic channel in 2D spinor space
    c.append(cirq.H(anc))
    c.append(cirq.CSWAP(anc, q0, q1))
    c.append(cirq.H(anc))
    c.append(cirq.measure(anc, key="anc"))
    return c


# ============================================================================
#  Noise model
# ============================================================================
def inject_depolarize(circuit: cirq.Circuit, p: float) -> cirq.Circuit:
    """Willow-realistic depolarizing channel per gate. p is the 2-qubit-gate
    rate; 1q is 10x smaller, 3q (CSWAP) is 1.5x larger per qubit."""
    if p <= 0:
        return circuit
    out = cirq.Circuit()
    for moment in circuit:
        out.append(moment, strategy=cirq.InsertStrategy.NEW_THEN_INLINE)
        for op in moment.operations:
            if isinstance(op.gate, cirq.MeasurementGate):
                continue
            n = len(op.qubits)
            scale = {1: 0.1, 2: 1.0, 3: 1.5}.get(n, 1.0)
            out.append(cirq.depolarize(p * scale).on_each(*op.qubits))
    return out


# ============================================================================
#  Analysis: SWAP-test counts -> overlap magnitude
# ============================================================================
def overlap_from_swap(counts_zero: int, total: int) -> float:
    """P(ancilla=0) = (1 + |<u|v>|^2) / 2."""
    p0 = counts_zero / total
    return math.sqrt(max(0.0, 2 * p0 - 1.0))


# ============================================================================
#  Simulation driver
# ============================================================================
def run_4spinor_trial(u0, v0, n_periods=10, shots=4096, p_depol=0.005):
    sim = cirq.DensityMatrixSimulator() if p_depol > 0 else cirq.Simulator()
    overlaps = []
    for period in range(1, n_periods + 1):
        steps = period * T_CYCLE
        circ = build_4spinor_snapshot(u0, v0, steps)
        circ = inject_depolarize(circ, p_depol)
        res = sim.run(circ, repetitions=shots)
        zeros = int(res.histogram(key="anc").get(0, 0))
        overlaps.append(overlap_from_swap(zeros, shots))
    return overlaps


def run_2spinor_trial(u0, v0, n_periods=10, shots=4096, p_depol=0.005):
    sim = cirq.DensityMatrixSimulator() if p_depol > 0 else cirq.Simulator()
    overlaps = []
    for _ in range(n_periods):
        circ = build_2spinor_snapshot(u0, v0)
        circ = inject_depolarize(circ, p_depol)
        res = sim.run(circ, repetitions=shots)
        zeros = int(res.histogram(key="anc").get(0, 0))
        overlaps.append(overlap_from_swap(zeros, shots))
    return overlaps


def run_full_protocol(n_trials=20, shots=4096, n_periods=10, p_depol=0.005,
                      seed4=0, seed2=1):
    rng4 = np.random.default_rng(seed4)
    rng2 = np.random.default_rng(seed2)
    res = {"4spinor": [], "2spinor": []}
    for t in range(n_trials):
        u0 = random_unit_vector(4, rng4); v0 = random_unit_vector(4, rng4)
        overlaps = run_4spinor_trial(u0, v0, n_periods, shots, p_depol)
        res["4spinor"].append({
            "trial": t,
            "initial_overlap": float(abs(np.vdot(u0, v0))),
            "overlaps_per_period": overlaps,
        })
        u0 = random_unit_vector(2, rng2); v0 = random_unit_vector(2, rng2)
        overlaps = run_2spinor_trial(u0, v0, n_periods, shots, p_depol)
        res["2spinor"].append({
            "trial": t,
            "initial_overlap": float(abs(np.vdot(u0, v0))),
            "overlaps_per_period": overlaps,
        })
    return res


def summarise_protocol(results):
    """Summary statistics for the Willow pre-registration comparison."""
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
    ap = argparse.ArgumentParser(description="P4S self-sustaining threshold test")
    ap.add_argument("--sim-only", action="store_true",
                    help="run Cirq simulator only (no hardware submission)")
    ap.add_argument("--project", default=None, help="GCP project ID for hardware")
    ap.add_argument("--processor", default=None, help="Willow processor ID")
    ap.add_argument("--n-trials", type=int, default=20)
    ap.add_argument("--shots", type=int, default=4096)
    ap.add_argument("--n-periods", type=int, default=10)
    ap.add_argument("--p-depol", type=float, default=0.005,
                    help="per-2q-gate depolarizing rate for sim; ignored on hardware")
    args = ap.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"P4S self-sustaining threshold  |  n_trials={args.n_trials}  "
          f"shots={args.shots}  n_periods={args.n_periods}  p_depol={args.p_depol}")

    if args.sim_only or args.project is None:
        results = run_full_protocol(n_trials=args.n_trials, shots=args.shots,
                                    n_periods=args.n_periods, p_depol=args.p_depol)
        summary = summarise_protocol(results)

        print("\n4-SPINOR (tesseract merkabit, internal dynamics only)")
        print(f"  mean of last 5 periods across {args.n_trials} trials: "
              f"{summary['4spinor']['across_trial_mean_last5']:.4f} +/- "
              f"{summary['4spinor']['across_trial_std_last5']:.4f}")
        print(f"  trial range: [{summary['4spinor']['trial_min']:.3f}, "
              f"{summary['4spinor']['trial_max']:.3f}]")
        print("\n2-SPINOR CONTROL (no internal channel)")
        print(f"  drift from initial (mean):  {summary['2spinor']['drift_mean']:.4f}")
        print(f"  drift from initial (max):   {summary['2spinor']['drift_max']:.4f}")

        # Willow pre-registration falsification thresholds (see PREDICTION.md)
        obs9_pass = (summary["4spinor"]["across_trial_mean_last5"] >= 0.30
                     and summary["4spinor"]["trial_min"] >= 0.20)
        obs10_pass = summary["2spinor"]["drift_max"] < 0.10
        print(f"\nObservable 9  (4-spinor sustains):  "
              f"{'PASS' if obs9_pass else 'FAIL'}")
        print(f"Observable 10 (2-spinor frozen):    "
              f"{'PASS' if obs10_pass else 'FAIL'}")

        payload = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "mode": "simulation",
            "parameters": {
                "n_trials":  args.n_trials,
                "shots":     args.shots,
                "n_periods": args.n_periods,
                "p_depol":   args.p_depol,
            },
            "summary": summary,
            "raw": results,
        }
        out = RESULTS_DIR / f"p4s_sim_{datetime.utcnow():%Y%m%dT%H%M%S}.json"
        out.write_text(json.dumps(payload, indent=2))
        print(f"\nWrote {out}")
    else:
        raise NotImplementedError(
            "Hardware submission path is pre-registered; add the Google "
            "quantum engine client here once credentials are in place. The "
            "Cirq circuits above are the full protocol; no modification is "
            "required for hardware execution."
        )


if __name__ == "__main__":
    main()
