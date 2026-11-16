import json
from pathlib import Path
import numpy as np
HERE = Path(__file__).parent.resolve().parent / "results"
def greedy(D, thr):
    n = D.shape[0]; flat = D.copy(); np.fill_diagonal(flat, -1)
    i, j = divmod(int(np.argmax(flat)), n)
    if D[i, j] < thr: return []
    sel = [i, j]; rem = set(range(n)) - set(sel)
    while rem:
        best, bm = None, -1
        for k in rem:
            md = min(D[k, s] for s in sel)
            if md >= thr and md > bm: best, bm = k, md
        if best is None: break
        sel.append(best); rem.discard(best)
    return sel
def dmat(fp): return np.linalg.norm(fp[:, None, :] - fp[None, :, :], axis=2)
bond = lambda p0: np.sqrt(np.maximum(0, 2 * p0 - 1))

ex = json.loads((HERE / "exact_fingerprints.json").read_text())
nz = json.loads((HERE / "noisy_p0.005_n1_T500.json").read_text())
assert ex["patterns"] == nz["patterns"]
S = np.array(ex["swap_expect_n1"]); P0i = (1 + S) / 2
P0n = np.array(nz["p0_mean"]); sem = np.array(nz["p0_sem"])
print("mean P0 sem %.4f" % sem.mean())
# linear fit in P0 space
x = P0i.ravel(); y = P0n.ravel(); w = 1 / sem.ravel() ** 2
A = np.vstack([np.ones_like(x), x]).T
cov = np.linalg.inv(A.T @ (A * w[:, None])); beta = cov @ (A.T @ (w * y))
res = y - A @ beta; chi2 = (w * res ** 2).sum()
print("P0_noisy = %.4f + %.4f * P0_ideal ; slope se %.4f ; chi2/dof %.2f (dof %d)"
      % (beta[0], beta[1], np.sqrt(cov[1, 1]), chi2 / (len(x) - 2), len(x) - 2))
print("fixed point P0 = %.4f (max mixed 0.625)" % (beta[0] / (1 - beta[1])))
print("residual rms %.4f, max %.4f" % (np.sqrt((res**2).mean()), np.abs(res).max()))
# per-bond-position fits
for b in range(4):
    c = np.polyfit(P0i[:, b], P0n[:, b], 1); print("  bond %d slope %.3f icpt %.3f" % (b, c[0], c[1]))
# bond-space damping as the paper defines it
bi = bond(P0i); bn = bond(P0n)
m = np.abs(bi - 0.5) > 0.1
f = (bn[m] - 0.5) / (bi[m] - 0.5)
print("paper-style damping factor (|bond_i-0.5|>0.1, n=%d): mean %.3f median %.3f sd %.3f range %.2f..%.2f"
      % (m.sum(), f.mean(), np.median(f), f.std(), f.min(), f.max()))
c = np.polyfit(bi.ravel(), bn.ravel(), 1)
print("bond-space fit: bond_n = %.3f + %.3f bond_i ; corr %.3f" % (c[1], c[0], np.corrcoef(bi.ravel(), bn.ravel())[0, 1]))
print("noisy bond range %.3f..%.3f ; ideal %.3f..%.3f" % (bn.min(), bn.max(), bi.min(), bi.max()))
P0fit = (A @ beta).reshape(81, 4)
print("\nCapacity, paper criterion (Euclid distance of bond vectors >= D_hw)")
print(" D_hw  paper_proj  direct(raw MC)  direct(linear-fit smoothed)  proj f=.384 on exact")
paper = {0.023: 71, 0.05: 59, 0.07: 51, 0.10: 32, 0.15: 16, 0.20: 8}
for t, n in paper.items():
    print(" %.3f  %4d  %4d  %4d  %4d" % (t, n, len(greedy(dmat(bn), t)), len(greedy(dmat(bond(P0fit)), t)),
          len(greedy(dmat(0.5 + 0.384 * (bi - 0.5)), t))))
# MC-noise effect on raw count: resample smoothed with MC sem
rng = np.random.default_rng(3); r = []
for _ in range(200):
    r.append([len(greedy(dmat(bond(P0fit + rng.normal(0, sem))), t)) for t in (0.07, 0.10)])
r = np.array(r); print(" smoothed + MC noise resample: N(0.07)=%.1f+-%.1f  N(0.10)=%.1f+-%.1f" % (r[:,0].mean(), r[:,0].std(), r[:,1].mean(), r[:,1].std()))
# shot-noise-correct criterion in P0 space, 4096 shots
def zmat(P, shots=4096):
    v = P * (1 - P) / shots
    d2 = (P[:, None, :] - P[None, :, :]) ** 2 / (v[:, None, :] + v[None, :, :])
    return np.sqrt(d2.sum(axis=2))
print("\nShot-noise criterion (4096 shots/bond, combined separation >= k sigma)")
print(" k   ideal  noisy(smoothed)  noisy(raw MC)")
for k in (3, 5, 8):
    print(" %d  %4d  %4d  %4d" % (k, len(greedy(zmat(P0i), k)), len(greedy(zmat(P0fit), k)), len(greedy(zmat(P0n), k))))
# bond standard error at 4096 shots
for P in (0.52, 0.625, 0.74):
    se = np.sqrt(P * (1 - P) / 4096); print(" P0 %.3f: se(P0) %.4f, se(bond) %.4f" % (P, se, se / bond(np.array(P))))
# distinct classes under noise: min pair z
Z = zmat(P0fit); up = Z[np.triu_indices(81, 1)]
print("pairs (of 3240) below 3 sigma, smoothed noisy: %d ; ideal: %d" % ((up < 3).sum(), (zmat(P0i)[np.triu_indices(81,1)] < 3).sum()))
