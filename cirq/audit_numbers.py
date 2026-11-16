import json, sys, itertools
import numpy as np
sys.argv = ["x"]
from baseline_capacity import fingerprint
from pathlib import Path
L = {"a": "alpha", "b": "beta", "g": "gamma"}
M = {"M1": "abga", "M2": "agba", "M3": "bgab", "M4": "gbag", "M5": "aaaa", "M6": "bbbb"}
print("== persistence, exact fingerprints (paper: sampled 3x2048 shots)")
paper = {1: (0.696, 0.983, 0.198), 2: (0.766, 1.109, 0.277), 3: (0.839, 1.075, 0.577), 5: (0.740, 1.270, 0.206), 10: (0.513, 0.782, 0.199)}
for n in (1, 2, 3, 5, 10):
    fp = {k: np.array(fingerprint(([L[c] for c in v], n, "merkabit", 0))) for k, v in M.items()}
    ds = {(a, b): np.linalg.norm(fp[a] - fp[b]) for a, b in itertools.combinations(M, 2)}
    v = np.array(list(ds.values()))
    print(f"n={n:2d} exact mean {v.mean():.3f} max {v.max():.3f} min {v.min():.3f} ({min(ds, key=ds.get)})  paper {paper[n]}")
    if n == 3:
        for k in M: print("   ", k, np.round(fp[k], 2))
ex = json.loads((Path(__file__).parent.parent / "results" / "exact_fingerprints.json").read_text())
names = ex["patterns"]; f1 = np.array(ex["bond_n1"])
D = np.linalg.norm(f1[:, None] - f1[None], axis=2); iu = np.triu_indices(81, 1)
order = np.argsort(D[iu])[:8]
print("== closest pairs at n=1:", [(names[iu[0][o]], names[iu[1][o]], round(float(D[iu][o]), 4)) for o in order])
rot = lambda s: s[1:] + s[0]
dr = [D[i, names.index(rot(n))] for i, n in enumerate(names) if rot(n) != n]
print("== distance between a pattern and its C4 rotation: min %.3f median %.3f" % (min(dr), np.median(dr)))
cal = json.loads((Path(__file__).parent.parent / "results" / "calibrate_4square_damping_20260420T133438.json").read_text())
print("== calibration keys", list(cal.keys())[:12])
print(json.dumps(cal, indent=0)[:1500])
