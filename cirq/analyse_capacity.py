"""Capacity from exact fingerprints vs the stored 4096-shot fingerprints."""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent.resolve()
PRIV = HERE.parent / "results"


def greedy(D, thr):
    n = D.shape[0]
    flat = D.copy(); np.fill_diagonal(flat, -1)
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


def dmat(fp):
    return np.linalg.norm(fp[:, None, :] - fp[None, :, :], axis=2)


ex = json.loads((PRIV / "exact_fingerprints.json").read_text())
names = ex["patterns"]
stored = {3: json.loads((PRIV / "p4s_memory_capacity_cirq_20260420T124932.json").read_text()),
          1: json.loads((PRIV / "p4s_memory_capacity_cirq_20260420T131659.json").read_text())}

for n in (1, 3):
    fe = np.array(ex[f"bond_n{n}"]); fs = np.array(stored[n]["fingerprints"])
    assert stored[n]["patterns"] == names
    print(f"\n===== n = {n} =====")
    print("stored (4096-shot) minus exact: max |diff| %.4f, rms %.4f"
          % (np.abs(fs - fe).max(), np.sqrt(((fs - fe) ** 2).mean())))
    # distinct exact fingerprints
    De = dmat(fe)
    classes = []
    for i in range(81):
        for c in classes:
            if De[i, c[0]] < 1e-9:
                c.append(i); break
        else:
            classes.append([i])
    print("distinct exact fingerprints among 81 patterns:", len(classes))
    print("class sizes:", sorted((len(c) for c in classes), reverse=True))
    up = De[np.triu_indices(81, 1)]
    print("exact pair distances: #pairs==0: %d, min nonzero %.4f, median %.4f"
          % ((up < 1e-9).sum(), up[up > 1e-9].min(), np.median(up)))
    print("  D     N_exact  N_stored(recomputed)  N_stored(file)")
    filetab = {c["D"]: c["N"] for c in stored[n]["capacity_table"]}
    Ds = dmat(fs)
    for thr in [0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]:
        print("  %.2f  %5d  %5d  %s" % (thr, len(greedy(De, thr)),
                                       len(greedy(Ds, thr)), filetab.get(thr, "-")))
    if n == 1:
        print("\n-- paper Table 7: damped fingerprints, f = 0.384 --")
        print("  D_hw   N(paper)  N(stored fp, recomputed)  N(exact fp)")
        paper = {0.023: 71, 0.05: 59, 0.07: 51, 0.10: 32, 0.15: 16, 0.20: 8}
        for thr, npap in paper.items():
            a = len(greedy(dmat(0.5 + 0.384 * (fs - 0.5)), thr))
            b = len(greedy(dmat(0.5 + 0.384 * (fe - 0.5)), thr))
            print("  %.3f  %5d  %5d  %5d" % (thr, npap, a, b))
        # what does shot noise alone do to distinct-looking patterns?
        rng = np.random.default_rng(1)
        raw = np.array(ex["swap_expect_n1"])
        p0 = (1 + raw) / 2
        res = []
        for _ in range(200):
            k = rng.binomial(4096, p0)
            fpn = np.sqrt(np.maximum(0, 2 * k / 4096 - 1))
            res.append([len(greedy(dmat(0.5 + 0.384 * (fpn - 0.5)), t))
                        for t in (0.023, 0.05, 0.07, 0.10)])
        res = np.array(res)
        print("  fresh 4096-shot samples of the IDEAL fingerprints, damped by 0.384:")
        for t, col in zip((0.023, 0.05, 0.07, 0.10), res.T):
            print("    D_hw %.3f: N = %.1f +- %.1f (range %d-%d)"
                  % (t, col.mean(), col.std(), col.min(), col.max()))
        print("\nexact n=1 classes (members):")
        for c in classes:
            print("   ", " ".join(names[i] for i in c), "->", np.round(fe[c[0]], 3))
