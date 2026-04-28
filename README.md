# Tesseract Quantum Implementation

Reference implementation for the **cross-chiral tunnel** primitive and its
**topology-independent Z₃ cellular-automaton** extension on the 4-spinor
tesseract merkabit. Companion code, raw simulation data, and pre-registered
hardware-deployment scripts for two papers in the Merkabit Research Series:

| Paper | Title | Headline result |
|-------|-------|-----------------|
| **31** | *The Cross-Chiral Tunnel and Its Topology-Independent Z₃ Cellular Automaton: A Pre-Registered Hardware Protocol Stack on Current Superconducting Quantum Processors* | 9-qubit two-merkabit protocol; ordered-pair (β, γ) → 0.000 destructive vs (γ, β) → 0.762 constructive at 166 σ ideal / 22 σ Willow-realistic noise |
| **32** | *The Merkabit Tunnel Network as a Z₃ Cellular Automaton: Topology-Independent Bond Locality and the Universal 9-Entry Gate Table* | Universal 9-entry Z₃ × Z₃ lookup table reproduces to within 0.03 across triangle (N = 3), 4-square (N = 4), and hexagon (N = 6) rings; Z₃ plaquette-holonomy interpretation falsified |

Together the two papers establish that the merkabit architecture is a
**Z₃-symmetric quantum cellular automaton** with a *derived* local rule —
not a gauge theory with loop-level invariants. Register capacity scales with
edge count *E* rather than vertex count *N*, giving native edge-level
parallelism on the Eisenstein coordination lattice.

## Architectural context

This work composes two prior strata:

- **The base merkabit paper** — *The Merkabit: A Ternary Computational Unit on the Eisenstein Lattice* (Stenberg, 2025). Geometric origin of the E₆-derived angle table.
- **Protocol 4S** — self-sustaining coherence on a single 4-spinor merkabit. The 4-spinor sustains `|⟨u|v⟩| ≈ 0.47` across ≥10 Coxeter periods under internal cross-coupling alone (no external Floquet drive); the 2-spinor control under the same no-drive condition is frozen. This freezing/sustaining contrast (Observables 9 and 10) is the empirical foundation of every script in this repository.

Hardware confirmation of the 2-spinor substrate (5/5 pre-registered observables on IBM Eagle r3 and Heron r2) is reported in Papers 24–26 of the series. The full forcing chain {Eisenstein lattice → Z₃ triangle → P₂₄ binary tetrahedral → McKay → E₆} is consolidated in the capstone:

> *Paper 30: A Unified Theory from E₆ Coxeter Geometry* — Stenberg (2026), [Zenodo 19690395](https://doi.org/10.5281/zenodo.19690395).

For the **composed-architecture extensions** (19-qubit Pentachoric Verification Protocol, 28-qubit ternary spectrum), see the companion repository
[`SelinaAliens/pentachoric_verification`](https://github.com/SelinaAliens/pentachoric_verification).

## Repository layout

```
README.md             this file
LICENSE               MIT
PREDICTION.md         Pre-registered Observables 9 and 10 (Protocol 4S baseline)

cirq/                 Cirq state-vector + trajectory implementations
  run_p4s_cirq.py                  Protocol 4S baseline (foundational)
  run_p4s_Z3_cirq.py               Z₃ eigenstate ladder
  run_p4s_Z3_short_cirq.py         short-horizon binary alignment memory
  run_p4s_Z3_three_cirq.py         three Galois-orbit classes
  run_p4s_Z3_three_P_cirq.py       four Z₃-labelled classes under chiral P
  run_p4s_Z3_noise_sweep.py        depolarising / amp-damp / phase-damp grid
  run_p4s_tunnel_cirq.py           [P31] 9-qubit two-merkabit cross-chiral tunnel
  stress_test_Jn_cirq.py           [P31] J × n stress grid
  run_p4s_ngon_cirq.py             [P32] N-gon topology scan (N = 3, 4, 6)
  run_p4s_4square_cirq.py          [P32] 4-square deep-dive
  calibrate_4square_damping.py     [P32] 4-square damping at p_depol = 0.005

qiskit/               Qiskit Aer + FakeSherbrooke noise stack (P31)
  run_p4s_aer.py, run_p4s_Z3_*_aer.py, run_p4s_tunnel_aer.py,
  stress_test_noise_aer.py

simulations/          Original four-noise-level sweep driver
  protocol_4S_sweep_cirq.py

willow/               Hardware-deployment scripts (Google Quantum Engine)
  obs14_tunnel.py                  [P31] Observable 14, 9 qubits, ≤ 45 QPU-min
  obs16_triangle.py                [P32] Observable 16, 13 qubits, ~25 QPU-min
  obs17_square.py                  [P32] Observable 17, 17 qubits, ~10 QPU-min
  _engine_wrapper.py               Engine-client adapter (credentials at marked line)

genesis/              Foundational R-locking verification
  R_locking_test.py                Confirms 5-fold {S,R,T,F,P} is the unique
  R_locking_output.txt             cycle giving α⁻¹ = 137.036 to 10⁻⁴

results/              Raw JSON outputs + analysis writeups
  tunnel_study.md                  [P31] main analysis
  tunnel_robustness_study.md       [P31] J × n × noise channel grid
  Z3_short_horizon_study.md        [P31] Z3-short ladder
  Z3_ternary_study.md              [P31] Z3-three (three classes)
  Z3_ternary_chiral_study.md       [P31] Z3-three-P (four classes under chiral P)
  ngon_study.md                    [P32] cross-topology comparison
  4square_study.md                 [P32] 4-square deep-dive
  cross_validation.md              Cirq vs Qiskit Aer consistency
  p4s_*_<timestamp>.json           One JSON per experiment

paper/                Drafts, masters, figures, figure-generation scripts
  paper_31_draft.md, Paper_31.docx
  paper_32_draft.md, Paper_32.docx
  paper_31_merged_draft.md         (merged narrative + Z3 ladder)
  figures/                         PNG outputs (fig1–fig6 per paper)
  make_figures.py, make_figures_32.py, make_figures_extra.py
  md_to_docx.py                    Markdown → docx converter
```

## Hardware observables — pre-registered

| Observable | Paper | Qubits | QPU-min | Script |
|---|---|---|---|---|
| 9  | Base / Protocol 4S | 5  | < 60   | [`cirq/run_p4s_cirq.py`](cirq/run_p4s_cirq.py) |
| 10 | Base / 2-spinor control | 3 | < 60 | [`cirq/run_p4s_cirq.py`](cirq/run_p4s_cirq.py) (control mode) |
| 14 | **Paper 31** — 2-merkabit tunnel | 9  | ≤ 45  | [`willow/obs14_tunnel.py`](willow/obs14_tunnel.py) |
| 16 | **Paper 32** — triangle ring | 13 | ~25 | [`willow/obs16_triangle.py`](willow/obs16_triangle.py) |
| 17 | **Paper 32** — 4-square ring | 17 | ~10 | [`willow/obs17_square.py`](willow/obs17_square.py) |

Pre-registration commit SHAs predate any hardware submission.
Hardware targets: **IBM Eagle r3 / Heron r2** and **Google Willow** in cross-architecture parallel.

## Reproduction

```bash
pip install -r requirements.txt   # cirq>=1.4, qiskit>=2.3, qiskit-aer, numpy, matplotlib

# Paper 31 — full regenerate (~45 min on a laptop)
python cirq/run_p4s_cirq.py
python cirq/run_p4s_Z3_three_P_cirq.py
python cirq/run_p4s_tunnel_cirq.py
python cirq/stress_test_Jn_cirq.py

# Paper 32 — full regenerate (~20 min)
python cirq/run_p4s_ngon_cirq.py
python cirq/run_p4s_4square_cirq.py
python cirq/calibrate_4square_damping.py --shots 256

# Build figures + docx
python paper/make_figures.py
python paper/make_figures_32.py
python paper/md_to_docx.py paper/paper_31_draft.md paper/Paper_31.docx
python paper/md_to_docx.py paper/paper_32_draft.md paper/Paper_32.docx
```

No GPU required. Largest circuit: 25 qubits (P32 hexagon, state-vector simulation).
Density-matrix simulation is prohibitive at ≥17 qubits; noise runs use Monte-Carlo trajectory sampling.

Windows users: set `PYTHONIOENCODING=utf-8` for scripts with Unicode characters.

## Dependencies

- Python 3.13+ (tested on Windows 11)
- Cirq ≥ 1.4
- Qiskit ≥ 2.3 + qiskit-aer (Paper 31 noise stack only)
- NumPy, Matplotlib, python-docx

## Related repositories

- [`SelinaAliens/pentachoric_verification`](https://github.com/SelinaAliens/pentachoric_verification) — composed-architecture extensions (Paper 33 PVP, Paper 34 ternary spectrum)
- [`SelinaAliens/The_Merkabit`](https://github.com/SelinaAliens/The_Merkabit) — base-paper companion code
- [`SelinaAliens/merkabit-companion-analysis`](https://github.com/SelinaAliens/merkabit-companion-analysis) — cross-platform KWW / threshold analyses

## License

[MIT](LICENSE) — Copyright © 2026 Selina Stenberg.

## Citation

See [`CITATION.cff`](CITATION.cff). When citing the papers individually, prefer the Zenodo records (DOIs added on release).

## Provenance

Both papers (31, 32) were drafted in collaboration with **Claude (Anthropic, Opus 4.7, 1M-context)** as a coding, analysis, and drafting assistant. The AI did not execute on IBM or Google hardware and had no operational runtime access; final scientific responsibility rests with the human author.
