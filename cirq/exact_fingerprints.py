"""Exact (no shot noise) 4-bond fingerprints for all 81 patterns.

Uses the paper's own circuit builder. The SWAP test measures
P(anc=0) = (1 + <SWAP_ab>)/2, so bond = sqrt(max(0, <psi|SWAP_ab|psi>)),
computed here directly from the final state vector.
"""
import json
import sys
from itertools import product
from pathlib import Path

import numpy as np
import cirq

HERE = Path(__file__).parent.resolve()
sys.path.insert(0, str(HERE))
RESULTS = HERE.parent / "results"
from run_p4s_memory_persistence_cirq import (  # noqa: E402
    build_square_dynamics, BOND_PAIRS, states_for_labels,
)

LABELS = ["alpha", "beta", "gamma"]
SHORT = {"alpha": "a", "beta": "b", "gamma": "g"}
Q = cirq.LineQubit.range(17)


def swap_expectation(psi, left, right):
    t = psi.reshape((2,) * 17)
    perm = list(range(17))
    for a, b in zip(left, right):
        ia, ib = a.x, b.x
        perm[ia], perm[ib] = perm[ib], perm[ia]
    return float(np.real(np.vdot(t, np.transpose(t, perm))))


def fingerprint(labels, n_periods, J=0.1):
    qc, regs, _ = build_square_dynamics(states_for_labels(labels), n_periods, J)
    psi = cirq.Simulator(dtype=np.complex128).simulate(
        qc, qubit_order=Q).final_state_vector
    raw = [swap_expectation(psi, regs[u], regs[v]) for _, u, v in BOND_PAIRS]
    return raw


def main():
    patterns = [list(c) for c in product(LABELS, repeat=4)]
    out = {"patterns": ["".join(SHORT[x] for x in p) for p in patterns]}
    for n in (1, 3):
        raws = [fingerprint(p, n) for p in patterns]
        out[f"swap_expect_n{n}"] = raws
        out[f"bond_n{n}"] = [[float(np.sqrt(max(0.0, r))) for r in row]
                             for row in raws]
        print(f"n={n} done", flush=True)
    (RESULTS / "exact_fingerprints.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
