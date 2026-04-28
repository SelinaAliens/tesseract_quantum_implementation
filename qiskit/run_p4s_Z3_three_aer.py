#!/usr/bin/env python3
"""
Protocol 4S-Z3-three (Qiskit Aer) - companion to cirq/run_p4s_Z3_three_cirq.py.

Tests whether three Z_3 eigenstate families (alpha, beta, gamma) give three
distinct attractor means at short horizons - the minimum requirement for
true ternary (rather than just binary) memory on the tesseract substrate.

Five families, three short horizons (n = 2, 3, 5), four noise levels.
Cross-stack agreement with Cirq rules out implementation artefacts.

Usage: python run_p4s_Z3_three_aer.py
"""
import argparse
import json
import math
import sys
from datetime import datetime
from pathlib import Path
from itertools import combinations

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.circuit.library import UnitaryGate
from qiskit_aer import AerSimulator

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))
from run_p4s_aer import (
    cross_gate_4, horizontal_gate_4, diagonal_gate_4,
    internal_step_angles, overlap_from_swap, zeros_from_counts,
    _simulator, _transpile, T_CYCLE,
)
from run_p4s_Z3_aer import build_snapshot

RESULTS_DIR = SCRIPT_DIR.parent / "results"

OMEGA = complex(math.cos(2 * math.pi / 3), math.sin(2 * math.pi / 3))


def basis_state(n: int) -> np.ndarray:
    v = np.zeros(4, dtype=complex)
    v[n] = 1.0
    return v


def z3_eigenstate(eigenvalue_power: int) -> np.ndarray:
    k = eigenvalue_power % 3
    coeffs = np.array([
        1.0,
        OMEGA ** (-k),
        OMEGA ** (-2 * k),
        0.0,
    ], dtype=complex)
    return coeffs / math.sqrt(3)


def make_families():
    return {
        "A_matched_basis_0":  (basis_state(0),   basis_state(0)),
        "C_orthog_0_3":       (basis_state(0),   basis_state(3)),
        "alpha_Z3_1":         (z3_eigenstate(0), z3_eigenstate(0)),
        "beta_Z3_omega":      (z3_eigenstate(1), z3_eigenstate(1)),
        "gamma_Z3_omega2":    (z3_eigenstate(2), z3_eigenstate(2)),
    }


def measure_single_horizon(u0, v0, n_periods, p_depol, fake_backend=None,
                           n_repeats=10, shots=4096):
    sim = _simulator(p_depol, fake_backend)
    overlaps = []
    for _ in range(n_repeats):
        circ = build_snapshot(u0, v0, n_periods * T_CYCLE)
        tqc = _transpile(circ, sim,
                         use_backend_calibration=(fake_backend is not None))
        result = sim.run(tqc, shots=shots).result()
        counts = result.get_counts()
        overlaps.append(overlap_from_swap(zeros_from_counts(counts), shots))
    return np.array(overlaps)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-repeats", type=int, default=10)
    ap.add_argument("--shots", type=int, default=4096)
    ap.add_argument("--fake-backend", default=None)
    args = ap.parse_args()

    periods = [2, 3, 5]
    if args.fake_backend:
        noise_levels = [None]
    else:
        noise_levels = [0.0, 0.001, 0.002, 0.005]
    families = make_families()

    tag = args.fake_backend or "depol_sweep"
    print(f"Protocol 4S-Z3-three (Aer) | {tag} | 5 families | periods={periods}")

    results = {}
    for n_p in periods:
        results[str(n_p)] = {}
        for p in noise_levels:
            print(f"\n[n_periods={n_p}, noise={args.fake_backend or p}]")
            cells = {}
            for fname, (u0, v0) in families.items():
                arr = measure_single_horizon(
                    u0, v0, n_p,
                    p if p is not None else 0.0,
                    fake_backend=args.fake_backend,
                    n_repeats=args.n_repeats, shots=args.shots,
                )
                cells[fname] = {
                    "values": arr.tolist(),
                    "mean":   float(np.mean(arr)),
                    "std":    float(np.std(arr, ddof=1)),
                    "sem":    float(np.std(arr, ddof=1) / math.sqrt(args.n_repeats)),
                }
                print(f"  {fname:22s}  mean={cells[fname]['mean']:.4f}  "
                      f"sem={cells[fname]['sem']:.4f}")
            pairs = {}
            for a, b in combinations(families.keys(), 2):
                gap = cells[a]["mean"] - cells[b]["mean"]
                sem_tot = math.sqrt(cells[a]["sem"] ** 2 + cells[b]["sem"] ** 2)
                ratio = gap / max(sem_tot, 1e-9)
                pairs[f"{a}__vs__{b}"] = {
                    "gap":       gap,
                    "sem_total": sem_tot,
                    "gap_over_sem": ratio,
                }
            key = args.fake_backend if args.fake_backend else str(p)
            results[str(n_p)][key] = {"cells": cells, "pairs": pairs}

            print("  Z_3 ternary tests:")
            for a, b in [
                ("alpha_Z3_1",    "beta_Z3_omega"),
                ("alpha_Z3_1",    "gamma_Z3_omega2"),
                ("beta_Z3_omega", "gamma_Z3_omega2"),
            ]:
                pkey = f"{a}__vs__{b}"
                pair = pairs[pkey]
                status = "PASS" if abs(pair["gap_over_sem"]) > 3 else "fail"
                print(f"    {a:22s} vs {b:22s}  "
                      f"gap={pair['gap']:+.4f}  sigma={pair['gap_over_sem']:+.2f}  [{status}]")

    if not args.fake_backend:
        print("\n" + "=" * 78)
        print("  TERNARY MEMORY: alpha, beta, gamma all pairwise separable?")
        print("=" * 78)
        print(f"{'n_p':>4} {'p':>7} | {'|a-b|/sem':>11} {'|a-g|/sem':>11} {'|b-g|/sem':>11} | All > 3?")
        print("-" * 78)
        for n_p in periods:
            for p in noise_levels:
                cell = results[str(n_p)][str(p)]["pairs"]
                ab = abs(cell["alpha_Z3_1__vs__beta_Z3_omega"]["gap_over_sem"])
                ag = abs(cell["alpha_Z3_1__vs__gamma_Z3_omega2"]["gap_over_sem"])
                bg = abs(cell["beta_Z3_omega__vs__gamma_Z3_omega2"]["gap_over_sem"])
                all_sep = min(ab, ag, bg) > 3
                print(f"{n_p:>4} {p:>7.4f} | {ab:>11.2f} {ag:>11.2f} {bg:>11.2f} | {'YES' if all_sep else 'no'}")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp":    datetime.now().isoformat(timespec="seconds"),
        "stack":        "qiskit_aer",
        "fake_backend": args.fake_backend,
        "n_repeats":    args.n_repeats,
        "shots":        args.shots,
        "periods":      periods,
        "results":      results,
    }
    out_tag = args.fake_backend or "depol"
    out = RESULTS_DIR / f"p4s_Z3_three_aer_{out_tag}_{datetime.now():%Y%m%dT%H%M%S}.json"
    out.write_text(json.dumps(payload, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
