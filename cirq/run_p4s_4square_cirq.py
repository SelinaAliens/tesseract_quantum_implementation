#!/usr/bin/env python3
"""
Protocol 4S-4Square: four tesseract merkabits on a plaquette, coupled by
four cross-chiral tunnels around the perimeter.

Topology (closed loop):

     A --- tunnel_AB ---> B
     ^                    |
     |                    v
  tunnel_DA            tunnel_BC
     |                    |
     D <--- tunnel_CD --- C

Each tunnel is the cross-chiral iSWAP^J between the forward spinor of the
upstream merkabit and the inverse spinor of the downstream:
  tunnel_AB : u_A <-> v_B
  tunnel_BC : u_B <-> v_C
  tunnel_CD : u_C <-> v_D
  tunnel_DA : u_D <-> v_A

The loop direction A -> B -> C -> D -> A is oriented. Under this oriented
structure, the Z_3 label sum (a + b + c + d) mod 3 defines a DISCRETE
HOLONOMY PHASE around the plaquette:

  loop phase = omega^((a+b+c+d) mod 3)    where a,b,c,d in {0,1,2} for
                                          Z_3 eigenstates {alpha, beta, gamma}

This phase is an analog of a Wilson loop / Berry phase for a Z_3 gauge
structure on the Eisenstein lattice. The experiment tests whether the
tunnel observables are SENSITIVE to this holonomy phase.

## Hypothesis

If merkabit dynamics are path-independent (no Z_3 holonomy), families that
differ only in Z_3 loop phase should give identical observables.

If merkabit dynamics carry Z_3 holonomy, families in different phase
classes {1, omega, omega^2} should cluster into three distinct observable
groups.

## Qubit layout (17 qubits)

  A: q[0,1]=u_A,  q[2,3]=v_A
  B: q[4,5]=u_B,  q[6,7]=v_B
  C: q[8,9]=u_C,  q[10,11]=v_C
  D: q[12,13]=u_D, q[14,15]=v_D
  anc: q[16]  (SWAP-test ancilla; reused across observables)

## Observables (10)

  local_A, local_B, local_C, local_D       (four self-coherences)
  tunnel_AB, tunnel_BC, tunnel_CD, tunnel_DA (four perimeter tunnels)
  tunnel_AC, tunnel_BD                      (two diagonals)

Each observable requires a separate circuit (SWAP test destroys state).

## Initial state families

Six families covering three Z_3 loop-phase classes:

  Phase 1 (trivial):       AAAA, alpha x 4, beta-gamma-beta-gamma
  Phase omega:             beta x 4
  Phase omega^2:           gamma x 4, beta-beta-alpha-alpha, beta-beta-beta-gamma

Usage:
  python run_p4s_4square_cirq.py --sim-only --phase ideal
  python run_p4s_4square_cirq.py --sim-only --phase noisy --p-depol 0.005
"""
import argparse
import json
import math
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import cirq

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))
from run_p4s_cirq import (
    cross_gate_4, horizontal_gate_4, diagonal_gate_4,
    inject_depolarize, overlap_from_swap, T_CYCLE,
)
from run_p4s_Z3_three_P_cirq import (
    p_gate_4, internal_step_angles_chiral,
)
from run_p4s_Z3_three_cirq import (
    basis_state, z3_eigenstate, OMEGA,
)
from run_p4s_Z3_cirq import state_prep_2q

RESULTS_DIR = SCRIPT_DIR.parent / "results"


# ============================================================================
#  Dynamics builder: 4 merkabits + 4 perimeter tunnels per internal step
# ============================================================================
def _append_internal_chiral(qc, q_u, q_v, step_idx, p_coupling=1.0):
    th_c, th_h, th_d, phi_p = internal_step_angles_chiral(
        step_idx % T_CYCLE, p_coupling=p_coupling)
    Cf, Ci = cross_gate_4(th_c)
    qc.append(cirq.MatrixGate(Cf, name="Cf").on(*q_u))
    qc.append(cirq.MatrixGate(Ci, name="Ci").on(*q_v))
    Hf, Hi = horizontal_gate_4(th_h)
    qc.append(cirq.MatrixGate(Hf, name="Hf").on(*q_u))
    qc.append(cirq.MatrixGate(Hi, name="Hi").on(*q_v))
    Df, Di = diagonal_gate_4(th_d)
    qc.append(cirq.MatrixGate(Df, name="Df").on(*q_u))
    qc.append(cirq.MatrixGate(Di, name="Di").on(*q_v))
    Pf, Pi = p_gate_4(phi_p)
    qc.append(cirq.MatrixGate(Pf, name="Pf").on(*q_u))
    qc.append(cirq.MatrixGate(Pi, name="Pi").on(*q_v))


def _tunnel_step(qc, q_u_from, q_v_to, J):
    if J == 0.0: return
    for i in range(2):
        qc.append((cirq.ISWAP ** J).on(q_u_from[i], q_v_to[i]))


def build_square_dynamics(states, n_periods, J=0.1, p_coupling=1.0):
    """states = (u_A, v_A, u_B, v_B, u_C, v_C, u_D, v_D) — eight 4-vectors.
    Returns the 17-qubit Circuit after state prep and n_periods x 12 internal
    steps (each step: 4 internal chiral + 4 perimeter tunnels), plus the
    qubit handles needed for SWAP-test variants."""
    q = cirq.LineQubit.range(17)
    regs = {
        "uA": (q[0],  q[1]),  "vA": (q[2],  q[3]),
        "uB": (q[4],  q[5]),  "vB": (q[6],  q[7]),
        "uC": (q[8],  q[9]),  "vC": (q[10], q[11]),
        "uD": (q[12], q[13]), "vD": (q[14], q[15]),
    }
    anc = q[16]
    names = ["uA", "vA", "uB", "vB", "uC", "vC", "uD", "vD"]

    qc = cirq.Circuit()
    for nm, st in zip(names, states):
        qc.append(state_prep_2q(st, nm).on(*regs[nm]))

    steps = n_periods * T_CYCLE
    for k in range(steps):
        # internal chiral on each merkabit
        _append_internal_chiral(qc, regs["uA"], regs["vA"], k, p_coupling)
        _append_internal_chiral(qc, regs["uB"], regs["vB"], k, p_coupling)
        _append_internal_chiral(qc, regs["uC"], regs["vC"], k, p_coupling)
        _append_internal_chiral(qc, regs["uD"], regs["vD"], k, p_coupling)
        # perimeter tunnels, cross-chiral u_X -> v_Y
        _tunnel_step(qc, regs["uA"], regs["vB"], J)
        _tunnel_step(qc, regs["uB"], regs["vC"], J)
        _tunnel_step(qc, regs["uC"], regs["vD"], J)
        _tunnel_step(qc, regs["uD"], regs["vA"], J)

    return qc, regs, anc


def _append_swap_test(qc, left_reg, right_reg, anc):
    qc.append(cirq.H(anc))
    qc.append(cirq.CSWAP(anc, left_reg[0], right_reg[0]))
    qc.append(cirq.CSWAP(anc, left_reg[1], right_reg[1]))
    qc.append(cirq.H(anc))
    qc.append(cirq.measure(anc, key="anc"))


OBSERVABLE_PAIRS = [
    # (name, left register, right register)
    ("local_A",   "uA", "vA"),
    ("local_B",   "uB", "vB"),
    ("local_C",   "uC", "vC"),
    ("local_D",   "uD", "vD"),
    ("tunnel_AB", "uA", "vB"),
    ("tunnel_BC", "uB", "vC"),
    ("tunnel_CD", "uC", "vD"),
    ("tunnel_DA", "uD", "vA"),
    ("tunnel_AC", "uA", "vC"),  # diagonal - should be path-independent if
                                  # info propagates through B or D
    ("tunnel_BD", "uB", "vD"),  # other diagonal
]


def measure_observable(states, which, n_periods=1, J=0.1, p_depol=0.0,
                       shots=4096):
    qc, regs, anc = build_square_dynamics(states, n_periods, J)
    pair = next(p for p in OBSERVABLE_PAIRS if p[0] == which)
    _append_swap_test(qc, regs[pair[1]], regs[pair[2]], anc)

    if p_depol > 0:
        qc = inject_depolarize(qc, p_depol)
        sim = cirq.DensityMatrixSimulator()
    else:
        sim = cirq.Simulator()
    res = sim.run(qc, repetitions=shots)
    zeros = int(res.histogram(key="anc").get(0, 0))
    return overlap_from_swap(zeros, shots)


# ============================================================================
#  Families
# ============================================================================
def family_states(family_name):
    alpha = z3_eigenstate(0); beta = z3_eigenstate(1); gamma = z3_eigenstate(2)
    b0 = basis_state(0)

    FAMILIES = {
        "AAAA":       (b0,    b0,    b0,    b0,    b0,    b0,    b0,    b0),
        "aaaa_p1":    (alpha, alpha, alpha, alpha, alpha, alpha, alpha, alpha),
        "bbbb_pw":    (beta,  beta,  beta,  beta,  beta,  beta,  beta,  beta),
        "gggg_pw2":   (gamma, gamma, gamma, gamma, gamma, gamma, gamma, gamma),
        "bgbg_p1":    (beta,  beta,  gamma, gamma, beta,  beta,  gamma, gamma),
        "bbgg_p1":    (beta,  beta,  beta,  beta,  gamma, gamma, gamma, gamma),
        "bbaa_pw2":   (beta,  beta,  beta,  beta,  alpha, alpha, alpha, alpha),
        "bbbg_pw2":   (beta,  beta,  beta,  beta,  beta,  beta,  gamma, gamma),
    }
    return FAMILIES[family_name]


# Z_3 loop-phase label per family.
# Each site contributes its Z_3 eigenvalue (alpha=0, beta=1, gamma=2)
# with sum taken mod 3. Label 0 -> phase 1; 1 -> omega; 2 -> omega^2.
FAMILY_LOOP_PHASE = {
    "AAAA":      None,       # not a Z_3 eigenstate; different class
    "aaaa_p1":   0,          # 0+0+0+0 = 0
    "bbbb_pw":   1,          # 1+1+1+1 = 4 mod 3 = 1
    "gggg_pw2":  2,          # 2+2+2+2 = 8 mod 3 = 2
    "bgbg_p1":   0,          # 1+2+1+2 = 6 mod 3 = 0
    "bbgg_p1":   0,          # 1+1+2+2 = 6 mod 3 = 0
    "bbaa_pw2":  2,          # 1+1+0+0 = 2
    "bbbg_pw2":  2,          # 1+1+1+2 = 5 mod 3 = 2
}


# ============================================================================
#  Main
# ============================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-repeats", type=int,   default=6)
    ap.add_argument("--shots",     type=int,   default=4096)
    ap.add_argument("--n-periods", type=int,   default=1)
    ap.add_argument("--J",         type=float, default=0.1)
    ap.add_argument("--p-depol",   type=float, default=0.0)
    args = ap.parse_args()

    families = list(FAMILY_LOOP_PHASE.keys())
    observables = [p[0] for p in OBSERVABLE_PAIRS]

    print(f"Protocol 4S-4Square | n={args.n_periods} J={args.J} p={args.p_depol}")
    print(f"families = {len(families)}   observables = {len(observables)}   "
          f"n_repeats = {args.n_repeats}   shots = {args.shots}")
    total = len(families) * len(observables) * args.n_repeats
    print(f"Total circuit runs: {total}\n")

    results = {}
    for fname in families:
        states = family_states(fname)
        initial_self_overlaps = [abs(np.vdot(states[2*i], states[2*i+1])) for i in range(4)]
        row = {"loop_phase": FAMILY_LOOP_PHASE[fname], "observables": {}}
        for which in observables:
            vals = []
            for _ in range(args.n_repeats):
                vals.append(measure_observable(
                    states, which,
                    n_periods=args.n_periods, J=args.J,
                    p_depol=args.p_depol, shots=args.shots))
            arr = np.array(vals)
            row["observables"][which] = {
                "values": arr.tolist(),
                "mean":   float(np.mean(arr)),
                "std":    float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0,
                "sem":    float(np.std(arr, ddof=1) / math.sqrt(args.n_repeats)) if len(arr) > 1 else 0.0,
            }
        row["initial_self_overlaps"] = initial_self_overlaps
        results[fname] = row
        phase_txt = {None: "-", 0: "1", 1: "ω", 2: "ω²"}[row["loop_phase"]]
        print(f"  [{fname:12s} Z₃ loop phase {phase_txt}]")
        for which in observables:
            m = row["observables"][which]["mean"]
            s = row["observables"][which]["sem"]
            print(f"    {which:12s}  {m:.4f} ± {s:.4f}")

    # -----------------------------------------------------------------
    # Z_3 loop-phase clustering test
    # -----------------------------------------------------------------
    print("\n" + "=" * 78)
    print("  Z_3 LOOP-PHASE CLUSTERING TEST")
    print("=" * 78)
    print("Per observable: compute the between-group / within-group variance")
    print("ratio across the three Z_3 phase classes. Large ratio (> ~3) means")
    print("the observable is sensitive to the plaquette Z_3 holonomy.\n")

    phase_groups = {0: [], 1: [], 2: []}
    for fname, row in results.items():
        if row["loop_phase"] is not None:
            phase_groups[row["loop_phase"]].append(fname)

    print(f"{'observable':>12} | {'phase 1':>10} {'phase ω':>10} {'phase ω²':>10} | {'ratio':>6}")
    print("-" * 70)
    holonomy_scores = {}
    for which in observables:
        means_per_phase = {}
        for phase, fams in phase_groups.items():
            vals = [results[f]["observables"][which]["mean"] for f in fams]
            means_per_phase[phase] = (float(np.mean(vals)) if vals else 0.0,
                                      float(np.std(vals)) if len(vals) > 1 else 0.0)
        between = np.std([means_per_phase[p][0] for p in [0, 1, 2]])
        within  = np.mean([means_per_phase[p][1] for p in [0, 1, 2]
                           if means_per_phase[p][1] > 0]) or 1e-9
        ratio = between / within
        holonomy_scores[which] = ratio
        p1 = f"{means_per_phase[0][0]:.3f}"
        po = f"{means_per_phase[1][0]:.3f}"
        po2 = f"{means_per_phase[2][0]:.3f}"
        print(f"{which:>12} | {p1:>10} {po:>10} {po2:>10} | {ratio:>6.2f}")

    print("\nObservables with largest Z_3 loop-phase sensitivity:")
    top = sorted(holonomy_scores.items(), key=lambda x: -x[1])[:5]
    for obs, score in top:
        print(f"  {obs:12s}  holonomy ratio = {score:.2f}")

    # -----------------------------------------------------------------
    # Save
    # -----------------------------------------------------------------
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp":  datetime.now().isoformat(timespec="seconds"),
        "stack":      "cirq",
        "topology":   "4-square with cross-chiral perimeter tunnels",
        "n_periods":  args.n_periods,
        "J":          args.J,
        "p_depol":    args.p_depol,
        "n_repeats":  args.n_repeats,
        "shots":      args.shots,
        "family_loop_phase": FAMILY_LOOP_PHASE,
        "results":    results,
        "holonomy_scores": holonomy_scores,
    }
    tag = "ideal" if args.p_depol == 0.0 else f"p{args.p_depol}"
    out = RESULTS_DIR / f"p4s_4square_cirq_{tag}_{datetime.now():%Y%m%dT%H%M%S}.json"
    out.write_text(json.dumps(payload, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
