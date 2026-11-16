# Paper 32 (Zenodo 10.5281/zenodo.19855345): version 2 re-check, November 2026

This note covers the files added for version 2 of Paper 32. The two study notes
`memory_capacity_study.md` and `memory_persistence_study.md` are the version 1
records and are kept unchanged; where they differ from this note, this note is
the current reading.

## What changed from version 1

| Item | Version 1 | Version 2 |
|---|---|---|
| Noisy capacity at D_hw = 0.07 (p_depol = 0.005, n = 1) | 51, projected from a 3-pattern calibration | about 38, direct simulation of all 81 patterns |
| Noisy capacity at D_hw = 0.10 | 32 (projected) | about 22 |
| Ideal capacity at D = 0.3, n = 1 | 31 (4,096-shot fingerprints) | 26 (exact fingerprints) |
| Ideal capacity at D = 0.3, n = 3 | 31 | 31 |
| Calibration factor range | 0.07 to 0.71 | -0.15 to 0.91 (mostly 256-shot noise) |
| Bond shot noise at 4,096 shots | 0.008 | 0.015 at bond = 0.5 |

Random-circuit baseline (same state preparation, layout and read-outs, exact
fingerprints): at n = 1 the merkabit circuit lies within the scatter of circuits
with Haar-random gates (26 against 23.9 and 22.4 on average at D = 0.3; 8 with
the tunnels removed). At n = 3 its mean pairwise distance (0.75) exceeds that
of all 20 random circuits tried (0.54 to 0.71). The baseline is noiseless.

The memory-register interpretation of version 1 is withdrawn in version 2.

## Files

Version 1 scripts and results (previously missing from this repository):

- `cirq/run_p4s_memory_persistence_cirq.py`, `cirq/run_p4s_memory_capacity_cirq.py`
- `results/p4s_memory_cirq_20260420T124037.json` (persistence)
- `results/p4s_memory_capacity_cirq_20260420T124932.json` (n = 3), `..._20260420T131659.json` (n = 1)
- `paper/make_memory_figure.py`, `paper/make_capacity_figure.py`, `paper/figures/fig_memory_*.png`

Version 2:

- `cirq/exact_fingerprints.py` -> `results/exact_fingerprints.json`
- `cirq/noisy_capacity.py` -> `results/noisy_p0.005_n1_T500.json` (500 trajectories per pattern, 2.6 h on ten cores)
- `cirq/baseline_capacity.py` -> `results/baseline_n1.json`, `results/baseline_n3.json`
- `cirq/analyse_capacity.py`, `cirq/analyse_noisy.py`, `cirq/audit_numbers.py` (analysis; print to the terminal)
- `paper/make_capacity_figure_v2.py` -> `paper/figures/fig_memory_capacity_v2.png`

## Running

Python 3.10, cirq-core 1.5.0, numpy, matplotlib. From `cirq/`:

    python exact_fingerprints.py
    python analyse_capacity.py
    python noisy_capacity.py 500 0.005 10 1
    python analyse_noisy.py
    python baseline_capacity.py 1 20 10
    python baseline_capacity.py 3 10 10
