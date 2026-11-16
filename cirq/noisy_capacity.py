"""Direct noisy simulation of all 81 patterns (the run the paper calls
'computationally prohibitive' and replaces with a 3-pattern calibration).

Noise model = the paper's inject_depolarize: after every gate, each qubit it
touches gets cirq.depolarize(p*scale), scale = 0.1 (1q), 1.0 (2q), 1.5 (3q).
depolarize(q) = with probability q one of X, Y, Z uniformly.

Each Monte-Carlo trajectory samples those Paulis, evolves the 16-qubit state
exactly, then runs the (noisy) SWAP test for each of the 4 bonds and records
the EXACT P(anc = 0) of that trajectory -- so there is no shot noise on top
of the trajectory noise.

Usage: python noisy_capacity.py <trajectories_per_pattern> <p_depol> <workers> [n_periods]
"""
import json
import sys
import time
from itertools import product
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent.resolve()
sys.path.insert(0, str(HERE))
RESULTS = HERE.parent / "results"

LABELS = ["alpha", "beta", "gamma"]
SHORT = {"alpha": "a", "beta": "b", "gamma": "g"}
NQ = 16
PAULI = [np.array([[0, 1], [1, 0]], dtype=complex),
         np.array([[0, -1j], [1j, 0]], dtype=complex),
         np.array([[1, 0], [0, -1]], dtype=complex)]
H = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)


def extract_ops(labels, n_periods, J):
    """Return [(unitary reshaped, qubit indices)] from the paper's builder."""
    import cirq
    from run_p4s_memory_persistence_cirq import (
        build_square_dynamics, BOND_PAIRS, states_for_labels)
    qc, regs, _ = build_square_dynamics(states_for_labels(labels), n_periods, J)
    ops = []
    for moment in qc:
        for op in moment.operations:
            idx = tuple(q.x for q in op.qubits)
            k = len(idx)
            ops.append((cirq.unitary(op).reshape((2,) * (2 * k)), idx))
    bonds = [(tuple(q.x for q in regs[u]), tuple(q.x for q in regs[v]))
             for _, u, v in BOND_PAIRS]
    return ops, bonds


def apply(t, u, idx):
    k = len(idx)
    t = np.tensordot(u, t, axes=(list(range(k, 2 * k)), list(idx)))
    return np.moveaxis(t, list(range(k)), list(idx))


def apply1(t, m, q):
    return np.moveaxis(np.tensordot(m, t, axes=([1], [q])), 0, q)


def noise(t, qubits, q, rng):
    for qb in qubits:
        if rng.random() < q:
            t = apply1(t, PAULI[rng.integers(3)], qb)
    return t


def swap_test_p0(t16, left, right, p, rng):
    """Noisy SWAP test on ancilla (axis 16). Returns exact P(anc=0)."""
    anc = NQ
    if p == 0:
        perm = list(range(NQ))
        for a, b in zip(left, right):
            perm[a], perm[b] = perm[b], perm[a]
        return 0.5 * (1 + float(np.real(np.vdot(t16, np.transpose(t16, perm)))))
    t = np.zeros(t16.shape + (2,), dtype=complex)
    t[..., 0] = t16
    t = apply1(t, H, anc)
    t = noise(t, [anc], 0.1 * p, rng)
    for a, b in zip(left, right):
        # CSWAP(anc; a, b): swap a,b on the anc=1 branch
        t1 = np.swapaxes(t[..., 1], a, b)
        t = np.stack([t[..., 0], t1], axis=-1)
        t = noise(t, [anc, a, b], 1.5 * p, rng)
    t = apply1(t, H, anc)
    t = noise(t, [anc], 0.1 * p, rng)
    return float(np.sum(np.abs(t[..., 0]) ** 2))


def run_pattern(args):
    labels, n_traj, p, n_periods, J, seed = args
    ops, bonds = extract_ops(labels, n_periods, J)
    rng = np.random.default_rng(seed)
    scale = {1: 0.1, 2: 1.0, 3: 1.5}
    s = np.zeros(4); s2 = np.zeros(4)
    for _ in range(n_traj):
        t = np.zeros((2,) * NQ, dtype=complex)
        t[(0,) * NQ] = 1.0
        for u, idx in ops:
            t = apply(t, u, idx)
            if p > 0:
                t = noise(t, idx, p * scale[len(idx)], rng)
        v = np.array([swap_test_p0(t, l, r, p, rng) for l, r in bonds])
        s += v; s2 += v * v
    mean = s / n_traj
    var = np.maximum(s2 / n_traj - mean ** 2, 0)
    return ("".join(SHORT[x] for x in labels), mean.tolist(),
            (np.sqrt(var / n_traj)).tolist())


def main():
    n_traj = int(sys.argv[1]); p = float(sys.argv[2]); workers = int(sys.argv[3])
    n_periods = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    only = sys.argv[5].split(",") if len(sys.argv) > 5 else None
    patterns = [list(c) for c in product(LABELS, repeat=4)]
    if only:
        patterns = [pt for pt in patterns if "".join(SHORT[x] for x in pt) in only]
    jobs = [(pt, n_traj, p, n_periods, 0.1, 1000 + i) for i, pt in enumerate(patterns)]
    t0 = time.time()
    out = {"p_depol": p, "n_traj": n_traj, "n_periods": n_periods,
           "patterns": [], "p0_mean": [], "p0_sem": []}
    tag = f"noisy_p{p}_n{n_periods}_T{n_traj}" + ("_sub" if only else "")
    with Pool(workers) as pool:
        for k, (name, mean, sem) in enumerate(pool.imap(run_pattern, jobs)):
            out["patterns"].append(name); out["p0_mean"].append(mean)
            out["p0_sem"].append(sem)
            print(f"[{k+1}/{len(jobs)}] {name} P0={np.round(mean, 4).tolist()} "
                  f"sem={np.round(sem, 4).tolist()} t={time.time()-t0:.0f}s", flush=True)
            (RESULTS / f"{tag}.json").write_text(json.dumps(out, indent=1))
    print("done", time.time() - t0)


if __name__ == "__main__":
    main()
