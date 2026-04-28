#!/usr/bin/env python3
"""
Protocol 4S-Z3-three-P (Qiskit Aer) - chiral internal-step cross-check.

Same extension as cirq/run_p4s_Z3_three_P_cirq.py: add the P gate
(Rz(+phi) (x) Rz(-phi) = diag(1, e^{-i*phi}, e^{+i*phi}, 1)) to the
internal step of the 4-spinor tesseract and retest whether beta and
gamma separate into distinct attractors.

Usage: python run_p4s_Z3_three_P_aer.py
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
    overlap_from_swap, zeros_from_counts,
    _simulator, _transpile, T_CYCLE,
)
from run_p4s_Z3_three_aer import make_families

RESULTS_DIR = SCRIPT_DIR.parent / "results"


# ============================================================================
#  Chiral internals (mirror Cirq)
# ============================================================================
def p_gate_4(phi: float):
    e_plus  = complex(math.cos(phi), math.sin(phi))
    e_minus = complex(math.cos(phi), -math.sin(phi))
    Pf = np.diag([1.0 + 0j, e_minus, e_plus, 1.0 + 0j]).astype(complex)
    Pi = np.diag([1.0 + 0j, e_plus,  e_minus, 1.0 + 0j]).astype(complex)
    return Pf, Pi


def internal_step_angles_chiral(step_index: int, coupling: float = 1.0,
                                p_coupling: float = 1.0):
    theta = (2 * math.pi / T_CYCLE) * coupling
    phi_p = (2 * math.pi / T_CYCLE) * p_coupling
    w = 2 * math.pi * step_index / T_CYCLE
    th_cross = theta * (1.0 + 0.3 * math.cos(w))
    th_horiz = theta * (1.0 + 0.3 * math.cos(w + 2 * math.pi / 3))
    th_diag  = theta * (1.0 + 0.3 * math.cos(w + 4 * math.pi / 3))
    phi_p_k  = phi_p * (1.0 + 0.3 * math.cos(w))
    return th_cross, th_horiz, th_diag, phi_p_k


def build_snapshot_chiral(u0: np.ndarray, v0: np.ndarray, steps_so_far: int,
                          p_coupling: float = 1.0) -> QuantumCircuit:
    q = QuantumRegister(5, "q")
    c = ClassicalRegister(1, "c")
    qc = QuantumCircuit(q, c)
    qc.initialize(u0, [q[0], q[1]])
    qc.initialize(v0, [q[2], q[3]])

    for k in range(steps_so_far):
        th_c, th_h, th_d, phi_p = internal_step_angles_chiral(
            k % T_CYCLE, p_coupling=p_coupling)
        Cf, Ci = cross_gate_4(th_c)
        qc.append(UnitaryGate(Cf, label="Cf"), [q[0], q[1]])
        qc.append(UnitaryGate(Ci, label="Ci"), [q[2], q[3]])
        Hf, Hi = horizontal_gate_4(th_h)
        qc.append(UnitaryGate(Hf, label="Hf"), [q[0], q[1]])
        qc.append(UnitaryGate(Hi, label="Hi"), [q[2], q[3]])
        Df, Di = diagonal_gate_4(th_d)
        qc.append(UnitaryGate(Df, label="Df"), [q[0], q[1]])
        qc.append(UnitaryGate(Di, label="Di"), [q[2], q[3]])
        Pf, Pi = p_gate_4(phi_p)
        qc.append(UnitaryGate(Pf, label="Pf"), [q[0], q[1]])
        qc.append(UnitaryGate(Pi, label="Pi"), [q[2], q[3]])

    qc.h(q[4])
    qc.cswap(q[4], q[0], q[2])
    qc.cswap(q[4], q[1], q[3])
    qc.h(q[4])
    qc.measure(q[4], c[0])
    return qc


def measure_single_horizon_chiral(u0, v0, n_periods, p_depol,
                                  fake_backend=None, p_coupling=1.0,
                                  n_repeats=10, shots=4096):
    sim = _simulator(p_depol, fake_backend)
    overlaps = []
    for _ in range(n_repeats):
        circ = build_snapshot_chiral(u0, v0, n_periods * T_CYCLE,
                                     p_coupling=p_coupling)
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
    ap.add_argument("--p-coupling", type=float, default=1.0)
    ap.add_argument("--fake-backend", default=None)
    args = ap.parse_args()

    periods = [2, 3, 5]
    if args.fake_backend:
        noise_levels = [None]
    else:
        noise_levels = [0.0, 0.001, 0.002, 0.005]
    families = make_families()

    tag = args.fake_backend or f"depol_sweep_pc{args.p_coupling}"
    print(f"Protocol 4S-Z3-three-P (Aer) | {tag} | periods={periods}")

    results = {}
    for n_p in periods:
        results[str(n_p)] = {}
        for p in noise_levels:
            print(f"\n[n_periods={n_p}, noise={args.fake_backend or p}]")
            cells = {}
            for fname, (u0, v0) in families.items():
                arr = measure_single_horizon_chiral(
                    u0, v0, n_p,
                    p if p is not None else 0.0,
                    fake_backend=args.fake_backend,
                    p_coupling=args.p_coupling,
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

            bg = pairs["beta_Z3_omega__vs__gamma_Z3_omega2"]
            status = "SEPARATED" if abs(bg["gap_over_sem"]) > 3 else "degenerate"
            print(f"  beta vs gamma:  gap={bg['gap']:+.4f}  sigma={bg['gap_over_sem']:+.2f}  [{status}]")

    if not args.fake_backend:
        print("\n" + "=" * 78)
        print("  beta vs gamma under chiral P gate")
        print("=" * 78)
        print(f"{'n_p':>4} {'p':>8} | {'beta':>10} {'gamma':>10} {'|b-g|/sem':>11} | status")
        four_class_cells = []
        for n_p in periods:
            for p in noise_levels:
                r = results[str(n_p)][str(p)]
                bm = r["cells"]["beta_Z3_omega"]["mean"]
                gm = r["cells"]["gamma_Z3_omega2"]["mean"]
                bg = abs(r["pairs"]["beta_Z3_omega__vs__gamma_Z3_omega2"]["gap_over_sem"])
                status = "SEPARATED" if bg > 3 else "degenerate"
                if bg > 3:
                    four_class_cells.append((n_p, p))
                print(f"{n_p:>4} {p:>8.4f} | {bm:>10.4f} {gm:>10.4f} {bg:>11.2f} | {status}")
        if four_class_cells:
            print(f"\nbeta-gamma SEPARATED in {len(four_class_cells)} cells.")
        else:
            print("\nbeta-gamma remains degenerate.")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "stack":     "qiskit_aer",
        "fake_backend": args.fake_backend,
        "p_coupling": args.p_coupling,
        "n_repeats": args.n_repeats,
        "shots":     args.shots,
        "periods":   periods,
        "results":   results,
    }
    out_tag = args.fake_backend or "depol"
    out = RESULTS_DIR / f"p4s_Z3_three_P_aer_{out_tag}_{datetime.now():%Y%m%dT%H%M%S}.json"
    out.write_text(json.dumps(payload, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
