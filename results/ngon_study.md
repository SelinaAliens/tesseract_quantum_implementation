# Protocol 4S-NGon: Bond-Level Locality is Complete

**Core result.** Across triangle (N=3, 13 qubits), 4-square (N=4, 17 qubits),
and hexagon (N=6, 25 qubits) topologies, every perimeter tunnel returns a
value depending *only* on its local (u_upstream, v_downstream) ordered
pair. The mapping is a universal 9-entry lookup table over Z₃ × Z₃
labels. Topology — triangle, square, hexagon, or any ring — does not
modify the bond response.

The architecture is therefore a **lattice of independent 2-trit directional
gates executing in parallel**, not a gauge theory with non-local holonomy
invariants.

## The universal lookup table

At n = 1 Coxeter period, J = 0.1, ideal (p_depol = 0), aggregated across
the three tested topologies (triangle, 4-square, hexagon) and all bond
positions within each:

| u \ v | α | β | γ |
|-------|-------|-------|-------|
| **α** | 0.68 ± 0.01 | 0.59 ± 0.01 | 0.69 ± 0.01 |
| **β** | 0.53 ± 0.02 | 0.18 ± 0.03 | **0.000 ± 0.000** |
| **γ** | 0.34 ± 0.02 | 0.57 ± 0.02 | 0.23 ± 0.03 |

The β → γ entry is exactly zero (destructive interference from the chiral
P gate + iSWAP combination). All other entries are continuous values
between 0.15 and 0.70. The table is not symmetric under transpose:
`lookup[β, γ] = 0` while `lookup[γ, β] = 0.57`. This asymmetry is the
ordered-pair directional signal at the bond level.

## What this rules out

- **Z₃ plaquette holonomy.** If the architecture were a Z₃ gauge theory,
  families with the same loop-sum Z₃ phase would give similar observables.
  They do not. Within-phase-class variance exceeds between-phase-class
  variance in every tested topology (4-square, triangle, hexagon).
- **Non-local structure at any tested scale.** Triangle (3 sites),
  4-square (4 sites, closed loop), and hexagon (6 sites) all report bond
  values that are pairwise independent. No cross-bond correlation that
  isn't reducible to the local ordered pair at each bond.
- **Size- or parity-dependent effects.** Triangle has 3 bonds (odd),
  hexagon has 6 bonds (even). Both report identical ordered-pair values
  at every bond position. The architecture is not sensitive to odd/even
  loop parity.

## What this confirms

- **Locality.** The bond observable is a function of (u_from, v_to) only.
- **Universality of the β → γ destructive zero.** Across every topology
  tested, β → γ gives exactly 0.000 ideal tunnel coherence. This is not
  an artefact of the 2-merkabit test — it is a structural property of
  the (chiral P + iSWAP^J) combination, independent of what else is in
  the lattice.
- **Parallel execution.** On an N-merkabit ring, all N perimeter bonds
  execute simultaneously in a single Coxeter period. The tunnel gate is
  inherently parallel.

## Complete per-topology data

### Triangle (N = 3, 13 qubits, 4 repeats × 2048 shots)

| family | bond 0→1 | bond 1→2 | bond 2→0 |
|--------|----------|----------|----------|
| aaa | a→a = 0.69 | a→a = 0.69 | a→a = 0.69 |
| bbb | b→b = 0.22 | b→b = 0.17 | b→b = 0.15 |
| ggg | g→g = 0.20 | g→g = 0.26 | g→g = 0.22 |
| abg | a→b = 0.59 | **b→g = 0.000** | g→a = 0.34 |
| gba | g→b = 0.57 | b→a = 0.55 | a→g = 0.70 |
| bga | **b→g = 0.000** | g→a = 0.36 | a→b = 0.58 |
| agb | a→g = 0.70 | g→b = 0.57 | b→a = 0.54 |

### 4-square (N = 4, 17 qubits, 6 repeats × 4096 shots)

| family | bond AB | bond BC | bond CD | bond DA |
|--------|---------|---------|---------|---------|
| aaaa | 0.69 | 0.69 | 0.70 | 0.70 |
| bbbb | 0.18 | 0.21 | 0.21 | 0.21 |
| gggg | 0.22 | 0.24 | 0.22 | 0.21 |
| bgbg | **0.000** | 0.58 | **0.000** | 0.58 |
| bbgg | 0.21 | **0.000** | 0.22 | 0.59 |

### Hexagon (N = 6, 25 qubits, 3 repeats × 1024 shots)

| family | bond 0 | bond 1 | bond 2 | bond 3 | bond 4 | bond 5 |
|--------|--------|--------|--------|--------|--------|--------|
| aaaaaa | 0.69 | 0.70 | 0.68 | 0.68 | 0.68 | 0.67 |
| bbbbbb | 0.15 | 0.22 | 0.16 | 0.18 | 0.17 | 0.14 |
| gggggg | 0.27 | 0.27 | 0.23 | 0.21 | 0.18 | 0.26 |
| abgabg | 0.59 | **0.000** | 0.35 | 0.58 | **0.000** | 0.33 |
| gbagba | 0.58 | 0.51 | 0.69 | 0.55 | 0.55 | 0.68 |
| **bgbgbg** | **0.000** | 0.56 | **0.000** | 0.60 | **0.000** | 0.56 |
| bgabga | **0.000** | 0.35 | 0.60 | **0.000** | 0.36 | 0.57 |

Observe `bgbgbg` on the hexagon: **three perfect zeros** at every other
bond, exactly where the β → γ transition occurs.

## Implications for ternary computation

1. **The tunnel gate is a 2-trit directional primitive with a complete 9-entry lookup table.** This table is:

   | u \ v | α | β | γ |
   |-------|---|---|---|
   | α | 0.68 | 0.59 | 0.69 |
   | β | 0.53 | 0.18 | 0.000 |
   | γ | 0.34 | 0.57 | 0.23 |

   It has full rank (9 distinct approximate values, with 0.000 and 0.18
   being the most distinctive). Under binarisation (threshold at e.g.
   0.15), each bond gives a 1-bit output per 2-trit input — a 2-trit-to-
   1-bit function with non-trivial truth table.

2. **Parallelism is native.** On a lattice of N merkabits with E edges,
   all E bonds execute one 2-trit gate per Coxeter period,
   simultaneously. For the Eisenstein hexagonal lattice (6-fold
   coordinated, E = 3N), this is 3× the merkabit count in per-tick
   throughput.

3. **The architecture is a Z₃-symmetric cellular automaton**, not a
   gate-model computer with arbitrary connectivity. Computation proceeds
   by:
   - Preparing an initial lattice configuration of Z₃ labels
   - Running 1–2 Coxeter periods of internal + tunnel dynamics
   - Measuring selected bonds
   Each measurement is destructive per-bond; full-lattice readout requires
   E separate circuit runs.

4. **Natural applications.** Ternary-graded quantum simulations map
   directly. Specific examples:
   - 3-state Potts models on arbitrary lattices
   - Ternary cellular automata with nearest-neighbor rules
   - Any Hamiltonian decomposing into Z₃-graded nearest-neighbor terms
   - Classical CSP / satisfiability problems with 3-coloring structure

5. **Not natural applications.** Problems requiring non-local gate
   connectivity (e.g., random circuit sampling with long-range gates) or
   arbitrary deep circuits (depth > 2 Coxeter periods at Willow noise)
   do not map well onto this architecture.

## Paper 32 structure

The bond-level locality result is the Paper 32 headline. Structure
candidate:

1. **Theory.** Framework recap: tesseract, cross-chiral tunnel, chiral P
   gate, bond observable.
2. **2-merkabit primitive** (from Paper 31): ordered-pair directional
   asymmetry, universal β → γ destructive zero.
3. **Topology independence.** Triangle, square, hexagon all report the
   same ordered-pair lookup table at every bond. Present the universal
   9-entry table.
4. **Z₃ holonomy falsified.** Variance analysis across loop-phase
   classes for the 4-square and hexagon experiments.
5. **Consequences for computation.** Lattice = register, edge = gate,
   Coxeter period = clock tick, readout = per-bond SWAP test.
6. **Natural algorithms** — Potts, Z₃ CA, ternary simulations.
7. **Hardware pre-registration.** Observables for triangle on 13 qubits
   and 4-square on 17 qubits at IBM Eagle r3 or Heron r2.

## Reproducibility

- `cirq/run_p4s_ngon_cirq.py --N 3` — triangle (13 qubits, ~2 minutes)
- `cirq/run_p4s_ngon_cirq.py --N 4` — 4-square (17 qubits, ~5 minutes)
- `cirq/run_p4s_ngon_cirq.py --N 6` — hexagon (25 qubits, ~15-25 minutes)
- Raw data: `results/p4s_3gon_cirq_*.json`, `results/p4s_4square_cirq_*.json`,
  `results/p4s_6gon_cirq_*.json`

All sims use Cirq state vector simulator at p_depol = 0. Noise sweeps
at larger N are computationally expensive (density matrix at 17+ qubits
is prohibitive) and are left for hardware confirmation rather than
simulation.
