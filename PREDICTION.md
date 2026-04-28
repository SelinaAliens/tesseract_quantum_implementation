# Pre-registered Prediction: 2-to-4 Spinor Self-Sustaining Threshold

**Pre-registration commits (timestamps unmodified):**

- Cirq / Willow:   [`selinaserephina-star/willow_hardware_merkabit@30984ca`](https://github.com/selinaserephina-star/willow_hardware_merkabit/commit/30984ca) — 2026-04-19
- Qiskit / IBM:    [`selinaserephina-star/merkabit_hardware_test@4a7bbb4`](https://github.com/selinaserephina-star/merkabit_hardware_test/commit/4a7bbb4) — 2026-04-20

Both commits predate any hardware submission. This document is the
authoritative summary; the falsifiable pre-registration lives at the SHAs above.

## Prediction

The merkabit architecture is geometrically 2-spinor at the dual-pentachoron
level (the configuration used in every existing hardware experiment: 2 qubits
per merkabit pair) and 4-spinor at the tesseract level (4 qubits per merkabit
pair, with u, v ∈ ℂ⁴). The 4-spinor admits three orthogonal isoclinic rotation
planes (cross, horizontal, diagonal) that the 2-spinor does not.

Under *internal-only* dynamics (isoclinic rotations applied in sequence with
no external Floquet modulation), the 4-spinor sustains a coherence attractor
at time-averaged `|<u|v>|` ≈ 0.47 across many Coxeter periods. The 2-spinor
under the same no-drive protocol has no channel for dynamics and stays
frozen at its initial overlap.

## Observables

| # | Observable | Predicted range | Basis |
|---|---|---|---|
| 9  | 4-spinor `\|<u\|v>\|` sustained, mean of last 5 Coxeter periods | **0.49 ± 0.03** across ≥10 random initial states; min trial ≥ 0.25; max trial ≤ 0.65 | Cirq 20-trial sweep at p_depol = 0.005 (see `cirq/run_p4s_cirq.py`) |
| 10 | 2-spinor control drift from initial overlap (mean of all periods – initial) | **< 0.05** across ≥10 random initial states | Cirq 20-trial sweep at p_depol = 0.005 (see `cirq/run_p4s_cirq.py`) |

## Falsification conditions

1. **Observable 9 fail.** 4-spinor mean `|<u|v>|` of last 5 periods `< 0.25`
   across all initial states — tesseract does not sustain internally, the
   self-sustaining threshold sits above 4 qubits per merkabit (test shifts
   to 8-spinor / octeract).
2. **Observable 10 fail.** 2-spinor drift `> 0.10` under no-drive conditions
   — the 2-spinor is not simply frozen; either the control circuit has hidden
   dynamics, or the freezing prediction is wrong.

## Evidence basis (pre-hardware)

Three independent simulation stacks cross-validated at Willow- and
Eagle-realistic per-2q-gate depolarizing rate p ≈ 0.005:

| Simulator | 4-spinor mean ± std (last 5) | Trial range | 2-spinor drift (max) |
|-----------|------------------------------|-------------|----------------------|
| Cirq (uniform depol) | **0.494 ± 0.008** | [0.476, 0.507] | 0.015 |
| Qiskit Aer (uniform depol) | **0.483 ± 0.007** | [0.470, 0.492] | 0.019 |
| Qiskit Aer + FakeSherbrooke (Eagle r3 calibrated T₁ / T₂ / ε_gate from IBM production calibration) | **0.441 ± 0.025** | [0.389, 0.502] | 0.043 |

All 60 trials land inside the predicted [0.30, 0.65] band. The attractor is
noise-*stabilised*, not noise-fragile: at ideal p=0 the across-trial std is
~0.12 (10 periods is insufficient for unitary convergence), but at realistic
p ≥ 0.002 the std collapses to ~0.01 and all trials concentrate near the
attractor. The 2-spinor drift stays below the falsifier threshold at every
noise level tested.

See `results/cross_validation.md` for the full sweep table and evidence JSONs.

## Resource budget

- **4-spinor circuit:** 4 data qubits + 1 ancilla = 5 qubits. 10 snapshots
  per trial × 20 trials × 4,096 shots = 819k shots. Deep circuit (~120
  internal steps × 6 SU(4) gate equivalents = ~720 two-qubit-gate equivalents
  per run). On Willow this compiles against the PhXZ optimiser; on IBM this
  transpiles to Eagle r3's native basis with ~300–600 CX/ECR per run.
- **2-spinor control:** 1+1 data qubits + 1 ancilla = 3 qubits. Short circuit
  (state prep + SWAP test = ~5 ops). Identity evolution by construction; no
  internal drive.
- **Total QPU time:** under 1 hour at typical superconducting shot rates.

## Commitments

- Raw counts and job identifiers from any hardware run will be committed to
  this repository within 48 h of receipt, prior to any analysis.
- The Fano-factor-analogue `|<u|v>|` estimator is the one in `cirq/run_p4s_cirq.py`
  and `qiskit/run_p4s_aer.py` at pre-registration commit SHAs; no modification
  to the estimator will be applied post-hoc.
- No error mitigation, readout correction, or post-selection will be applied.

## Interpretation of partial passes

- **Observable 9 PASS, Observable 10 PASS.** The architecture has crossed the
  self-sustaining threshold; coherent ternary dynamics without external control.
- **9 FAIL, 10 PASS.** 2-spinor freezing confirmed but 4-spinor does not
  sustain — threshold lies above 4 qubits. Test extends to 8-spinor (octeract,
  `|C|` ~ 1/3 per Paper 6 memory), 16 physical qubits per unit.
- **9 PASS, 10 FAIL.** The claimed 2-spinor freezing is wrong; something else
  is driving the 2-spinor under the "no-drive" protocol. Control circuit needs
  redesign.
- **9 FAIL, 10 FAIL.** Both claims broken; the self-sustaining interpretation
  of Level 5 does not translate to circuit execution in its current form. The
  pipeline result needs re-examination.

All four outcomes are scientifically valuable; only the first confirms the
framework's central hardware claim.
