# Period-12 Exactness Verification

Verifies the headline claim of Paper 34 — that the v_D entropy spectrum is
periodic at the Coxeter number h(E₆) = 12 — to machine precision, by direct
state-vector comparison at offset_T2 = base vs base + 12 (which reduce to
identical dynamics modulo T_CYCLE = 12).

## Result summary

| Precision | max ‖ψ(b) − ψ(b+12)‖₂ | max │ΔS│ | Machine eps |
|---|---|---|---|
| `complex64` (single, default of cirq.Simulator) | 8.7 × 10⁻⁸ | 1.2 × 10⁻⁷ | 1.19 × 10⁻⁷ |
| `complex128` (double) | **1.6 × 10⁻¹⁶** | **4.4 × 10⁻¹⁶** | 2.22 × 10⁻¹⁶ |

At `complex128`, the state-vector L2 distance and the v_D von Neumann
entropy delta both sit **below machine epsilon** at base offsets 0, 4, 8
versus 12, 16, 20. Two of three offset pairs (4↔16 and 8↔20) are
**bit-identical** to ‖·‖₂ = 0.000e+00 — the simulator returned the
exact same state vector for offsets that differ by one Coxeter period.

This justifies the description in Paper 34's abstract that the spectrum
is "perfectly period-12 to machine precision" — provided the simulation
is run at `complex128`. The original Stage C JSON deposit
(`p4s_double_triangle_stageC_20260421T171812.json`) was generated at the
cirq default `complex64`, which shows ~10⁻⁸ residuals consistent with
single-precision FP rounding.

## Files

```
verify_period_12.py                                 verification driver
outputs/verify_period_12_complex64_baseline.json   complex64 reference
outputs/verify_period_12_complex128_3bases.json    complex128 (the verification)
```

## Usage

```bash
# complex64 baseline (matches the main Stage C deposit's precision)
python verify_period_12.py --dtype complex64 --bases 0

# complex128 verification (3 base offsets at the Z_3 triadic points 0, 4, 8)
python verify_period_12.py --dtype complex128 --bases 0 4 8 --low-memory
```

`--low-memory` stages ψ(base) to disk between simulations and streams the
L2 diff from a memory-mapped file. Required for `complex128` on machines
with less than ~16 GB RAM (peak resident memory ≈ 4–5 GB instead of ≈ 8–10 GB).

Memory and runtime per base offset:

| Precision | Resident peak | Disk staging | Per pair |
|---|---|---|---|
| complex64  | ~4 GB | none | ~25 s |
| complex128 | ~5 GB (with `--low-memory`) | 4.3 GB | ~75–90 s |

## What the verification does

For each base offset *b* in the requested set:

1. Builds the full 28-qubit double-triangle circuit at `offset_T2 = b`,
   using the same `build_double_triangle_circuit(...)` builder as the
   Stage C deposit. State preparation is `(α, α, α)` on Triangle 1 and
   `(α, α, α)` on Triangle 2 (one representative input pair; the period-12
   property is per-circuit, not per-input).
2. Simulates with `cirq.Simulator(dtype=...)` at the requested precision.
3. Records the v_D von Neumann entropy `S(b)` and the state-vector norm.
4. Stages ψ(b) to disk (in `--low-memory` mode); frees RAM.
5. Builds and simulates the circuit at `offset_T2 = b + 12`.
6. Records `S(b+12)`, norm, and the chunk-streamed L2 distance and
   per-amplitude max of `ψ(b+12) − ψ(b)` against the on-disk ψ(b).

The output JSON records all six numbers per base offset plus per-circuit
runtime.

## Why complex128 should be the production setting

Cirq's `Simulator` defaults to `complex64`. The default is reasonable for
small circuits where the residual single-precision rounding (~10⁻⁷) is
well below shot noise, but for state-vector observables computed
analytically (no shots) the rounding becomes the dominant error source.
Paper 34's entropy-spectrum result is derived analytically from the v_D
reduced density matrix, so single-precision rounding is what shows up as
the "six decimals" agreement reported in the master text §4.3.

Re-running Stage C at `complex128` (324 configurations × ~90 s ≈ 8 hours
on a laptop, ~4.3 GB state vector, ~5 GB resident peak) would tighten
all reported residuals from 10⁻⁸ to 10⁻¹⁶ and make the period-12
exactness reported in Paper 34's abstract literally exact at the FP
level. The verification in this directory demonstrates that the precision
is achievable; it does not yet replace the full Stage C deposit.
