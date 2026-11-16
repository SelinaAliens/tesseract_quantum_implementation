"""Baseline: is the merkabit circuit better at keeping 81 patterns apart than
other circuits with the same inputs, layout and read-outs?

Same 81 input states (the paper's state preparation), same four SWAP-test
bonds, exact fingerprints (no shot noise, no gate noise). Circuits compared:
  merkabit        the paper's dynamics
  none            state preparation only
  no_tunnel       paper's internal gates, tunnel gates removed
  rand_internal   every within-site gate replaced by a Haar-random gate of the
                  same size on the same qubits; the J = 0.1 tunnels kept
  rand_all        every gate, tunnels included, replaced by a Haar-random gate
Usage: python baseline_capacity.py <n_periods> <seeds> <workers>
"""
import json
import sys
from itertools import product
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent.resolve()
sys.path.insert(0, str(HERE))
RESULTS = HERE.parent / "results"
LABELS = ["alpha", "beta", "gamma"]
NQ = 16
_cache = {}


def circuit(labels, n_periods):
    import cirq
    from run_p4s_memory_persistence_cirq import (
        build_square_dynamics, BOND_PAIRS, states_for_labels)
    qc, regs, _ = build_square_dynamics(states_for_labels(labels), n_periods, 0.1)
    ops = []
    for mi, moment in enumerate(qc):
        for op in moment.operations:
            idx = tuple(q.x for q in op.qubits)
            ops.append((mi == 0, idx, cirq.unitary(op)))
    assert sum(1 for o in ops if o[0]) == 8
    bonds = [(tuple(q.x for q in regs[u]), tuple(q.x for q in regs[v]))
             for _, u, v in BOND_PAIRS]
    return ops, bonds


def haar(dim, rng):
    z = (rng.normal(size=(dim, dim)) + 1j * rng.normal(size=(dim, dim))) / np.sqrt(2)
    q, r = np.linalg.qr(z)
    return q * (np.diag(r) / np.abs(np.diag(r)))


def apply(t, u, idx):
    k = len(idx)
    t = np.tensordot(u.reshape((2,) * (2 * k)), t, axes=(list(range(k, 2 * k)), list(idx)))
    return np.moveaxis(t, list(range(k)), list(idx))


def fingerprint(args):
    labels, n_periods, mode, seed = args
    ops, bonds = circuit(labels, n_periods)
    rng = np.random.default_rng(seed)       # same seed -> same random circuit for all patterns
    t = np.zeros((2,) * NQ, dtype=complex); t[(0,) * NQ] = 1.0
    for is_prep, idx, u in ops:
        tunnel = len({q // 4 for q in idx}) > 1
        if not is_prep:
            if mode == "none":
                continue
            if mode == "no_tunnel" and tunnel:
                continue
            if mode == "rand_all" or (mode == "rand_internal" and not tunnel):
                u = haar(u.shape[0], rng)
        t = apply(t, u, idx)
    out = []
    for left, right in bonds:
        perm = list(range(NQ))
        for a, b in zip(left, right):
            perm[a], perm[b] = perm[b], perm[a]
        s = float(np.real(np.vdot(t, np.transpose(t, perm))))
        out.append(float(np.sqrt(max(0.0, s))))
    return out


def greedy(D, thr):
    n = D.shape[0]; flat = D.copy(); np.fill_diagonal(flat, -1)
    i, j = divmod(int(np.argmax(flat)), n)
    if D[i, j] < thr:
        return []
    sel = [i, j]; rem = set(range(n)) - set(sel)
    while rem:
        best, bm = None, -1
        for k in rem:
            md = min(D[k, s] for s in sel)
            if md >= thr and md > bm:
                best, bm = k, md
        if best is None:
            break
        sel.append(best); rem.discard(best)
    return sel


THR = [0.1, 0.2, 0.3, 0.4, 0.5]


def summarise(fp):
    fp = np.array(fp)
    D = np.linalg.norm(fp[:, None, :] - fp[None, :, :], axis=2)
    return [len(greedy(D, t)) for t in THR] + [float(D[np.triu_indices(81, 1)].mean())]


def main():
    n_periods = int(sys.argv[1]); seeds = int(sys.argv[2]); workers = int(sys.argv[3])
    patterns = [list(c) for c in product(LABELS, repeat=4)]
    res = {}
    with Pool(workers) as pool:
        for mode, ns in (("merkabit", 1), ("none", 1), ("no_tunnel", 1),
                         ("rand_internal", seeds), ("rand_all", seeds)):
            rows = []
            for s in range(ns):
                fp = pool.map(fingerprint, [(p, n_periods, mode, 7000 + s) for p in patterns])
                rows.append(summarise(fp))
            res[mode] = rows
            a = np.array(rows, dtype=float)
            print(f"{mode:14s} seeds={ns:2d}  N(D) mean " +
                  " ".join(f"{x:5.1f}" for x in a[:, :5].mean(0)) +
                  "  max " + " ".join(f"{int(x):3d}" for x in a[:, :5].max(0)) +
                  f"  mean dist {a[:, 5].mean():.3f}", flush=True)
    (RESULTS / f"baseline_n{n_periods}.json").write_text(json.dumps({"thr": THR, "res": res}, indent=1))


if __name__ == "__main__":
    main()
