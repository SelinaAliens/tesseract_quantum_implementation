#!/usr/bin/env python3
"""
Protocol 4S-Z3-three-P: add the chiral P gate to internal dynamics and
test whether beta and gamma separate.

Protocol 4S-Z3-three (real-only internal dynamics) collapsed {alpha, beta,
gamma} to two equivalence classes because the isoclinic rotations are
real-valued, making complex conjugation a symmetry and forcing
beta <-> gamma degeneracy.

This experiment adds the P gate -- the complex-phase generator

  P(phi) = Rz(+phi) ⊗ Rz(-phi)  =  diag(1, e^(-i*phi), e^(+i*phi), 1)

to the internal step. P is applied to the forward spinor u with phase
+phi; the inverse P is applied to v with phase -phi (P_inverse = P^dagger).
This explicitly breaks complex conjugation symmetry between u and v.

Predicted effect: beta and gamma should now separate into distinct
attractors. Four equivalence classes become visible:

  Class I      real-matched (alpha, A)
  Class IIa    complex-matched (beta)   <-- splits from II
  Class IIb    complex-matched (gamma)  <-- splits from II
  Class III    orthogonal (C)

Falsification: if beta and gamma remain indistinguishable, the P gate
alone is insufficient to break the Galois degeneracy. Something else in
the substrate structure is enforcing the Z2 collapse.

Five families, three short horizons (n=2,3,5), four noise levels. Same
statistical budget as Protocol 4S-Z3-three (10 repeats x 4096 shots).

Usage: python run_p4s_Z3_three_P_cirq.py
"""
import argparse
import json
import math
import sys
from datetime import datetime
from pathlib import Path
from itertools import combinations

import numpy as np
import cirq

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))
from run_p4s_Z3_cirq import state_prep_2q
from run_p4s_cirq import (
    cross_gate_4, horizontal_gate_4, diagonal_gate_4,
    internal_step_angles, inject_depolarize, overlap_from_swap, T_CYCLE,
)
from run_p4s_Z3_three_cirq import (
    basis_state, z3_eigenstate, make_families, OMEGA,
)

RESULTS_DIR = SCRIPT_DIR.parent / "results"


# ============================================================================
#  Chiral P gate
# ============================================================================
def p_gate_4(phi: float):
    """Chirality-breaking P gate on a 2-qubit (4-dim) spinor.

    P_forward(phi) = Rz(+phi) (x) Rz(-phi) = diag(1, e^{-i*phi}, e^{+i*phi}, 1)
    P_inverse(phi) = P_forward^dagger = diag(1, e^{+i*phi}, e^{-i*phi}, 1)

    These two differ by complex conjugation -> break complex-conjugation
    symmetry between u and v, which was what forced beta ~ gamma in
    Protocol 4S-Z3-three.
    """
    e_plus  = complex(math.cos(phi), math.sin(phi))
    e_minus = complex(math.cos(phi), -math.sin(phi))
    Pf = np.diag([1.0 + 0j, e_minus, e_plus, 1.0 + 0j]).astype(complex)
    Pi = np.diag([1.0 + 0j, e_plus,  e_minus, 1.0 + 0j]).astype(complex)
    return Pf, Pi


# ============================================================================
#  Chiral internal step (same three isoclinic rotations + P gate)
# ============================================================================
def internal_step_angles_chiral(step_index: int, coupling: float = 1.0,
                                p_coupling: float = 1.0):
    theta = (2 * math.pi / T_CYCLE) * coupling
    phi_p = (2 * math.pi / T_CYCLE) * p_coupling
    w = 2 * math.pi * step_index / T_CYCLE
    th_cross = theta * (1.0 + 0.3 * math.cos(w))
    th_horiz = theta * (1.0 + 0.3 * math.cos(w + 2 * math.pi / 3))
    th_diag  = theta * (1.0 + 0.3 * math.cos(w + 4 * math.pi / 3))
    # P-gate angle also triality-phased (matches ouroboros structure)
    phi_p_k = phi_p * (1.0 + 0.3 * math.cos(w))
    return th_cross, th_horiz, th_diag, phi_p_k


def build_snapshot_chiral(u0: np.ndarray, v0: np.ndarray, steps_so_far: int,
                          p_coupling: float = 1.0) -> cirq.Circuit:
    q = cirq.LineQubit.range(5)
    q_u, q_v, anc = (q[0], q[1]), (q[2], q[3]), q[4]
    c = cirq.Circuit()
    c.append(state_prep_2q(u0, "u").on(*q_u))
    c.append(state_prep_2q(v0, "v").on(*q_v))

    for k in range(steps_so_far):
        th_c, th_h, th_d, phi_p = internal_step_angles_chiral(
            k % T_CYCLE, p_coupling=p_coupling)
        Cf, Ci = cross_gate_4(th_c)
        c.append(cirq.MatrixGate(Cf, name="Cf").on(*q_u))
        c.append(cirq.MatrixGate(Ci, name="Ci").on(*q_v))
        Hf, Hi = horizontal_gate_4(th_h)
        c.append(cirq.MatrixGate(Hf, name="Hf").on(*q_u))
        c.append(cirq.MatrixGate(Hi, name="Hi").on(*q_v))
        Df, Di = diagonal_gate_4(th_d)
        c.append(cirq.MatrixGate(Df, name="Df").on(*q_u))
        c.append(cirq.MatrixGate(Di, name="Di").on(*q_v))
        # Chiral P gate - NEW
        Pf, Pi = p_gate_4(phi_p)
        c.append(cirq.MatrixGate(Pf, name="Pf").on(*q_u))
        c.append(cirq.MatrixGate(Pi, name="Pi").on(*q_v))

    c.append(cirq.H(anc))
    c.append(cirq.CSWAP(anc, q_u[0], q_v[0]))
    c.append(cirq.CSWAP(anc, q_u[1], q_v[1]))
    c.append(cirq.H(anc))
    c.append(cirq.measure(anc, key="anc"))
    return c


def measure_single_horizon_chiral(u0, v0, n_periods, p_depol,
                                  p_coupling=1.0, n_repeats=10, shots=4096):
    sim = cirq.DensityMatrixSimulator() if p_depol > 0 else cirq.Simulator()
    overlaps = []
    for _ in range(n_repeats):
        circ = build_snapshot_chiral(u0, v0, n_periods * T_CYCLE,
                                     p_coupling=p_coupling)
        circ = inject_depolarize(circ, p_depol)
        result = sim.run(circ, repetitions=shots)
        zeros = int(result.histogram(key="anc").get(0, 0))
        overlaps.append(overlap_from_swap(zeros, shots))
    return np.array(overlaps)


# ============================================================================
#  Main
# ============================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-repeats", type=int, default=10)
    ap.add_argument("--shots", type=int, default=4096)
    ap.add_argument("--p-coupling", type=float, default=1.0,
                    help="P-gate coupling strength; 0=off (reduces to Protocol 4S-Z3-three)")
    args = ap.parse_args()

    periods = [2, 3, 5]
    noise = [0.0, 0.001, 0.002, 0.005]
    families = make_families()

    print(f"Protocol 4S-Z3-three-P | 5 families | p_coupling={args.p_coupling}")
    print(f"periods={periods} noise={noise} n_repeats={args.n_repeats} shots={args.shots}")

    results = {}
    for n_p in periods:
        results[str(n_p)] = {}
        for p in noise:
            print(f"\n[n_periods={n_p}, p_depol={p:.4f}]")
            cells = {}
            for fname, (u0, v0) in families.items():
                arr = measure_single_horizon_chiral(
                    u0, v0, n_p, p,
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
            results[str(n_p)][str(p)] = {"cells": cells, "pairs": pairs}

            print("  beta vs gamma (was degenerate without P):")
            bg = pairs["beta_Z3_omega__vs__gamma_Z3_omega2"]
            status = "SEPARATED" if abs(bg["gap_over_sem"]) > 3 else "still degenerate"
            print(f"    gap={bg['gap']:+.4f}  sigma={bg['gap_over_sem']:+.2f}  [{status}]")

    print("\n" + "=" * 78)
    print("  beta vs gamma separation under chiral P gate")
    print("=" * 78)
    print(f"{'n_p':>4} {'p':>8} | {'beta mean':>10} {'gamma mean':>11} {'|b-g|/sem':>11} | status")
    print("-" * 78)
    four_class_cells = []
    for n_p in periods:
        for p in noise:
            r = results[str(n_p)][str(p)]
            bm = r["cells"]["beta_Z3_omega"]["mean"]
            gm = r["cells"]["gamma_Z3_omega2"]["mean"]
            bg = abs(r["pairs"]["beta_Z3_omega__vs__gamma_Z3_omega2"]["gap_over_sem"])
            status = "SEPARATED" if bg > 3 else "degenerate"
            if bg > 3:
                four_class_cells.append((n_p, p))
            print(f"{n_p:>4} {p:>8.4f} | {bm:>10.4f} {gm:>11.4f} {bg:>11.2f} | {status}")

    if four_class_cells:
        print(f"\nbeta-gamma SEPARATED in {len(four_class_cells)} cells: {four_class_cells}")
        print("Four-class memory demonstrated (alpha/A, beta, gamma, C).")
    else:
        print("\nbeta-gamma remains degenerate at all tested cells.")
        print("P gate alone is insufficient to break the Z2 Galois symmetry.")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "stack":     "cirq",
        "p_coupling": args.p_coupling,
        "n_repeats": args.n_repeats,
        "shots":     args.shots,
        "periods":   periods,
        "noise":     noise,
        "results":   results,
        "four_class_cells": four_class_cells,
    }
    out = RESULTS_DIR / f"p4s_Z3_three_P_cirq_{datetime.now():%Y%m%dT%H%M%S}.json"
    out.write_text(json.dumps(payload, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
