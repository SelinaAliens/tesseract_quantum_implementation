#!/usr/bin/env python3
"""
Protocol 4S-Z3 short-horizon sweep - Qiskit Aer cross-check.

Companion to cirq/run_p4s_Z3_short_cirq.py. Same (n_periods, p_depol) grid,
same Family A (matched basis |0>) vs Family C (orthogonal |0>, |3>)
comparison, same 10 repeats x 4096 shots budget. The cross-stack agreement
test rules out simulator-specific artefacts in the short-horizon viable
region.

Usage: python run_p4s_Z3_short_aer.py
       python run_p4s_Z3_short_aer.py --fake-backend sherbrooke
"""
import argparse
import json
import math
import sys
from datetime import datetime
from pathlib import Path

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
from run_p4s_Z3_aer import basis_state, build_snapshot

RESULTS_DIR = SCRIPT_DIR.parent / "results"


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

    periods = [1, 2, 3, 5, 7, 10]
    if args.fake_backend:
        noise = [None]
    else:
        noise = [0.0, 0.001, 0.002, 0.005]
    families = {
        "A_matched_basis_0": (basis_state(0), basis_state(0)),
        "C_orthog_0_3":      (basis_state(0), basis_state(3)),
    }

    noise_tag = args.fake_backend or "depol_sweep"
    print(f"Protocol 4S-Z3 short-horizon (Aer) | {noise_tag}")
    print(f"periods={periods}  n_repeats={args.n_repeats}  shots={args.shots}")
    print()
    print(f"{'n_periods':>9} {'noise':>12} | {'A mean':>7} {'A SEM':>7} | {'C mean':>7} {'C SEM':>7} | {'gap':>7} {'gap/SEM_tot':>11}")
    print("-" * 90)

    results = {}
    for n_p in periods:
        results[str(n_p)] = {}
        for p in noise:
            cells = {}
            for fname, (u0, v0) in families.items():
                arr = measure_single_horizon(
                    u0, v0, n_p, p if p is not None else 0.0,
                    fake_backend=args.fake_backend,
                    n_repeats=args.n_repeats, shots=args.shots)
                cells[fname] = {
                    "values": arr.tolist(),
                    "mean":   float(np.mean(arr)),
                    "std":    float(np.std(arr, ddof=1)),
                    "sem":    float(np.std(arr, ddof=1) / math.sqrt(args.n_repeats)),
                }
            ma = cells["A_matched_basis_0"]["mean"]
            mc = cells["C_orthog_0_3"]["mean"]
            sa = cells["A_matched_basis_0"]["sem"]
            sc = cells["C_orthog_0_3"]["sem"]
            gap = ma - mc
            sem_tot = math.sqrt(sa ** 2 + sc ** 2)
            ratio = gap / max(sem_tot, 1e-9)
            noise_label = args.fake_backend if args.fake_backend else f"{p:.4f}"
            print(f"{n_p:>9d} {noise_label:>12} | {ma:>7.4f} {sa:>7.4f} | {mc:>7.4f} {sc:>7.4f} | {gap:>7.4f} {ratio:>11.2f}")
            key = args.fake_backend if args.fake_backend else str(p)
            results[str(n_p)][key] = {
                "A": cells["A_matched_basis_0"],
                "C": cells["C_orthog_0_3"],
                "gap": gap,
                "sem_total": sem_tot,
                "gap_over_sem": ratio,
            }

    if not args.fake_backend:
        print()
        print("Viability heatmap (gap/SEM > 3 means the alignment signal is detectable):")
        header = "  " + " ".join(f"{p:>7.3f}" for p in noise)
        print(f"{'':>10}{header}")
        for n_p in periods:
            row = [results[str(n_p)][str(p)]["gap_over_sem"] for p in noise]
            cells_str = " ".join(f"{'PASS' if abs(r) > 3 else 'fail':>7s}" for r in row)
            print(f"{n_p:>10d}  {cells_str}")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "stack": "qiskit_aer",
        "fake_backend": args.fake_backend,
        "n_repeats":    args.n_repeats,
        "shots":        args.shots,
        "periods":      periods,
        "results":      results,
    }
    tag = args.fake_backend or "depol"
    out = RESULTS_DIR / f"p4s_Z3_short_aer_{tag}_{datetime.now():%Y%m%dT%H%M%S}.json"
    out.write_text(json.dumps(payload, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
