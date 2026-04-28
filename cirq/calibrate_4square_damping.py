#!/usr/bin/env python3
"""
Calibrate the 4-square depolarization damping coefficient at n=1.

The memory-capacity experiment was run at n=3 (peak distinguishability)
under IDEAL unitary dynamics. Willow-realistic noise (p_depol = 0.005)
collapses the 2-merkabit directional gap at n=3 to ~0, so the practical
hardware operating point must be n=1.

This calibration measures how 4-square bond values decay under depolarizing
noise at n=1, for a small set of representative patterns. The empirical
damping coefficient is then applied to the 81-pattern ideal fingerprints
to produce a hardware-realistic N(D) capacity curve.

Protocol:
  - 3 patterns: M1 (alpha,beta,gamma,alpha), M5 (alpha,alpha,alpha,alpha),
    M6 (beta,beta,beta,beta)
  - All 4 bonds per pattern
  - p_depol in {0, 0.005}  (at n=1 only)
  - 512 Monte-Carlo trajectory shots per (pattern, bond, p)

Budget: ~12 cells * 512 shots = 6,144 trajectories at ~0.9 shots/sec
~= 2 hours.
"""
import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import cirq

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))
from run_p4s_memory_persistence_cirq import (
    build_square_dynamics, _append_swap_test, BOND_PAIRS, states_for_labels,
)
from run_p4s_cirq import overlap_from_swap, inject_depolarize

RESULTS_DIR = SCRIPT_DIR.parent / "results"


PATTERNS = {
    "M1_abga": ["alpha", "beta",  "gamma", "alpha"],
    "M5_aaaa": ["alpha", "alpha", "alpha", "alpha"],
    "M6_bbbb": ["beta",  "beta",  "beta",  "beta"],
}


def measure_bond(states, bond_name, n_periods, J, p_depol, shots):
    qc, regs, anc = build_square_dynamics(states, n_periods, J)
    pair = next(p for p in BOND_PAIRS if p[0] == bond_name)
    _append_swap_test(qc, regs[pair[1]], regs[pair[2]], anc)
    if p_depol > 0:
        qc = inject_depolarize(qc, p_depol)
    sim = cirq.Simulator()
    res = sim.run(qc, repetitions=shots)
    zeros = int(res.histogram(key="anc").get(0, 0))
    return overlap_from_swap(zeros, shots)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots",     type=int,   default=512)
    ap.add_argument("--n-periods", type=int,   default=1)
    ap.add_argument("--J",         type=float, default=0.1)
    ap.add_argument("--p-depol",   type=float, default=0.005)
    args = ap.parse_args()

    bonds = [b[0] for b in BOND_PAIRS]
    print(f"4-square damping calibration")
    print(f"  n={args.n_periods}, J={args.J}, shots={args.shots}")
    print(f"  p in [0, {args.p_depol}]")
    print(f"  {len(PATTERNS)} patterns x {len(bonds)} bonds x 2 noise levels "
          f"= {len(PATTERNS)*len(bonds)*2} cells\n")

    rows = []
    for name, labels in PATTERNS.items():
        states = states_for_labels(labels)
        for bond in bonds:
            for p in [0.0, args.p_depol]:
                t0 = time.time()
                b = measure_bond(states, bond,
                                 n_periods=args.n_periods, J=args.J,
                                 p_depol=p, shots=args.shots)
                dt = time.time() - t0
                rows.append({"pattern": name, "bond": bond,
                             "p_depol": p, "bond_val": b, "dt": dt})
                print(f"  {name} {bond} p={p:.4f}  bond={b:.4f}  "
                      f"({dt:.1f}s)")

    # Compute empirical damping
    print("\nDamping factor (bond(p) - 0.5) / (bond(0) - 0.5):")
    print(f"{'pattern':>10} {'bond':>8}  {'bond(0)':>8} {'bond(p)':>8}  "
          f"{'factor':>8}")
    factors = []
    for name in PATTERNS:
        for bond in bonds:
            b0 = next(r["bond_val"] for r in rows
                      if r["pattern"] == name and r["bond"] == bond
                      and r["p_depol"] == 0.0)
            bp = next(r["bond_val"] for r in rows
                      if r["pattern"] == name and r["bond"] == bond
                      and r["p_depol"] == args.p_depol)
            denom = b0 - 0.5
            if abs(denom) > 0.05:  # only meaningful when ideal is far from 0.5
                factor = (bp - 0.5) / denom
                factors.append(factor)
                print(f"  {name:>10} {bond:>8}  {b0:>8.4f} {bp:>8.4f}  "
                      f"{factor:>8.4f}")
            else:
                print(f"  {name:>10} {bond:>8}  {b0:>8.4f} {bp:>8.4f}  "
                      f"(ideal too close to 0.5)")

    if factors:
        factors = np.array(factors)
        print(f"\nDamping factor (distance from 0.5 fixed point):")
        print(f"  mean  = {factors.mean():.4f}")
        print(f"  std   = {factors.std():.4f}")
        print(f"  median= {np.median(factors):.4f}")
        alpha_eff = -np.log(abs(factors.mean())) / (args.n_periods * args.p_depol)
        print(f"  alpha_eff (per n*p) = {alpha_eff:.1f}")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp":  datetime.now().isoformat(timespec="seconds"),
        "stack":      "cirq",
        "n_periods":  args.n_periods,
        "J":          args.J,
        "shots":      args.shots,
        "p_depol":    args.p_depol,
        "rows":       rows,
        "damping_factor_mean":   float(np.mean(factors)) if factors.size else None,
        "damping_factor_std":    float(np.std(factors))  if factors.size else None,
    }
    out = RESULTS_DIR / f"calibrate_4square_damping_{datetime.now():%Y%m%dT%H%M%S}.json"
    out.write_text(json.dumps(payload, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
