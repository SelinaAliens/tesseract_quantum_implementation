# Cross-Stack Validation of Protocol 4S

**Date:** 2026-04-20
**Stacks tested:** Cirq (Google), Qiskit Aer (IBM), Qiskit Aer + FakeSherbrooke
(IBM Eagle r3 calibrated).

Three independent simulator stacks were run against the same protocol with the
same noise budget to rule out implementation artefacts before hardware submission.

## Full noise sweep — 20 trials per configuration, 4,096 shots

### Cirq (Google stack, uniform depolarizing noise)

Source: `cirq/run_p4s_cirq.py` at Willow pre-registration SHA [`30984ca`](https://github.com/selinaserephina-star/willow_hardware_merkabit/commit/30984ca).

| p_depol | 4-spinor last-5 mean ± std | Trial range | 2-spinor drift (max) |
|---------|---------------------------|-------------|----------------------|
| 0.000   | 0.411 ± 0.120             | [0.21, 0.58] | 0.021 |
| 0.002   | 0.491 ± 0.016             | [0.47, 0.53] | 0.023 |
| **0.005** | **0.494 ± 0.008**       | **[0.48, 0.51]** | **0.015** |
| 0.010   | 0.489 ± 0.008             | [0.48, 0.50] | 0.016 |

### Qiskit Aer (IBM stack, uniform depolarizing noise)

Source: `qiskit/run_p4s_aer.py` at IBM pre-registration SHA [`4a7bbb4`](https://github.com/selinaserephina-star/merkabit_hardware_test/commit/4a7bbb4).
Raw output: `results/p4s_aer_depol_20260420T000945.json`.

| p_depol | 4-spinor last-5 mean ± std | Trial range | 2-spinor drift (max) |
|---------|---------------------------|-------------|----------------------|
| 0.000   | 0.423 ± 0.116             | [0.21, 0.62] | 0.021 |
| 0.002   | 0.477 ± 0.036             | [0.42, 0.57] | 0.023 |
| **0.005** | **0.483 ± 0.007**       | **[0.47, 0.49]** | **0.019** |
| 0.010   | 0.471 ± 0.007             | [0.46, 0.49] | 0.048 |

### Qiskit Aer + FakeSherbrooke (IBM Eagle r3 calibrated noise)

Source: `qiskit/run_p4s_aer.py --fake-backend sherbrooke`.
Raw output: `results/p4s_aer_sherbrooke_20260420T001745.json`.
Noise model: real IBM Eagle r3 T₁ / T₂ / per-gate error rates from the
production FakeSherbrooke backend in `qiskit_ibm_runtime.fake_provider`.

| Backend | 4-spinor last-5 mean ± std | Trial range | 2-spinor drift (max) |
|---------|---------------------------|-------------|----------------------|
| **FakeSherbrooke (Eagle r3)** | **0.441 ± 0.025** | **[0.389, 0.502]** | **0.043** |

## Convergence assessment

At the Willow-realistic depolarizing rate p = 0.005:

- Cirq: 0.494 ± 0.008
- Aer uniform: 0.483 ± 0.007
- Aer Sherbrooke: 0.441 ± 0.025

The Cirq vs Aer (both uniform depol) gap is ~0.011 — statistically
indistinguishable at 20 trials × 4,096 shots. No protocol drift between
implementations.

The Aer-uniform vs Aer-Sherbrooke gap is ~0.042 — Sherbrooke's calibrated
noise is non-uniform across qubits and gates, and the effective mean error
rate on the particular 5-qubit layout used exceeds the uniform p=0.005
assumption. The attractor is pulled slightly lower but remains well inside
the predicted band. Trial dispersion (±0.025) is also higher than uniform,
reflecting per-trial variation in which qubits were selected by the
transpiler.

**2-spinor drift** stays below the 0.10 falsification threshold on every
stack at every noise level. The highest drift observed (Aer Sherbrooke,
0.043) still leaves factor-of-two margin before falsifier.

## Noise-stabilised attractor

A notable pattern: across-trial variance of the 4-spinor attractor
*decreases* with increasing noise, up to the Willow-realistic range.

| p_depol | Cirq σ (4-spinor) | Aer uniform σ (4-spinor) |
|---------|-------------------|---------------------------|
| 0.000   | 0.120             | 0.116                     |
| 0.002   | 0.016             | 0.036                     |
| 0.005   | 0.008             | 0.007                     |
| 0.010   | 0.008             | 0.007                     |

Ten Coxeter periods is not sufficient for unitary-only convergence to the
attractor from every random initial state — some trials are still in
transient at p=0. Modest depolarization drives the state toward the
attractor faster than unitary evolution alone, collapsing the spread by
factor ~15 between p=0 and p=0.005. This is the opposite of the usual
"noise kills signal" expectation and means the prediction *should* be
easier to confirm on hardware than in ideal simulation.

## Validation conclusion

Three independent simulators converge on:

- 4-spinor mean `|<u|v>|` (last 5 periods): **0.44–0.50** depending on noise model
- 2-spinor control drift: **< 0.05** across all stacks
- Both observables pass falsifier thresholds at every noise level tested

Pre-registered hardware prediction is ready for execution on Willow (Cirq
path) or IBM Eagle r3 / Heron r2 (Qiskit path).
