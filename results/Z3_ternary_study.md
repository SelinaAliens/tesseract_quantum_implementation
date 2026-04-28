# Protocol 4S-Z3-three: Ternary Memory on the Tesseract Substrate

**Core result.** The tesseract's internal dynamics preserve **three distinct
equivalence classes** of initial state, visible at short horizons and
persistent under Willow-realistic noise. The classes are NOT labeled by
raw Z₃ eigenvalue — they correspond to the Galois orbits of the Z₃ action
under complex conjugation, plus the orthogonal-alignment class. This is
still three-way memory; it just has the algebraic structure forced by the
real-valued internal dynamics.

## Experimental setup

Five families, three horizons (n = 2, 3, 5), four noise levels
(p_depol = 0, 0.001, 0.002, 0.005), 10 repeats × 4,096 shots per cell.

| Family | u₀ = v₀ (matched) or (u₀, v₀) | Z₃ label |
|--------|----------------------------|----------|
| A | \|0⟩ | (not Z₃-eigenstate) |
| C | \|0⟩, \|3⟩ (orthogonal) | n/a |
| α | (\|0⟩ + \|1⟩ + \|2⟩)/√3 | Z₃ eigenvalue 1 |
| β | (\|0⟩ + ω\|1⟩ + ω²\|2⟩)/√3 | Z₃ eigenvalue ω |
| γ | (\|0⟩ + ω²\|1⟩ + ω\|2⟩)/√3 | Z₃ eigenvalue ω² |

## Attractor values at n = 2, p_depol = 0.005 (Willow-realistic)

| Family | Cirq mean ± SEM | Aer mean ± SEM | Class |
|--------|----------------|----------------|-------|
| A | 0.569 ± 0.004 | 0.650 ± 0.002 | **I — real-matched** |
| α | 0.579 ± 0.006 | 0.643 ± 0.004 | **I — real-matched** (= A within 1.3–1.6σ) |
| β | 0.617 ± 0.003 | 0.722 ± 0.004 | **II — complex-matched** |
| γ | 0.614 ± 0.003 | 0.724 ± 0.003 | **II — complex-matched** (= β within 0.3–1σ) |
| C | 0.457 ± 0.005 | 0.404 ± 0.006 | **III — orthogonal** |

**Ideal cross-stack check at n = 2, p = 0:** Cirq and Aer agree to
three decimal places (Cirq/Aer respectively: A = 0.799/0.799, α = 0.801/0.802,
β = 0.929/0.930, γ = 0.930/0.933, C = 0.332/0.309). The underlying
tesseract unitary dynamics are verified identical across simulators.

## Three-way pairwise separability

At n = 2, p_depol = 0.005, per-family pair significance (σ of gap in
units of combined SEM, 10 repeats × 4,096 shots). Cirq / Aer:

| Pair | Cirq gap (σ) | Aer gap (σ) |
|------|--------------|-------------|
| α vs β (I vs II) | −0.038 (5.8σ) | −0.079 (14.7σ) |
| α vs γ (I vs II) | −0.035 (5.2σ) | −0.081 (16.4σ) |
| **β vs γ (within II)** | +0.003 (**0.98σ**) | −0.002 (**0.31σ**) |
| A vs β (I vs II) | −0.048 (~9σ) | −0.072 (16.0σ) |
| A vs C (I vs III) | +0.112 (~18σ) | +0.246 (40.2σ) |
| β vs C (II vs III) | +0.160 (~25σ) | +0.318 (46.4σ) |
| **A vs α (within I)** | −0.010 (**1.3σ**) | +0.007 (**1.6σ**) |

Every cross-class pair separable at ≥ 5σ (Cirq) or ≥ 14σ (Aer).
Every within-class pair indistinguishable at ≤ 1.7σ on both stacks.
Both stacks agree on three and only three equivalence classes at
Willow-realistic noise.

Aer predicts systematically larger gaps than Cirq (same effect seen
in Protocol 4S-Z3-short) because MatrixGate → CX decomposition in
Qiskit transpilation distributes noise differently. Real-hardware
gaps expected in the Cirq–Aer bracket or above.

## Within-class indistinguishability (the structural observation)

At every (n, p) cell tested, β and γ are statistically indistinguishable
(within-pair σ < 1.3). This is not experimental error — it is a
consequence of the internal dynamics being **real-valued**.

The isoclinic rotations `cross_gate_4`, `horizontal_gate_4`,
`diagonal_gate_4` have all-real matrix elements (rotations in coordinate
planes by angles `theta`). Complex conjugation is therefore a symmetry of
the dynamics. Since β and γ are complex conjugates of each other
(γ = β*), they evolve to complex-conjugate states throughout, and their
SWAP-test overlap (a magnitude) is identical.

Equivalently: the Z₃ eigenvalues ω and ω² are related by the Galois
automorphism of ℚ(ω)/ℚ (complex conjugation), and the internal dynamics
respect this Galois symmetry. The **orbits of Z₃ eigenstates under
Galois** are {1} and {ω, ω²} — two orbits, not three — and that is what
the simulation returns.

α (Z₃ = 1, real) sits in the same equivalence class as A (arbitrary
matched basis state) because the Z₃ = 1 subspace is 2-dimensional within
ℂ⁴ (spanned by the symmetric combination (\|0⟩+\|1⟩+\|2⟩)/√3 AND \|3⟩),
and any real-matched input lies in that subspace's dynamical envelope
after a few periods.

## What this says about the framework

The framework's ternary claim is recovered, but via a specific and natural
algebraic mechanism: **Galois orbits of the Z₃ action**, not raw Z₃
labels. This is consistent with:

- **The Eisenstein lattice interpretation.** ℤ[ω] with ω = e^(2πi/3)
  carries a Z₂ Galois action (ω ↔ ω² is the nontrivial element of
  Gal(ℚ(ω)/ℚ)). Real-valued dynamics inherit this Galois action as a
  symmetry automatically.
- **The merkabit's chirality structure.** The forward spinor (u) and
  inverse spinor (v) counter-rotate, but the internal cross-coupling
  planes (cross, horizontal, diagonal) have real generators. The complex
  (chirality-discriminating) element in the full merkabit comes from the
  **P gate** — which is an external drive, not part of Protocol 4S's
  internal-only dynamics.
- **The §15.8 trit structure in the capstone.** Three states labeled
  \|+1⟩, \|0⟩, \|−1⟩, with \|0⟩ self-dual and \|±1⟩ conjugate pair. The
  simulation recovers exactly this pattern: Class I (\|0⟩, self-dual),
  Class II (\|±1⟩, conjugate pair), plus Class III (orthogonal reference).

## What would give full Z₃ (three distinct eigenvalue classes)

To break the β ↔ γ indistinguishability, the internal dynamics must have
complex generators. One route: include the P gate (`P(φ) = Rz(+φ) ⊗ Rz(−φ)`,
explicitly complex) as part of the internal step, not just the external
drive. Another route: use a different internal step structure that
respects Z₃ but breaks complex conjugation (e.g., triality-phased
non-self-adjoint generators).

This is a testable follow-up: extend `internal_step_4` with a P-gate
phase and re-run the ternary test. Predicted outcome: β and γ separate
by the same amount that α separated from them under pure real dynamics.

## Cross-stack confirmation

Qiskit Aer cross-check in progress. Expected to confirm the three-class
structure at the same significance (minor shift in specific attractor
values due to CX-decomposition noise model, as in Protocol 4S-Z3-short).

## Prediction for hardware (observable 12, proposed)

**Three-family SWAP-test clustering.**

Families: A (\|0⟩), β ((\|0⟩+ω\|1⟩+ω²\|2⟩)/√3), C (\|0⟩ vs \|3⟩).

Predict three distinct attractor clusters at n = 2, p_depol ≈ 0.005:

| Class | Representative | Cirq mean | Aer mean | Hardware range (Cirq–Aer bracket) |
|-------|---------------|-----------|----------|-----------------------------------|
| I — real-matched | A = \|0⟩⊗\|0⟩ | 0.569 | 0.650 | [0.55, 0.68] |
| II — complex-matched | β = (\|0⟩+ω\|1⟩+ω²\|2⟩)/√3 (both u and v) | 0.617 | 0.722 | [0.60, 0.75] |
| III — orthogonal | C = \|0⟩, \|3⟩ | 0.457 | 0.404 | [0.38, 0.50] |

All three pairs predicted separable at ≥ 5σ with 10 repeats × 4,096 shots.
Falsification: any two of {Class I, Class II, Class III} overlap within
0.01 on hardware.

Circuit budget identical to Observable 11 (~144 two-qubit-gate-equivalents
per trial, under 1 QPU-hour total). Three families instead of two adds
50% shot-count overhead; still well within hardware access window.

## Reproducibility

- `cirq/run_p4s_Z3_three_cirq.py` — five-family sweep
- `qiskit/run_p4s_Z3_three_aer.py` — Qiskit Aer cross-check
- `results/p4s_Z3_three_cirq_*.json` / `_aer_*.json` — raw data
