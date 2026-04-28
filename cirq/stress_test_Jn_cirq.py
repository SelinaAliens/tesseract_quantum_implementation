#!/usr/bin/env python3
"""
Protocol 4S-Tunnel stress test: J and n dependence of the directional signal.

The tunnel result was established at J = 0.1, n = 2 only. Before writing
the paper we stress-test along these two axes:

  --mode J:  sweep tunnel strength J in {0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 0.7, 1.0}
             at fixed n = 2 and p_depol = 0.005.
  --mode n:  sweep horizon n in {1, 2, 3, 4, 5, 7, 10} at fixed J = 0.1
             and p_depol = 0.005.

Both: measure the directional tunnel gap |<u_A|v_B>|(beta, gamma) minus
|<u_A|v_B>|(gamma, beta), the quantity the paper's central claim
depends on. Only this observable -- skip local_A / local_B and all
other families for speed.

Statistical budget per cell: 6 repeats x 4,096 shots (same as full
tunnel experiment).

Usage:
  python stress_test_Jn_cirq.py --mode J
  python stress_test_Jn_cirq.py --mode n
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
from run_p4s_tunnel_cirq import (
    build_dynamics, append_swap_test, measure_overlap,
)
from run_p4s_Z3_three_cirq import z3_eigenstate

RESULTS_DIR = SCRIPT_DIR.parent / "results"


def run_directional_cell(J: float, n_periods: int, p_depol: float,
                         n_repeats: int = 6, shots: int = 4096):
    """Measure the (β, γ) vs (γ, β) tunnel gap at one (J, n, p) point."""
    beta  = z3_eigenstate(1)
    gamma = z3_eigenstate(2)

    bg_vals, gb_vals = [], []
    for _ in range(n_repeats):
        bg_vals.append(measure_overlap(
            beta, beta, gamma, gamma,
            which="tunnel", n_periods=n_periods,
            J=J, p_depol=p_depol, shots=shots,
        ))
        gb_vals.append(measure_overlap(
            gamma, gamma, beta, beta,
            which="tunnel", n_periods=n_periods,
            J=J, p_depol=p_depol, shots=shots,
        ))
    bg = np.array(bg_vals); gb = np.array(gb_vals)
    bg_mean = float(np.mean(bg)); gb_mean = float(np.mean(gb))
    bg_sem  = float(np.std(bg, ddof=1) / math.sqrt(n_repeats))
    gb_sem  = float(np.std(gb, ddof=1) / math.sqrt(n_repeats))
    gap     = bg_mean - gb_mean
    sem_tot = math.sqrt(bg_sem ** 2 + gb_sem ** 2)
    return {
        "bg_mean": bg_mean, "bg_sem": bg_sem,
        "gb_mean": gb_mean, "gb_sem": gb_sem,
        "gap":     gap,
        "sem_tot": sem_tot,
        "sigma":   gap / max(sem_tot, 1e-9),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["J", "n"], required=True)
    ap.add_argument("--n-repeats", type=int, default=6)
    ap.add_argument("--shots",     type=int, default=4096)
    ap.add_argument("--p-depol",   type=float, default=0.005)
    args = ap.parse_args()

    if args.mode == "J":
        J_values = [0.0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 0.7, 1.0]
        n_fixed = 2
        print(f"# J sweep | n_periods={n_fixed}, p_depol={args.p_depol}, "
              f"n_repeats={args.n_repeats}")
        print(f"{'J':>6} | {'bg tunnel':>12} {'gb tunnel':>12} {'gap':>8} {'sigma':>8}")
        print("-" * 60)
        results = {}
        for J in J_values:
            r = run_directional_cell(J, n_fixed, args.p_depol,
                                     args.n_repeats, args.shots)
            results[f"J={J}"] = r
            print(f"{J:>6.3f} | {r['bg_mean']:>12.4f} {r['gb_mean']:>12.4f} "
                  f"{r['gap']:>+8.4f} {r['sigma']:>+8.2f}")
        fixed_param = f"n={n_fixed}"
    else:
        n_values = [1, 2, 3, 4, 5, 7, 10]
        J_fixed = 0.1
        print(f"# n sweep | J={J_fixed}, p_depol={args.p_depol}, "
              f"n_repeats={args.n_repeats}")
        print(f"{'n':>4} | {'bg tunnel':>12} {'gb tunnel':>12} {'gap':>8} {'sigma':>8}")
        print("-" * 60)
        results = {}
        for n_p in n_values:
            r = run_directional_cell(J_fixed, n_p, args.p_depol,
                                     args.n_repeats, args.shots)
            results[f"n={n_p}"] = r
            print(f"{n_p:>4d} | {r['bg_mean']:>12.4f} {r['gb_mean']:>12.4f} "
                  f"{r['gap']:>+8.4f} {r['sigma']:>+8.2f}")
        fixed_param = f"J={J_fixed}"

    # summary: does the signal survive at |sigma| > 3 across most cells?
    surviving = sum(1 for r in results.values() if abs(r["sigma"]) > 3)
    total = len(results)
    print(f"\n{surviving}/{total} cells have |sigma| > 3 "
          f"(directional signal detectable)")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "stack":     "cirq",
        "mode":      args.mode,
        "fixed":     fixed_param,
        "p_depol":   args.p_depol,
        "n_repeats": args.n_repeats,
        "shots":     args.shots,
        "results":   results,
        "surviving": f"{surviving}/{total}",
    }
    out = RESULTS_DIR / f"stress_{args.mode}_cirq_{datetime.now():%Y%m%dT%H%M%S}.json"
    out.write_text(json.dumps(payload, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
