#!/usr/bin/env python3
"""
Protocol 4S-Tunnel (Qiskit Aer) - cross-stack check.

Cross-check for cirq/run_p4s_tunnel_cirq.py on the IBM Qiskit stack.
Same six family pairs, same three overlap measurements (local_A,
local_B, tunnel), same J = 0.1 tunnel strength.

Usage: python run_p4s_tunnel_aer.py
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
from qiskit.circuit.library import UnitaryGate, iSwapGate
from qiskit_aer import AerSimulator

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))
from run_p4s_aer import (
    cross_gate_4, horizontal_gate_4, diagonal_gate_4,
    overlap_from_swap, zeros_from_counts,
    _simulator, _transpile, T_CYCLE,
)
from run_p4s_Z3_three_P_aer import p_gate_4, internal_step_angles_chiral
from run_p4s_Z3_three_aer import basis_state, z3_eigenstate

RESULTS_DIR = SCRIPT_DIR.parent / "results"


# ============================================================================
#  Tunnel step: iSWAP^J between (u_A[i], v_B[i]) for i = 0, 1
# ============================================================================
def tunnel_step_qiskit(qc: QuantumCircuit, q_uA, q_vB, J: float):
    if J == 0.0:
        return
    # Parameterized iSWAP = iSWAP^J via matrix decomposition
    # iSWAP^J = exp(i J pi/2 (XX + YY)/2). Use the XX+YY interaction Hamiltonian.
    theta = J * math.pi / 2
    c, s = math.cos(theta), math.sin(theta)
    # iSWAP^J matrix (2-qubit):
    iswap_j = np.array([
        [1, 0,          0,          0],
        [0, c,          1j * s,     0],
        [0, 1j * s,     c,          0],
        [0, 0,          0,          1],
    ], dtype=complex)
    for i in range(2):
        qc.append(UnitaryGate(iswap_j, label=f"iSWAP^{J}"), [q_uA[i], q_vB[i]])


def _append_internal_chiral(qc, q_u, q_v, step_idx, p_coupling=1.0):
    th_c, th_h, th_d, phi_p = internal_step_angles_chiral(
        step_idx % T_CYCLE, p_coupling=p_coupling)
    Cf, Ci = cross_gate_4(th_c)
    qc.append(UnitaryGate(Cf, label="Cf"), list(q_u))
    qc.append(UnitaryGate(Ci, label="Ci"), list(q_v))
    Hf, Hi = horizontal_gate_4(th_h)
    qc.append(UnitaryGate(Hf, label="Hf"), list(q_u))
    qc.append(UnitaryGate(Hi, label="Hi"), list(q_v))
    Df, Di = diagonal_gate_4(th_d)
    qc.append(UnitaryGate(Df, label="Df"), list(q_u))
    qc.append(UnitaryGate(Di, label="Di"), list(q_v))
    Pf, Pi = p_gate_4(phi_p)
    qc.append(UnitaryGate(Pf, label="Pf"), list(q_u))
    qc.append(UnitaryGate(Pi, label="Pi"), list(q_v))


def build_tunnel_snapshot(u0_A, v0_A, u0_B, v0_B, steps_so_far: int,
                          which: str, J: float, p_coupling: float = 1.0) -> QuantumCircuit:
    """Build the 9-qubit circuit with dynamics then SWAP test of `which`."""
    q = QuantumRegister(9, "q")
    c = ClassicalRegister(1, "c")
    qc = QuantumCircuit(q, c)
    q_uA = [q[0], q[1]]; q_vA = [q[2], q[3]]
    q_uB = [q[4], q[5]]; q_vB = [q[6], q[7]]
    anc = q[8]
    qc.initialize(u0_A, q_uA)
    qc.initialize(v0_A, q_vA)
    qc.initialize(u0_B, q_uB)
    qc.initialize(v0_B, q_vB)

    for k in range(steps_so_far):
        _append_internal_chiral(qc, q_uA, q_vA, k, p_coupling=p_coupling)
        _append_internal_chiral(qc, q_uB, q_vB, k, p_coupling=p_coupling)
        tunnel_step_qiskit(qc, q_uA, q_vB, J)

    if which == "local_A":
        left, right = q_uA, q_vA
    elif which == "local_B":
        left, right = q_uB, q_vB
    elif which == "tunnel":
        left, right = q_uA, q_vB
    else:
        raise ValueError(f"unknown which: {which}")

    qc.h(anc)
    qc.cswap(anc, left[0], right[0])
    qc.cswap(anc, left[1], right[1])
    qc.h(anc)
    qc.measure(anc, c[0])
    return qc


def measure_overlap(u0_A, v0_A, u0_B, v0_B, which: str, n_periods: int,
                    J: float, p_depol: float, p_coupling: float = 1.0,
                    shots: int = 4096, fake_backend=None) -> float:
    qc = build_tunnel_snapshot(u0_A, v0_A, u0_B, v0_B,
                               n_periods * T_CYCLE,
                               which=which, J=J, p_coupling=p_coupling)
    sim = _simulator(p_depol, fake_backend)
    tqc = _transpile(qc, sim, use_backend_calibration=(fake_backend is not None))
    result = sim.run(tqc, shots=shots).result()
    counts = result.get_counts()
    return overlap_from_swap(zeros_from_counts(counts), shots)


def make_pair_families():
    b0 = basis_state(0)
    alpha = z3_eigenstate(0)
    beta  = z3_eigenstate(1)
    gamma = z3_eigenstate(2)
    return {
        "AA_matched":       (b0,    b0,    b0,    b0),
        "aa_Z3_1_both":     (alpha, alpha, alpha, alpha),
        "bb_Z3_omega_both": (beta,  beta,  beta,  beta),
        "gg_Z3_w2_both":    (gamma, gamma, gamma, gamma),
        "bg_cross_fwd":     (beta,  beta,  gamma, gamma),
        "gb_cross_rev":     (gamma, gamma, beta,  beta),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-repeats", type=int, default=6)
    ap.add_argument("--shots",     type=int, default=4096)
    ap.add_argument("--n-periods", type=int, default=2)
    ap.add_argument("--J",         type=float, default=0.1)
    ap.add_argument("--fake-backend", default=None)
    ap.add_argument("--p-coupling", type=float, default=1.0)
    args = ap.parse_args()

    noise = [None] if args.fake_backend else [0.0, 0.005]
    families = make_pair_families()
    overlap_types = ["local_A", "local_B", "tunnel"]

    tag = args.fake_backend or "depol"
    print(f"Protocol 4S-Tunnel (Aer) | {tag} | {len(families)} pairs | J={args.J} "
          f"n_periods={args.n_periods} n_repeats={args.n_repeats}")

    results = {}
    for p in noise:
        label = args.fake_backend or f"p={p:.4f}"
        print(f"\n=== {label} ===")
        results[str(p)] = {}
        for fname, (uA, vA, uB, vB) in families.items():
            row = {}
            for which in overlap_types:
                vals = []
                for _ in range(args.n_repeats):
                    vals.append(measure_overlap(
                        uA, vA, uB, vB, which,
                        n_periods=args.n_periods, J=args.J,
                        p_depol=p if p is not None else 0.0,
                        p_coupling=args.p_coupling,
                        shots=args.shots,
                        fake_backend=args.fake_backend))
                arr = np.array(vals)
                row[which] = {
                    "values": arr.tolist(),
                    "mean":   float(np.mean(arr)),
                    "std":    float(np.std(arr, ddof=1)),
                    "sem":    float(np.std(arr, ddof=1) / math.sqrt(args.n_repeats)),
                }
            results[str(p)][fname] = row
            print(f"  {fname:22s}  "
                  f"local_A={row['local_A']['mean']:.3f}±{row['local_A']['sem']:.3f}  "
                  f"local_B={row['local_B']['mean']:.3f}±{row['local_B']['sem']:.3f}  "
                  f"tunnel ={row['tunnel' ]['mean']:.3f}±{row['tunnel' ]['sem']:.3f}")

    print("\n" + "=" * 78)
    print("  DIRECTIONAL TUNNEL: (beta, gamma) vs (gamma, beta)")
    print("=" * 78)
    print(f"{'noise':>16} | {'bg tunnel':>12} {'gb tunnel':>12} {'gap':>8} {'sigma':>7}")
    for p in noise:
        bg = results[str(p)]["bg_cross_fwd"]["tunnel"]
        gb = results[str(p)]["gb_cross_rev"]["tunnel"]
        gap = bg["mean"] - gb["mean"]
        sem_tot = math.sqrt(bg["sem"] ** 2 + gb["sem"] ** 2)
        sig = gap / max(sem_tot, 1e-9)
        status = "DIRECTIONAL" if abs(sig) > 3 else "symmetric"
        label = args.fake_backend or f"{p:.4f}"
        print(f"{label:>16} | {bg['mean']:>12.4f} {gb['mean']:>12.4f} "
              f"{gap:>+8.4f} {sig:>+7.2f}  [{status}]")

    print("\n  Pairs separable @ 3 sigma, by observable")
    for p in noise:
        label = args.fake_backend or f"p={p}"
        print(f"\n  {label}")
        for which in overlap_types:
            sep = 0; total = 0
            for a, b in combinations(families.keys(), 2):
                ra = results[str(p)][a][which]; rb = results[str(p)][b][which]
                gap = abs(ra["mean"] - rb["mean"])
                sem_tot = math.sqrt(ra["sem"] ** 2 + rb["sem"] ** 2)
                if gap / max(sem_tot, 1e-9) > 3: sep += 1
                total += 1
            print(f"    {which:8s}  {sep}/{total}")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp":    datetime.now().isoformat(timespec="seconds"),
        "stack":        "qiskit_aer",
        "fake_backend": args.fake_backend,
        "n_repeats":    args.n_repeats,
        "shots":        args.shots,
        "n_periods":    args.n_periods,
        "J":            args.J,
        "p_coupling":   args.p_coupling,
        "results":      results,
    }
    out_tag = args.fake_backend or "depol"
    out = RESULTS_DIR / f"p4s_tunnel_aer_{out_tag}_{datetime.now():%Y%m%dT%H%M%S}.json"
    out.write_text(json.dumps(payload, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
