#!/usr/bin/env python3
"""
Protocol 4S-Z3 (structural memory test) - Cirq Implementation
==============================================================

Follow-up to Protocol 4S. Tests whether the tesseract's internal dynamics
preserve information about the initial state, or thermalise fully.

The question this experiment answers:

  Haar-random initial states settle to |<u|v>| ~ 0.47-0.50 (close to the
  Haar expectation 1/sqrt(d) = 0.5 for d=4). Is this attractor a structural
  fixed point of the tesseract, or is it just thermal equilibration that
  erases the initial state?

Test: prepare four DISTINCT, DETERMINISTIC input families and evolve each
under Protocol 4S internal dynamics. Compare the attractor values.

  Family A  Matched basis     u = v = |0>                       overlap(0) = 1
  Family B  Matched uniform   u = v = (|0>+|1>+|2>+|3>)/2       overlap(0) = 1
  Family C  Orthogonal basis  u = |0>, v = |3>                  overlap(0) = 0
  Family D  Matched Bell-like u = v = (|0>+|3>)/sqrt(2)         overlap(0) = 1

Prediction under the "thermalisation" hypothesis:
  All four families settle to the same attractor ~0.47-0.50 by period 10.

Prediction under the "structural memory" hypothesis:
  The four families settle to distinct attractors whose difference is
  larger than the shot-noise error bar.

Structural memory is the prerequisite for the substrate to encode
computation. If families thermalise, self-sustaining coherence is real but
the substrate is a noise source, not a memory. If families differentiate,
the substrate can hold an input label across many Coxeter periods - the
minimum requirement for a ternary computational primitive.

Usage:
  python run_p4s_Z3_cirq.py --sim-only
  python run_p4s_Z3_cirq.py --sim-only --n-repeats 10 --shots 8192

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
import cirq

# Reuse the gate layer from run_p4s_cirq.py; state_prep is replaced locally
# with a QR-based completion that handles basis-state inputs without
# degenerating (the pre-registered state_prep_2q uses standard-basis-seeded
# Gram-Schmidt which fails when u = |3>).
SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))
from run_p4s_cirq import (
    cross_gate_4, horizontal_gate_4, diagonal_gate_4,
    internal_step_angles, inject_depolarize, overlap_from_swap,
    T_CYCLE,
)


def state_prep_2q(u: np.ndarray, label: str) -> cirq.MatrixGate:
    """Robust 2-qubit state prep via QR completion. First column = u,
    remaining columns = orthonormal completion, works even when u is a
    standard basis vector."""
    assert len(u) == 4
    rng = np.random.default_rng(12345)
    M = np.zeros((4, 4), dtype=complex)
    M[:, 0] = u
    # fill remaining columns with deterministic random, then QR
    M[:, 1:] = (rng.normal(size=(4, 3)) + 1j * rng.normal(size=(4, 3)))
    Q, _ = np.linalg.qr(M)
    # align first column of Q with u (QR may flip sign / phase)
    phase = np.vdot(u, Q[:, 0])
    if abs(phase) > 1e-12:
        Q[:, 0] *= phase.conjugate() / abs(phase)
    # final matrix: first column = u, remaining = orthonormal completion
    Mfinal = np.zeros((4, 4), dtype=complex)
    Mfinal[:, 0] = u
    Mfinal[:, 1:] = Q[:, 1:]
    return cirq.MatrixGate(Mfinal, name=f"Prep_{label}")

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
#  Circuit builder (reusing the Protocol 4S structure but with deterministic
#  state prep)
# ============================================================================
def build_snapshot(u0: np.ndarray, v0: np.ndarray, steps_so_far: int) -> cirq.Circuit:
    q = cirq.LineQubit.range(5)
    q_u, q_v, anc = (q[0], q[1]), (q[2], q[3]), q[4]
    c = cirq.Circuit()
    c.append(state_prep_2q(u0, "u").on(*q_u))
    c.append(state_prep_2q(v0, "v").on(*q_v))

    for k in range(steps_so_far):
        th_c, th_h, th_d = internal_step_angles(k % T_CYCLE)
        Cf, Ci = cross_gate_4(th_c)
        c.append(cirq.MatrixGate(Cf, name="Cf").on(*q_u))
        c.append(cirq.MatrixGate(Ci, name="Ci").on(*q_v))
        Hf, Hi = horizontal_gate_4(th_h)
        c.append(cirq.MatrixGate(Hf, name="Hf").on(*q_u))
        c.append(cirq.MatrixGate(Hi, name="Hi").on(*q_v))
        Df, Di = diagonal_gate_4(th_d)
        c.append(cirq.MatrixGate(Df, name="Df").on(*q_u))
        c.append(cirq.MatrixGate(Di, name="Di").on(*q_v))

    c.append(cirq.H(anc))
    c.append(cirq.CSWAP(anc, q_u[0], q_v[0]))
    c.append(cirq.CSWAP(anc, q_u[1], q_v[1]))
    c.append(cirq.H(anc))
    c.append(cirq.measure(anc, key="anc"))
    return c


def run_family(u0, v0, n_periods=10, shots=8192, p_depol=0.005, n_repeats=5):
    """Run the Protocol 4S internal dynamics with a deterministic input
    family. n_repeats repetitions gives a shot-noise error bar."""
    sim = cirq.DensityMatrixSimulator() if p_depol > 0 else cirq.Simulator()
    # Shape: [n_repeats, n_periods]
    overlaps = np.zeros((n_repeats, n_periods))
    for rep in range(n_repeats):
        for period in range(1, n_periods + 1):
            circ = build_snapshot(u0, v0, period * T_CYCLE)
            circ = inject_depolarize(circ, p_depol)
            result = sim.run(circ, repetitions=shots)
            zeros = int(result.histogram(key="anc").get(0, 0))
            overlaps[rep, period - 1] = overlap_from_swap(zeros, shots)
    return overlaps


def summarise_family(overlaps: np.ndarray) -> dict:
    """last-5-periods statistics."""
    last5 = overlaps[:, -5:]
    return {
        "mean":    float(np.mean(last5)),
        "std":     float(np.std(last5)),
        "min":     float(np.min(last5)),
        "max":     float(np.max(last5)),
        "per_period_mean": [float(x) for x in np.mean(overlaps, axis=0)],
    }


# ============================================================================
#  Main
# ============================================================================
def main():
    ap = argparse.ArgumentParser(description="Protocol 4S-Z3 structural memory test")
    ap.add_argument("--sim-only", action="store_true")
    ap.add_argument("--n-repeats", type=int, default=5)
    ap.add_argument("--shots", type=int, default=8192)
    ap.add_argument("--n-periods", type=int, default=10)
    ap.add_argument("--p-depol", type=float, default=0.005)
    args = ap.parse_args()

    families = make_families()
    print(f"Protocol 4S-Z3 | {len(families)} families | n_repeats={args.n_repeats} "
          f"| shots={args.shots} | p_depol={args.p_depol}")
    print("=" * 78)

    results = {}
    for name, (u0, v0) in families.items():
        initial = float(abs(np.vdot(u0, v0)))
        print(f"\n[{name}]  initial |<u|v>| = {initial:.4f}")
        overlaps = run_family(u0, v0, n_periods=args.n_periods,
                              shots=args.shots, p_depol=args.p_depol,
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

    # ---- cross-family comparison ----
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
        print("  VERDICT: Families separate beyond shot noise -> "
              "STRUCTURAL memory signal present.")
    else:
        print("  VERDICT: Families consistent within shot noise -> "
              "THERMALISATION (no memory) at these parameters.")

    # save JSON
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "stack": "cirq",
        "parameters": {
            "n_repeats": args.n_repeats,
            "shots":     args.shots,
            "n_periods": args.n_periods,
            "p_depol":   args.p_depol,
        },
        "families": results,
        "cross_family": {
            "means": means, "stds": stds,
            "span": span, "max_std": max_std, "separable": separable,
        },
    }
    out = RESULTS_DIR / f"p4s_Z3_cirq_{datetime.now():%Y%m%dT%H%M%S}.json"
    out.write_text(json.dumps(payload, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
