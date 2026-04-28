#!/usr/bin/env python3
"""
Protocol 4S-Z3 (structural memory test) - Qiskit Aer Implementation
====================================================================

Qiskit counterpart to cirq/run_p4s_Z3_cirq.py. Same four deterministic input
families, same SWAP-test readout, same no-external-drive condition - but run
through Qiskit Aer with depolarizing or calibrated FakeSherbrooke noise.

The cross-stack comparison tests whether the family-separation signal (if
any) is a property of the protocol rather than an artefact of either
simulator's transpilation or noise model.

Usage:
  python run_p4s_Z3_aer.py --sim-only
  python run_p4s_Z3_aer.py --sim-only --fake-backend sherbrooke
  python run_p4s_Z3_aer.py --sim-only --n-repeats 10 --shots 8192

Authors: Stenberg with Claude Anthropic, April 2026
"""
import argparse
import json
import math
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit.circuit.library import UnitaryGate
from qiskit_aer import AerSimulator

# Reuse the gate layer from run_p4s_aer.py
SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))
from run_p4s_aer import (
    cross_gate_4, horizontal_gate_4, diagonal_gate_4,
    internal_step_angles, build_depolarizing_noise,
    overlap_from_swap, zeros_from_counts, _simulator, _transpile,
    T_CYCLE,
)

RESULTS_DIR = SCRIPT_DIR.parent / "results"


# ============================================================================
#  Initial state families
# ============================================================================
def basis_state(n: int, d: int = 4) -> np.ndarray:
    v = np.zeros(d, dtype=complex)
    v[n] = 1.0
    return v


def uniform_state(d: int = 4) -> np.ndarray:
    return np.ones(d, dtype=complex) / math.sqrt(d)


def bell_like() -> np.ndarray:
    v = np.zeros(4, dtype=complex)
    v[0] = 1.0
    v[3] = 1.0
    return v / math.sqrt(2)


def make_families():
    return {
        "A_matched_basis_0":   (basis_state(0), basis_state(0)),
        "B_matched_uniform":   (uniform_state(),  uniform_state()),
        "C_orthog_0_3":        (basis_state(0),   basis_state(3)),
        "D_matched_bell_03":   (bell_like(),      bell_like()),
    }


# ============================================================================
#  Circuit builder (Qiskit)
# ============================================================================
def build_snapshot(u0: np.ndarray, v0: np.ndarray, steps_so_far: int) -> QuantumCircuit:
    q = QuantumRegister(5, "q")
    c = ClassicalRegister(1, "c")
    qc = QuantumCircuit(q, c)
    qc.initialize(u0, [q[0], q[1]])
    qc.initialize(v0, [q[2], q[3]])

    for k in range(steps_so_far):
        th_c, th_h, th_d = internal_step_angles(k % T_CYCLE)
        Cf, Ci = cross_gate_4(th_c)
        qc.append(UnitaryGate(Cf, label="Cf"), [q[0], q[1]])
        qc.append(UnitaryGate(Ci, label="Ci"), [q[2], q[3]])
        Hf, Hi = horizontal_gate_4(th_h)
        qc.append(UnitaryGate(Hf, label="Hf"), [q[0], q[1]])
        qc.append(UnitaryGate(Hi, label="Hi"), [q[2], q[3]])
        Df, Di = diagonal_gate_4(th_d)
        qc.append(UnitaryGate(Df, label="Df"), [q[0], q[1]])
        qc.append(UnitaryGate(Di, label="Di"), [q[2], q[3]])

    qc.h(q[4])
    qc.cswap(q[4], q[0], q[2])
    qc.cswap(q[4], q[1], q[3])
    qc.h(q[4])
    qc.measure(q[4], c[0])
    return qc


def run_family(u0, v0, n_periods=10, shots=8192, p_depol=0.005,
               fake_backend=None, n_repeats=5):
    sim = _simulator(p_depol, fake_backend)
    overlaps = np.zeros((n_repeats, n_periods))
    for rep in range(n_repeats):
        for period in range(1, n_periods + 1):
            circ = build_snapshot(u0, v0, period * T_CYCLE)
            tqc = _transpile(circ, sim, use_backend_calibration=(fake_backend is not None))
            result = sim.run(tqc, shots=shots).result()
            counts = result.get_counts()
            overlaps[rep, period - 1] = overlap_from_swap(
                zeros_from_counts(counts), shots)
    return overlaps


def summarise_family(overlaps: np.ndarray) -> dict:
    last5 = overlaps[:, -5:]
    return {
        "mean": float(np.mean(last5)),
        "std":  float(np.std(last5)),
        "min":  float(np.min(last5)),
        "max":  float(np.max(last5)),
        "per_period_mean": [float(x) for x in np.mean(overlaps, axis=0)],
    }


# ============================================================================
#  Main
# ============================================================================
def main():
    ap = argparse.ArgumentParser(description="Protocol 4S-Z3 (Qiskit Aer)")
    ap.add_argument("--sim-only", action="store_true")
    ap.add_argument("--fake-backend", default=None)
    ap.add_argument("--n-repeats", type=int, default=5)
    ap.add_argument("--shots", type=int, default=8192)
    ap.add_argument("--n-periods", type=int, default=10)
    ap.add_argument("--p-depol", type=float, default=0.005)
    args = ap.parse_args()

    families = make_families()
    noise_tag = args.fake_backend or f"depol_{args.p_depol}"
    print(f"Protocol 4S-Z3 (Aer) | {len(families)} families | noise={noise_tag} "
          f"| n_repeats={args.n_repeats} | shots={args.shots}")
    print("=" * 78)

    results = {}
    for name, (u0, v0) in families.items():
        initial = float(abs(np.vdot(u0, v0)))
        print(f"\n[{name}]  initial |<u|v>| = {initial:.4f}")
        overlaps = run_family(u0, v0, n_periods=args.n_periods,
                              shots=args.shots, p_depol=args.p_depol,
                              fake_backend=args.fake_backend,
                              n_repeats=args.n_repeats)
        summary = summarise_family(overlaps)
        results[name] = {
            "initial_overlap": initial,
            "summary": summary,
            "raw": overlaps.tolist(),
        }
        print(f"    last-5 mean: {summary['mean']:.4f} +/- {summary['std']:.4f}  "
              f"[{summary['min']:.3f}, {summary['max']:.3f}]")
        print("    per-period mean:  " +
              "  ".join(f"{x:.3f}" for x in summary["per_period_mean"]))

    print("\n" + "=" * 78)
    print("  CROSS-FAMILY COMPARISON (last-5 attractor values)")
    print("=" * 78)
    means = {k: v["summary"]["mean"] for k, v in results.items()}
    stds  = {k: v["summary"]["std"]  for k, v in results.items()}
    for k, m in means.items():
        print(f"  {k:25s}  {m:.4f} +/- {stds[k]:.4f}")

    all_means = list(means.values())
    span = max(all_means) - min(all_means)
    max_std = max(stds.values())
    separable = span > 5 * max_std

    print()
    print(f"  Range across families: {span:.4f}")
    print(f"  Max within-family std: {max_std:.4f}")
    print(f"  Range / std ratio:     {span / max(max_std, 1e-9):.2f}")
    if separable:
        print("  VERDICT: STRUCTURAL memory signal present.")
    else:
        print("  VERDICT: THERMALISATION (families converge).")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "stack": "qiskit_aer",
        "parameters": {
            "n_repeats":    args.n_repeats,
            "shots":        args.shots,
            "n_periods":    args.n_periods,
            "p_depol":      args.p_depol,
            "fake_backend": args.fake_backend,
        },
        "families": results,
        "cross_family": {
            "means": means, "stds": stds,
            "span": span, "max_std": max_std, "separable": separable,
        },
    }
    tag = args.fake_backend or "depol"
    out = RESULTS_DIR / f"p4s_Z3_aer_{tag}_{datetime.now():%Y%m%dT%H%M%S}.json"
    out.write_text(json.dumps(payload, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
