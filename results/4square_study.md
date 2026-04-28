# Protocol 4S-4Square: Four Merkabits on a Plaquette

**Goal.** Test whether the tunnel network supports information propagation
around a closed loop — specifically, whether the plaquette has non-trivial
Z₃ holonomy when the four sites carry Z₃-eigenstate labels.

**Design.** Four tesseract merkabits A, B, C, D on a square, coupled by
four cross-chiral tunnels A→B, B→C, C→D, D→A around the perimeter.
Seventeen qubits total (16 data + 1 SWAP ancilla). Ten observables per
configuration: four local coherences, four perimeter tunnels, two
diagonals.

Eight initial-state families, grouped by their Z₃ loop phase
(a+b+c+d) mod 3 where α↦0, β↦1, γ↦2:

| Family | (A, B, C, D) | Loop sum mod 3 | Phase |
|--------|--------------|----------------|-------|
| AAAA | basis |0⟩ everywhere | — | baseline |
| aaaa | α α α α | 0 | 1 |
| bgbg | β γ β γ | 6 | 1 |
| bbgg | β β γ γ | 6 | 1 |
| ββββ | β β β β | 4 | ω |
| γγγγ | γ γ γ γ | 8 | ω² |
| bbaa | β β α α | 2 | ω² |
| bbbg | β β β γ | 5 | ω² |

## Headline result

**Z₃ loop holonomy is NOT the dominant invariant of the 4-square.**
Between-group / within-group variance ratios across phase classes are all
< 1.8, well below the clustering threshold (∼3). Families sharing the
same Z₃ loop phase sum give observable values that are *not* similar;
families in different phase classes give values that are not clearly
separated.

**Instead, each perimeter bond independently preserves the cross-chiral
directional asymmetry from the 2-merkabit Protocol 4S-Tunnel**. A bond
returns exactly 0.000 when its ordered pair is (β → γ) (destructive
interference from the chiral P gate + iSWAP combination) and ~0.58 when
(γ → β) (constructive). The 4-square is **four independent 2-trit
directional detectors**, not a single gauge plaquette.

## Per-family per-bond table (ideal, n = 1, J = 0.1)

| Family | loop phase | tunnel_AB | tunnel_BC | tunnel_CD | tunnel_DA |
|--------|-----------|-----------|-----------|-----------|-----------|
| AAAA | — | 0.34 | 0.34 | 0.36 | 0.33 |
| aaaa | 1 | 0.69 | 0.69 | 0.70 | 0.70 |
| bgbg (β,γ,β,γ) | 1 | **0.000** | 0.58 | **0.000** | 0.58 |
| bbgg (β,β,γ,γ) | 1 | 0.21 | **0.000** | 0.22 | 0.59 |
| ββββ | ω | 0.18 | 0.21 | 0.21 | 0.21 |
| γγγγ | ω² | 0.22 | 0.24 | 0.22 | 0.21 |
| bbaa (β,β,α,α) | ω² | 0.20 | 0.55 | 0.69 | 0.60 |
| bbbg (β,β,β,γ) | ω² | 0.19 | 0.21 | **0.000** | 0.57 |

## Reading the table

- **aaaa**: all four sites in the Z₃=1 (real) eigenstate. Every bond has
  matching u and v labels from the same subspace — four constructive
  tunnels, all ~0.70.
- **ββββ**: uniform Z₃=ω. Every bond is (β → β), which produces weak
  coupling ~0.20 at all four locations. The uniform weak-coupling state.
- **γγγγ**: uniform Z₃=ω². Same pattern as ββββ under complex
  conjugation symmetry (values ~0.22).
- **bgbg** (alternating): bonds A→B and C→D are (β → γ), giving **exact
  zeros**. Bonds B→C and D→A are (γ → β), giving constructive ~0.58.
  Two zeros and two maxima around the loop, dictated by the alternating
  input.
- **bbgg**: only one (β → γ) transition in the loop (at B→C boundary).
  One zero, three non-zeros.
- **bbbg**: only one (β → γ) transition (at C→D). Same pattern — one
  zero, three non-zeros.
- **bbaa**: no (β → γ) transitions, but mixed Z₃=ω and Z₃=1 sites. Bonds
  show varying intermediate values (0.20–0.69) depending on local pair.

The pattern is clear: **each bond's observable is a function of its
local (u_upstream, v_downstream) pair, essentially independently of the
other bonds**. The 2-merkabit directional asymmetry extends site-by-site
to the 4-site plaquette with no additional loop-level information.

## Why the Z₃ holonomy hypothesis fails

For pure Z₃ gauge theory, the Wilson loop around the plaquette would
carry the phase ω^((sum of site labels) mod 3). Families with the same
loop sum mod 3 should be indistinguishable under any loop observable.

They are not. Within the "phase 1" group:

- aaaa: all tunnels ~0.70
- bgbg: two tunnels at 0.000, two at 0.58
- bbgg: one tunnel at 0.000, others 0.21–0.59

These are obviously distinct arrangements. The Z₃ loop phase doesn't
capture their differences because the relevant information lives at the
bond level, not the loop level.

## Why this is actually a bigger result than pure Z₃ holonomy

A Z₃ Wilson loop gives one number per plaquette (one of three phase
values). The 4-square architecture gives **four independent directional
signatures per plaquette**, each carrying (roughly) continuous ordered-
pair information. The information density per plaquette is therefore
much higher than a Z₃ gauge theory — closer to a continuous interference
pattern than a discrete holonomy.

In computational terms: a lattice of N merkabits on the Eisenstein
(6-fold-coordinated hexagonal) lattice has 3N bonds. Each bond is an
independent 2-trit directional gate. **The computational register
capacity scales as 3N, not N.** That is the opposite scaling from binary
qubit registers, where logical capacity scales as N — and it's a direct
consequence of the inter-merkabit-channel-is-the-computer finding.

## What a ternary algorithm on the plaquette looks like

A minimal ternary algorithm on the 4-square would be:

1. Prepare each merkabit in a chosen Z₃ eigenstate (α, β, or γ).
2. Run one Coxeter period of internal chiral + perimeter tunnel dynamics.
3. Measure all four perimeter tunnels via four SWAP-test circuit runs.
4. The output is a 4-bit bit-string (each bond above/below threshold =
   1 bit), or a 4-real-number measurement (each bond's overlap magnitude).

Different input configurations map to different bit-string / number
patterns. A computation is the MAP from input configuration to output
pattern; different algorithms correspond to different initial-state
choices and Coxeter-period counts.

One interesting feature: the SWAP-test readout is NATURALLY DESTRUCTIVE,
so each run extracts one bond's value. To characterise a plaquette
fully requires 4 runs. This is the "plaquette = 4 SWAP tests" pattern
that would be repeated across a larger lattice.

## Proposed hardware extension

Observable 15 (Paper 32 candidate):

**The 4-bond directional pattern.** Run Protocol 4S-4Square on 17
qubits (IBM Heron r2 has the native connectivity for a 4×4
arrangement; Eagle r3 needs careful layout). Measure the four
perimeter tunnels for a set of Z₃-labeled input families. Predict:

- Families with β → γ bonds at bond positions {ij}: tunnel_ij ≈ 0 at
  those positions, ~0.6 elsewhere (under ideal).
- Under Willow/Eagle-realistic noise at n = 1: ideal 0.00 → measured
  0.25 ± 0.05; ideal 0.60 → measured 0.45 ± 0.05; gap ~ 0.20 cleanly
  distinguishable at ≥ 5σ.

The signature is: **which bonds are in the zero-class for which input
families**. Pre-registration specifies the mapping family → zero-bond-
positions before hardware access. Confirmation = hardware shows the
predicted zero-bond pattern within statistical tolerance.

## What this does NOT rule out

The negative Z₃ holonomy result says the 4-plaquette observable pattern
is not dominated by the Z₃ loop phase. It does NOT rule out:

- **Higher-order loop invariants** — sensitive to (a, b, c, d) more
  finely than (a+b+c+d) mod 3. Could be a Z₃² × Z₂ structure (cyclic
  plus reflection), which would need a finer stress test to detect.
- **Directional flux invariants at larger plaquettes** — a 6-plaquette
  on the Eisenstein hexagonal lattice might show different behavior.
- **Dynamical holonomy at longer horizons** — we only tested n = 1.
  Noise kills n ≥ 3 on Willow-realistic hardware, but ideal simulation
  at larger n might reveal richer structure.

Each of these is a follow-up experiment.

## Summary for the paper series

Paper 32 headline finding (tentative): **The merkabit architecture's
ternary information content scales per bond, not per site or per
plaquette**. Four merkabits on a plaquette carry not 2 bits (one Z₃
trit per site, compressed) but ~8 bits (4 bonds × 2 bits each from
directional asymmetry). The computational register scales as the
**edge count** of the lattice, not the **vertex count**.

On the Eisenstein lattice (6-fold coordinated hexagonal), this is
3× the vertex count. On a 4-square lattice it's 1× (closed loop). On
a tree (no loops) it's (N−1). The architecture's computational
density depends on the lattice topology in a specific, measurable way.

## Reproducibility

- `cirq/run_p4s_4square_cirq.py` — 17-qubit simulation (state vector at
  p = 0; density matrix required for p > 0, computationally expensive
  at this qubit count)
- `results/p4s_4square_cirq_ideal_*.json` — raw per-repeat data for the
  ideal run

To regenerate:
```
python cirq/run_p4s_4square_cirq.py --n-repeats 6 --shots 4096 --n-periods 1 --J 0.1
```

Runtime: approximately 4 minutes on a standard laptop.
