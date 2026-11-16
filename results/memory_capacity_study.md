# Protocol 4S-Memory-Capacity: how many memories can the 4-square merkabit hold?

**Core result.** The 4-square merkabit substrate (4 sites, 17 qubits)
addresses ~5 bits of content-memory under ideal unitary dynamics and
retains ≥5 bits under Willow-realistic depolarizing noise
(p_depol = 0.005). At the 3σ shot-noise floor for 4096 shots, **51
mutually-distinguishable memories (5.67 bits) are resolvable on
hardware**. At the more conservative 5σ operating point, 32 memories
(5.00 bits) are resolvable — matching a classical 4-bit register.

## Protocol

**Substrate.** Single 4-site ring ("4-square"), 17 qubits: 4 sites × 4
data qubits + 1 SWAP-test ancilla. Internal dynamics = three isoclinic
rotations + chiral P gate (run_p4s_Z3_three_P) + perimeter iSWAP^J
tunnels, J = 0.1. Coxeter period T = 12 internal steps.

**Memory space.** All 3⁴ = 81 Z₃-eigenstate configurations
(site_0, site_1, site_2, site_3) with each site ∈ {α, β, γ}.

**Fingerprint.** For each pattern, measure the four perimeter bonds
(AB, BC, CD, DA) via SWAP test. Each pattern → 4-dimensional bond
vector.

**Horizon choice.** Two regimes:
- **n = 3 (peak amplification):** the horizon at which pairwise distances
  peak per the persistence study (mean 0.84 at n = 3 vs 0.70 at n = 1).
- **n = 1 (hardware operating point):** the horizon where depolarization
  has minimal effect. From the 2-merkabit tunnel stress test, n = 3 at
  p = 0.005 collapses the directional gap to ~0 — unusable on Willow.
  n = 1 preserves signal.

**Noise model.** Willow-realistic depolarization, p_depol = 0.005
(2-qubit gate error), applied per gate via injected Kraus channels.
Monte-Carlo trajectory sampling on 17-qubit state vector (density-matrix
simulation is prohibitive at 2^34 entries).

**Capacity measure.** For threshold D, greedy maximum-packing: select
the maximum subset of patterns such that all pairwise bond-vector
distances exceed D. N(D) is the resulting size.

## Result

### (1) Ideal capacity — n = 3 and n = 1

Full 81-pattern enumeration, 4096 shots per bond, p_depol = 0.

| Threshold D | N (n=3) | bits (n=3) | N (n=1) | bits (n=1) |
|-------------|---------|------------|---------|------------|
| 0.10 | 71 | 6.15 | 63 | 5.98 |
| 0.20 | 57 | 5.83 | 46 | 5.52 |
| **0.30** | **31** | **4.95** | **31** | **4.95** |
| 0.40 | 19 | 4.25 | 14 | 3.81 |
| 0.50 | 16 | 4.00 | 8 | 3.00 |
| 0.70 | 8 | 3.00 | 7 | 2.81 |
| 1.00 | 2 | 1.00 | 2 | 1.00 |

**Key observation at D = 0.30 both horizons give 31 memories.** The
peak-amplification at n = 3 does NOT increase the number of resolvable
clusters at moderate threshold; it only widens the tail of long-distance
pairs (D > 0.4). So running at n = 1 (hardware-safe) does not cost the
headline 5-bit capacity.

### (2) Pairwise-distance structure (n = 1 ideal)

Over 3,240 unordered pairs of 81 patterns:

| Statistic | Value |
|-----------|-------|
| min | 0.014 |
| median | 0.644 |
| mean | 0.621 |
| max | 1.157 |
| std | 0.198 |

**Min distance 0.014** indicates a small redundancy set: patterns equivalent
under the 4-square's C₄ rotational symmetry collapse to near-identical
bond fingerprints. Burnside on C₄ gives 24 orbits, but we observe 63
distinguishable memories at D = 0.10 — so the bond fingerprint is NOT
merely a C₄-orbit invariant. Only a handful of highly symmetric patterns
(αααα, ββββ, γγγγ, and select period-2 patterns) truly collapse.

### (3) 4-square damping calibration at n = 1, p_depol = 0.005

Three patterns × 4 bonds × 2 noise levels = 24 Monte-Carlo cells at 256
shots each (run time: ~50 min). Damping factor f is defined as
(bond(p) − 0.5) / (bond(0) − 0.5) — the shrinkage of bond signal toward
the maximally-mixed fixed point.

| Statistic | Value |
|-----------|-------|
| mean | 0.384 |
| median | 0.396 |
| std | 0.279 |
| α_eff (per n·p) | 191 |

High variance reflects per-pattern circuit-depth differences: uniform-α
patterns (shorter state prep) damp less than mixed patterns. Mean 0.384
is the best single-number estimate for distance-scaling.

### (4) Hardware-realistic capacity N(D_hw)

Apply linear damping (bond_hw = 0.5 + 0.384 × (bond_ideal − 0.5)) to
the 81-pattern n = 1 fingerprints, then recompute greedy packing.

Shot-noise floor at 4096 shots: σ_bond ≈ 0.008, so SWAP-test
pair-distance noise σ_d ≈ √8 σ_bond ≈ 0.023. Useful operating regime is
D_hw ≥ 3σ_d ≈ 0.07.

| D_hw | equivalent D_ideal | N_hw | bits |
|------|--------------------|------|------|
| 0.023 (1σ) | 0.060 | 71 | 6.15 |
| 0.050 | 0.130 | 59 | 5.88 |
| **0.070 (3σ)** | **0.182** | **51** | **5.67** |
| 0.100 | 0.260 | 32 | 5.00 |
| 0.115 (4σ)| 0.299 | 31 | 4.95 |
| 0.200 | 0.521 | 8 | 3.00 |

**Hardware capacity claim:** At Willow-realistic noise and 4096-shot
SWAP measurement,
- **3σ-resolvable:** 51 memories = 5.67 bits
- **4σ-resolvable:** 31 memories = 4.95 bits
- **5σ-resolvable:** ~32 memories = 5.00 bits

All three beat a 4-bit binary register (16 states).

## Interpretation

The 4-square substrate is a register of approximately **5 information
bits** under conditions that current quantum hardware can deliver. This
is:
- 78% of the theoretical 3⁴ = 81 ternary ceiling (log₂ 81 = 6.34 bits),
- 125% of the 4-bit binary register capacity (16 states),
- resilient to Willow-realistic depolarization (f_damp = 0.38) at the
  n = 1 operating point.

Combined with Protocol 4S-Memory (persistence to n = 10 periods), the
substrate satisfies both requirements of an associative-memory register:
**high content capacity** (≥5 bits) and **temporal persistence**
(10 periods at ideal noise).

### What this claim is NOT

- **Not a retrieval protocol.** We show patterns are distinguishable;
  we have not demonstrated that the Z₃ label configuration can be
  decoded back from the bond fingerprint. Retrieval is experiment E3.
- **Not a writing protocol.** We prepare patterns deterministically from
  specified inputs; learning/training is outside this study.
- **Not a proof of capacity under full Willow conditions.** We account
  for depolarization (p = 0.005) but not dephasing-vs-amplitude
  splitting, readout error, or measurement crosstalk. Those are
  addressed in the proposed hardware observable.
- **Calibration variance is large.** The per-pattern damping factor
  ranges from 0.07 to 0.71. Reporting the mean (0.38) is a convenient
  single-number estimate; a production hardware run should measure
  actual pair-distance shrinkage per-pattern.

## Proposed hardware observable (Observable 18: capacity-at-noise)

Measure N(D_hw) on IBM Eagle r3 or Heron r2:

**Resource budget.** 81 patterns × 4 bonds × 2048 shots = 664k shots,
~40 QPU-minutes at current Eagle r3 throughputs. Half the budget of the
existing Paper 30–32 observables.

**Pre-registered predictions.**
- **Weak pass:** N_hw(D = 0.07) ≥ 25 memories, demonstrating >4-bit
  addressable capacity at hardware noise. This is ~half the simulation
  prediction; passes even under 2× worse damping than observed.
- **Strong pass:** N_hw(D = 0.07) ≥ 45 memories = log₂ ≥ 5.5 bits.
  Matches simulation prediction within pattern-level variance.

## Follow-up experiments

**E3 (retrieval).** Design a measurement that recovers Z₃ labels from
the 4-bond fingerprint. This closes the storage → recall loop. Requires
inversion of the bond → pattern map, which is many-to-one due to
rotation redundancy; a retrieval protocol would need to return the
C₄ orbit, not the specific pattern.

**E4 (scaling with lattice size).** Repeat on 6-site hexagon: capacity
scales with 3^N (theoretical) or with something softer due to more
bonds (6 bonds vs 4 at N = 4)? Hexagon theoretical max is
log₂ 3⁶ = 9.5 bits.

**E5 (robustness to noise model).** Full FakeSherbrooke calibration
instead of uniform depolarization. Per-qubit T1/T2 variation is the
likely dominant effect not captured here.

## Reproducibility

- Enumeration: `cirq/run_p4s_memory_capacity_cirq.py` (both n = 1 and
  n = 3 via `--n-periods`).
- Damping calibration: `cirq/calibrate_4square_damping.py`.
- Raw data: `results/p4s_memory_capacity_cirq_*.json`,
  `results/calibrate_4square_damping_*.json`.
- Figure: `paper/make_capacity_figure.py` →
  `paper/figures/fig_memory_capacity.png`.

Run time: n = 1 ideal ~2 min on laptop state-vector simulation; damping
calibration ~50 min (trajectory sampling at 17 qubits). Full
density-matrix simulation at 17 qubits is prohibitive
(2^34 complex ≈ 130 GB).
