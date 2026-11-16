# Protocol 4S-Memory: Content-Specific Memory Persistence on the Merkabit Substrate

**Core result.** Six deterministic "memory" configurations on the 4-square
merkabit lattice produce bond-pattern signatures that remain mutually
distinguishable across at least ten Coxeter periods of internal
dynamics. At n = 10, pairwise bond-vector distances are 74% of their
n = 1 values — memories decay slowly rather than collapsing. Even more
striking: between n = 1 and n = 3, pairwise distances **grow** (mean
0.70 → 0.84), indicating early-period feature amplification before slow
decay sets in. The substrate does not merely sustain coherence — it
sustains *content*.

## Motivation

Protocol 4S established that the 4-spinor tesseract sustains the coherence
observable |⟨u|v⟩| ≈ 0.47 under internal dynamics. Protocol 4S-Tunnel
(Paper 31) established that the cross-chiral bond encodes ordered-pair
directional information. Protocol 4S-NGon (Paper 32) established that
the bond-level lookup table is topology-independent across triangle,
square, and hexagon.

None of these established whether specific INPUT content is preserved
across many Coxeter periods. The substrate could sustain coherence while
forgetting what was stored — which would make it a noise source, not a
memory register.

This experiment tests the memory-persistence claim directly: given a
specific Z₃ label configuration encoding a "memory," does the bond
pattern at late horizons reflect the original input, or does it converge
to a universal attractor common across all memories?

## Method

Four-square lattice (N = 4, 17 qubits) with the full Protocol 4S-Z3-three-P
internal dynamics (three isoclinic rotations + chiral P gate per step)
plus perimeter iSWAP^J tunnels (J = 0.1). Six deterministic memories
tested:

| Memory | Pattern (A, B, C, D) |
|--------|----------------------|
| M1 | α, β, γ, α |
| M2 | α, γ, β, α |
| M3 | β, γ, α, β |
| M4 | γ, β, α, γ |
| M5 | α, α, α, α (uniform alpha — reference) |
| M6 | β, β, β, β (uniform beta — reference) |

Each memory's bond pattern was measured at horizons n ∈ {1, 2, 3, 5, 10}
Coxeter periods, four perimeter bonds (AB, BC, CD, DA), 3 repeats × 2,048
shots per measurement. Ideal unitary dynamics (p_depol = 0).

For each (memory, horizon), the 4-dimensional bond vector
`(tunnel_AB, tunnel_BC, tunnel_CD, tunnel_DA)` is recorded. Memory
distinguishability is quantified by computing Euclidean distance between
bond vectors of every memory pair (15 pairs total for 6 memories), and
summarising by pairwise mean, max, and min at each horizon.

## Result

### Pairwise distances vs horizon

| Horizon n | Mean distance | Max | Min |
|-----------|---------------|-----|-----|
| 1 | 0.696 | 0.983 | 0.198 |
| 2 | 0.766 | 1.109 | 0.277 |
| **3** | **0.839** (peak) | 1.075 | 0.577 |
| 5 | 0.740 | 1.270 | 0.206 |
| 10 | 0.513 | 0.782 | 0.199 |

At n = 10 the mean distance is 74% of its n = 1 value. Memories remain
significantly distinguishable; decay is slow.

### Three distinctive features

**1. Memory persists to n = 10 periods.** The substrate does not forget
the input by period 10. Even the closest pair (M2 vs M5, distance 0.20)
remains above typical SWAP-test noise levels (SEM < 0.02 per bond).

**2. Distance peaks at n = 3, not n = 1.** Between n = 1 and n = 3 the
mean distance **grows** (0.70 → 0.84). The dynamics amplify
memory-distinguishing features in the early periods before they slowly
decay. This is unusual — standard dynamical systems either preserve
distance (conservative / reversible) or decay it exponentially
(dissipative). The merkabit dynamics show a distinct *grow then slow
decay* pattern.

**3. Minimum and maximum distances evolve differently.** The max
pairwise distance peaks at n = 5 (1.27, for M2 vs M6), while the mean
peaks at n = 3. Different memory pairs are amplified and decayed on
different timescales, suggesting multiple dynamical modes at work.

### Bond-pattern detail at peak and late horizons

At n = 3 (peak distinguishability):

| Memory | bond_AB | bond_BC | bond_CD | bond_DA |
|--------|---------|---------|---------|---------|
| M1 α-β-γ-α | 0.72 | 0.31 | 0.35 | 0.59 |
| M2 α-γ-β-α | 0.44 | 0.56 | 0.44 | 0.74 |
| M3 β-γ-α-β | 0.60 | 0.73 | 0.63 | 0.30 |
| M4 γ-β-α-γ | 0.63 | 0.66 | 0.37 | 0.58 |
| M5 α-α-α-α | 0.69 | 0.69 | 0.70 | 0.70 |
| M6 β-β-β-β | 0.22 | 0.21 | 0.21 | 0.21 |

Each row is visibly distinct from the others. Six memories, six distinct
4-dimensional fingerprints.

At n = 10 (late horizon), memories remain distinguishable though with
reduced contrast:

| Memory | bond_AB | bond_BC | bond_CD | bond_DA |
|--------|---------|---------|---------|---------|
| M1 α-β-γ-α | 0.15 | 0.50 | 0.78 | 0.56 |
| M2 α-γ-β-α | 0.43 | 0.52 | 0.43 | 0.63 |
| M3 β-γ-α-β | 0.72 | 0.74 | 0.43 | 0.72 |
| M4 γ-β-α-γ | 0.44 | 0.23 | 0.64 | 0.37 |
| M5 α-α-α-α | 0.40 | 0.38 | 0.58 | 0.58 |
| M6 β-β-β-β | 0.46 | 0.62 | 0.62 | 0.54 |

Patterns shift and re-arrange but remain distinguishable. Memory content
is preserved, not lost.

## Interpretation

The substrate is doing something computationally significant: it is
**amplifying distinguishing features** of the input in the early
dynamics, before slowly dissipating them. Structurally, this is the
signature of a system performing feature-extraction: early layers spread
input-specific information across representational degrees of freedom,
making the pattern more separable, before later layers hold it and
gradually lose it.

This is the same functional role played by the early layers of a deep
neural network. Classical ML intuition says: "shallow feature extraction,
then deeper layers for classification." The merkabit substrate appears
to do this natively, without training — the early Coxeter periods
amplify memory-distinguishing features because of the architecture's
structure, not because of any optimisation.

### What this claims (carefully bounded)

- Under ideal unitary dynamics, six distinct deterministic memory
  configurations on a 4-site ring substrate produce bond-pattern vectors
  that remain pairwise distinguishable (mean distance > 0.5, max > 0.75)
  for at least 10 Coxeter periods (120 internal steps).
- Memory distinguishability is amplified by the early dynamics: mean
  pairwise distance grows from n = 1 (0.70) to n = 3 (0.84) before
  declining.
- Each memory produces a visibly unique 4-dimensional bond-pattern
  fingerprint.

### What this does NOT claim

- We did not test noise. Under Willow-realistic p_depol = 0.005, we
  expect significantly faster decay — similar to the 2-merkabit tunnel
  result where signal damped by factor exp(-130·n·p).
- We did not test the LARGE-N scaling. Six memories fit easily; 100
  orthogonal memories on a larger lattice have different capacity
  implications.
- We did not demonstrate RETRIEVAL — we showed the bond patterns
  remain distinguishable, not that the original Z₃ label configuration
  can be read back from the bond pattern. Decoding is a separate
  question.

## Connection to quantum AI

This is the first concrete evidence that the merkabit substrate supports
**content-specific memory**, not just coherence sustain. Combined with
the earlier Protocol 4S results, we now have:

- Coherence sustain (Protocol 4S)
- Ordered-pair directional information (Protocol 4S-Tunnel)
- Topology-independent local rule (Protocol 4S-NGon)
- **Content-memory persistence to at least 10 Coxeter periods** (this)

For the AI-relevance question: the substrate does not just hold a
state — it holds *distinguishable* states of different inputs, and it
does so while performing early-dynamics feature amplification. That is
the specific combination of properties an associative-memory register
needs.

Whether this generalises to LEARNING (updating memory via training) and
RETRIEVAL (decoding stored patterns from bond-pattern queries) is
undetermined. But the substrate-level requirement — "hold distinct
content-specific states stably" — is now experimentally supported.

## Proposed hardware extension (Observable 18)

Replicate the memory-persistence test on IBM Eagle r3 or Heron r2 at
17 qubits. Pre-register predicted bond patterns for M1–M4 at n = 2 and
n = 3. Two thresholds:

- **Weak pass:** hardware bond vectors show mean pairwise distance > 0.3
  at n = 2, demonstrating input-specific signatures survive Willow-realistic
  noise.
- **Strong pass:** distance growth n = 1 → n = 3 detectable on hardware
  (distance ratio > 1.1), demonstrating the early-period amplification
  signature.

Resource budget: 6 memories × 4 bonds × 4 repeats × 4,096 shots × 2 horizons
= ~790 k shots, approximately 45 QPU-minutes. Same order as Observables
14, 16, 17 from Papers 31 and 32.

## Follow-up experiments

**E1.** Memory capacity: how many mutually distinguishable memories can
the 4-site substrate hold? Test 20 memories, measure minimum pairwise
distance. If min distance stays above noise floor for ≥ 9 memories, the
4-site register has at least 9-ary capacity — comparable to log₂(9)
≈ 3.2 bits of addressable memory per 4-site plaquette.

**E2.** Noise-robustness: repeat at p_depol ∈ {0.001, 0.005} to find the
memory-persistence horizon under realistic noise. Predicted: n ≤ 2 at
Willow-realistic.

**E3.** Retrieval protocol: can we design a measurement that RECOVERS
the original Z₃ label pattern from the bond-pattern fingerprint? This
is the content-addressable-memory test and would close the loop from
"storage" to "recall."

**E4.** Scaling: repeat on 6-site hexagon or larger lattices. Does
memory persistence scale with lattice size or with bond count?

Each of these is an independent paper-length project. Together they
would establish (or falsify) the "merkabit as quantum associative
memory" claim empirically.

## Reproducibility

- `cirq/run_p4s_memory_persistence_cirq.py` — experiment script
- `results/p4s_memory_cirq_*.json` — raw per-repeat data
- `paper/figures/fig_memory_persistence.png` — summary figure

Runtime: approximately 25 minutes on a standard laptop at state-vector
simulation. Density-matrix simulation at 17 qubits is prohibitive; noise
sweeps are reserved for the hardware test.
