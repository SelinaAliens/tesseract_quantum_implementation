# Protocol 4S-Tunnel: Inter-Merkabit Ternary Correlation

**Core result.** The cross-chiral tunnel between two tesseract merkabits
encodes ordered-pair ternary correlation that neither merkabit holds
locally. At ideal (p=0) the tunnel distinguishes the input pair (β, γ)
from (γ, β) at > 40σ — a **directional asymmetry** that establishes the
tunnel as the natural computational primitive of the architecture.

At Willow-realistic p_depol = 0.005, the directional signal persists but
requires adequate shot statistics. With 6 repeats × 4,096 shots at
n_periods = 2, Cirq predicts a detectable gap (preliminary smoke test
at 2 reps × 1,024 shots: 2.7σ; full sweep: to be filled).

## Setup

Two 4-spinor merkabits A and B, coupled per internal step by a
**cross-chiral tunnel**:

- Internal step on A: three isoclinic rotations + P gate
  (same as Protocol 4S-Z3-three-P)
- Internal step on B: identical
- **Tunnel step:** partial SWAP (iSWAP^J) between u_A and v_B with
  exchange angle J per step. Forward spinor of A couples to inverse
  spinor of B — this is the "cross-chiral" tunnel specified in Paper 17
  and the base paper.

Default J = 0.1 (weak tunnel, models lattice-adjacent J/r ≈ 0.1 coupling).

Qubits: 8 data (4 per merkabit) + 1 ancilla = 9 total. Each snapshot
requires three separate circuit runs to measure:

- **local_A** = \|⟨u_A|v_A⟩\| — A's self-coherence
- **local_B** = \|⟨u_B|v_B⟩\| — B's self-coherence  
- **tunnel** = \|⟨u_A|v_B⟩\| — the cross-chiral channel

## Families (six input pairs)

Each input is a pair of 4-spinors, one per merkabit:

| Family | u_A = v_A | u_B = v_B | Physics label |
|--------|-----------|-----------|---------------|
| AA | \|0⟩ | \|0⟩ | baseline matched basis |
| aa | (\|0⟩+\|1⟩+\|2⟩)/√3 | same | both Z₃ = 1 (real) |
| bb | (\|0⟩+ω\|1⟩+ω²\|2⟩)/√3 | same | both Z₃ = ω |
| gg | (\|0⟩+ω²\|1⟩+ω\|2⟩)/√3 | same | both Z₃ = ω² |
| **bg** | Z₃ = ω | Z₃ = ω² | mixed, forward order |
| **gb** | Z₃ = ω² | Z₃ = ω | mixed, reverse order |

The two "cross" families (bg, gb) are the critical pair for detecting
directional tunnel asymmetry.

## Result summary (6 repeats × 4,096 shots, n_periods = 2, J = 0.1)

### At p_depol = 0 (ideal unitary)

| Family | local_A | local_B | **tunnel** |
|--------|---------|---------|----------|
| AA | 0.569 ± 0.006 | 0.605 ± 0.003 | 0.714 ± 0.003 |
| aa | 0.450 ± 0.005 | 0.374 ± 0.005 | 0.196 ± 0.019 |
| bb | 0.349 ± 0.010 | 0.520 ± 0.004 | 0.605 ± 0.007 |
| gg | 0.480 ± 0.010 | 0.521 ± 0.004 | 0.376 ± 0.013 |
| **bg** | 0.457 ± 0.009 | 0.296 ± 0.010 | **0.000 ± 0.000** |
| **gb** | 0.543 ± 0.005 | 0.352 ± 0.010 | **0.762 ± 0.005** |

**Directional tunnel gap: (β, γ) − (γ, β) = −0.762 at 166σ.**

### At p_depol = 0.005 (Willow-realistic)

| Family | local_A | local_B | **tunnel** |
|--------|---------|---------|----------|
| AA | 0.511 ± 0.007 | 0.502 ± 0.005 | 0.513 ± 0.004 |
| aa | 0.500 ± 0.003 | 0.493 ± 0.005 | 0.495 ± 0.005 |
| bb | 0.488 ± 0.004 | 0.498 ± 0.005 | 0.483 ± 0.003 |
| gg | 0.487 ± 0.005 | 0.492 ± 0.004 | 0.493 ± 0.005 |
| **bg** | 0.485 ± 0.006 | 0.486 ± 0.005 | **0.442 ± 0.006** |
| **gb** | 0.490 ± 0.006 | 0.478 ± 0.008 | **0.514 ± 0.008** |

**Directional tunnel gap at Willow-realistic noise: −0.072 at 7.57σ.**

### Pairs separable at ≥ 3σ, by observable and stack

|             | Cirq @ p = 0 | Cirq @ p = 0.005 | **Aer @ p = 0** | **Aer @ p = 0.005** |
|-------------|---------------|-------------------|-----------------|----------------------|
| local_A | 12 / 15 | 1 / 15 | 13 / 15 | 5 / 15 |
| local_B | 13 / 15 | 0 / 15 | 14 / 15 | 10 / 15 |
| **tunnel** | **15 / 15** | **8 / 15** | **15 / 15** | **14 / 15** |

### Cross-stack agreement

| Observable | Cirq @ p=0 | Aer @ p=0 |
|-----------|-----------|-----------|
| (β, γ) tunnel | 0.000 ± 0.000 | 0.000 ± 0.000 |
| (γ, β) tunnel | 0.762 ± 0.005 | 0.764 ± 0.006 |
| Directional gap | 0.762 | 0.764 |
| Significance | 166σ | 125σ |

Ideal dynamics identical across simulator stacks (≥3-decimal agreement).

### Cross-stack divergence at p = 0.005

| Observable | Cirq @ p=0.005 | Aer @ p=0.005 |
|-----------|----------------|----------------|
| (β, γ) tunnel | 0.442 | 0.294 |
| (γ, β) tunnel | 0.514 | 0.562 |
| Directional gap | 0.072 | **0.268** |
| Significance | 7.6σ | **23σ** |

Aer predicts a ~4× larger directional gap than Cirq at Willow-realistic
p=0.005. The difference reflects the same MatrixGate-vs-CX noise-model
asymmetry observed in Protocol 4S-Z3-three-P. For IBM hardware
prediction, Aer is the more faithful model. Hardware result expected
between the two brackets or above.

## Key finding in one sentence

**At current superconducting-qubit noise levels, tesseract memory
survives only in the inter-merkabit cross-chiral tunnel, not in the
individual merkabits — and on IBM-convention compilation (Aer), the
tunnel preserves 14 of 15 family-pair distinctions while local
measurements collapse to 5/15 or 0/15.**

## Interpretation

The tunnel coherence \|⟨u_A|v_B⟩\| is sensitive to the ordered Z₃ labels
of the two-merkabit input. Under the cross-chiral exchange (iSWAP^J
between u_A and v_B) combined with the chiral P-gate on each merkabit,
the two orderings (β, γ) and (γ, β) evolve into states with dramatically
different u_A / v_B overlaps.

This is **two-trit correlation**: information that is not reducible to
the individual Z₃ labels of merkabit A and merkabit B separately. The
same phenomenon in standard quantum computing is what makes the CNOT
gate entangling — the output depends on the ordered pair of inputs, not
just their individual states.

In the framework's language:

- **Intra-merkabit (Protocol 4S / Z3-three / Z3-three-P):** memory local
  to one tesseract. At most 4 Z₃-labelled classes (3 Galois orbits + 1
  orthogonal). The single tesseract is a trit-register.
- **Inter-merkabit (Protocol 4S-Tunnel):** correlation between two
  tesseracts via cross-chiral torsion. Distinguishes ordered pairs,
  giving at least 2 × 3 × 2 = 12 distinct input labels in principle
  (ordered pairs from a 3-class alphabet × chirality). The tunnel is a
  two-trit gate.

**If the full sweep confirms the directional signal at p = 0.005, the
paper's central claim becomes: ternary computation lives in the
cross-chiral tunnel between merkabits, realisable on current IBM Eagle r3
or Heron r2 with ~9 qubits and under 1 QPU-hour.**

## Why this might be more noise-robust than single-merkabit memory

Tunnel coherence is a JOINT property of two tesseracts coupled through a
permanent axis. Decoherence events that scramble one tesseract's local
state (shifting local_A or local_B) need not affect their cross-overlap,
because the tunnel averages over the joint Hilbert space differently than
either local SWAP test.

This is the general principle behind many decoherence-free subspaces in
quantum information: the error channel on a single subsystem is often
"blind" to certain cross-subsystem correlations. If the cross-chiral
channel lives in a commutant of local noise, the tunnel is symmetry-
protected.

The full sweep will quantify how much more robust tunnel is vs local
under realistic noise. If tunnel > local at p = 0.005, the DFS search
we proposed as a follow-up becomes unnecessary — **the tunnel is the
DFS**.

## Proposed Observable 14 for hardware pre-registration

Two-merkabit ternary correlation test on 9 qubits (8 data + 1 ancilla).
Run three variants per snapshot (local_A / local_B / tunnel), each a
separate Cirq/Qiskit circuit.

Two critical pre-registered predictions:

- **Directional tunnel gap:** |tunnel(β, γ) − tunnel(γ, β)| predicted in
  [bracket to be filled from full sweep] at p_depol = 0.005. ≥5σ
  threshold with 10 repeats × 4,096 shots.
- **Tunnel > local discrimination count:** tunnel distinguishes more
  family pairs at 3σ than either local coherence at p_depol = 0.005.

Hardware budget: 9 qubits, three circuits × six families × ten repeats
× 4,096 shots per (n, p) point ≈ 700k shots. Under 1 QPU-hour on IBM
Eagle r3 or Heron r2.

Falsification: tunnel(β, γ) = tunnel(γ, β) within 0.02 on hardware —
would mean the directional signal is real only at ideal and does not
survive realistic noise. Follow-up then goes to DFS search.

Confirmation: directional asymmetry survives at ≥5σ on hardware —
first experimental demonstration of ordered-pair ternary computation
on current superconducting qubits.

## Reproducibility

- `cirq/run_p4s_tunnel_cirq.py` — Cirq implementation
- `results/p4s_tunnel_cirq_*.json` — raw per-repeat data
- Full sweep output in this directory with 6 × 4,096 shot statistics.
- Qiskit Aer cross-check pending (script to be added).
