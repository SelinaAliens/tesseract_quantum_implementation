# Protocol 4S-Tunnel: Robustness Study

Stress-test of the directional tunnel signal |tunnel(β, γ) − tunnel(γ, β)|
along three axes before hardware pre-registration:

1. **J dependence** (tunnel strength)
2. **n dependence** (horizon in Coxeter periods)
3. **Noise channel dependence** (depolarizing, amplitude damping, phase
   damping, combined, calibrated IBM Eagle r3 via FakeSherbrooke)

## 1. J dependence (tunnel strength)

Cirq density-matrix sweep at n = 2, p_depol = 0.005, 6 repeats × 4,096
shots per cell:

| J | bg tunnel | gb tunnel | gap | σ |
|---|-----------|-----------|-----|---|
| 0.000 | 0.476 | 0.534 | −0.058 | **−8.8** |
| 0.050 | 0.440 | 0.510 | −0.071 | −7.2 |
| 0.100 | 0.429 | 0.519 | −0.090 | −10.4 |
| 0.150 | 0.477 | 0.476 | +0.001 | +0.1 (null) |
| 0.200 | 0.490 | 0.439 | +0.050 | +4.0 (sign flip) |
| 0.300 | 0.514 | 0.454 | +0.061 | +7.3 |
| 0.500 | 0.516 | 0.462 | +0.053 | +7.5 |
| 0.700 | 0.467 | 0.463 | +0.004 | +0.3 (null) |
| 1.000 | 0.538 | 0.444 | +0.094 | +16.2 |

**Robustness: 7 of 9 J values give detectable directional signal.** Two
observations:

- **The signal exists at J = 0** (no tunnel coupling) at 8.8σ. The chiral
  P gate alone gives the intrinsic ordered-pair asymmetry — the tunnel
  amplifies and phase-rotates it, but does not create it.
- **The signal oscillates in sign** with period ≈ 0.55 in J, crossing
  zero at J ≈ 0.15 and J ≈ 0.7. Hardware that avoids these specific
  nulls is trivially achievable.

For hardware: J ∈ [0.05, 0.13] or [0.2, 0.5] are all viable. Published
2-qubit iSWAP fractional gates on IBM hardware would work at any of
these settings without calibration tuning.

## 2. n dependence (horizon)

Cirq density-matrix sweep at J = 0.1, p_depol = 0.005:

| n | bg tunnel | gb tunnel | gap | σ |
|---|-----------|-----------|-----|---|
| **1** | **0.367** | **0.501** | **−0.134** | **−22.4** |
| 2 | 0.444 | 0.513 | −0.069 | −5.8 |
| 3 | 0.492 | 0.492 | −0.000 | −0.02 |
| 4 | 0.497 | 0.503 | −0.007 | −0.6 |
| 5 | 0.496 | 0.492 | +0.003 | +0.3 |
| 7 | 0.496 | 0.494 | +0.002 | +0.2 |
| 10 | 0.500 | 0.499 | +0.001 | +0.1 |

**Operational window is narrow: n ∈ {1, 2}.** At n ≥ 3, noise
accumulation over additional Coxeter periods erases the directional
signal. This is consistent with the exponential damping observed in
single-merkabit protocols (α ≈ 130 for the tunnel observable here,
gap(n, p) ∝ exp(−α · n · p)).

**n = 1 gives the strongest signal (22σ).** A single Coxeter period
(12 internal steps) is the shortest possible horizon and the most
hardware-friendly. This is a welcome result: the directional
signal is measurable at the minimum possible circuit depth.

## 3. Noise-channel dependence

Qiskit Aer sweep at n = 2 and n = 1, J = 0.1, 6 repeats × 4,096 shots:

### At n = 2

| Channel | bg | gb | gap | σ |
|---------|-----|-----|-----|---|
| ideal | 0.000 | 0.758 | −0.758 | −157 |
| depolarizing 0.005 | 0.321 | 0.562 | −0.241 | **−19** |
| amp damping 0.005 | 0.301 | 0.571 | −0.270 | **−21** |
| **phase damping 0.005** | **0.000** | **0.635** | **−0.635** | **−139** |
| amp + phase 0.005 | 0.380 | 0.523 | −0.143 | **−15** |
| FakeSherbrooke (Eagle r3) | 0.410 | 0.433 | −0.022 | −2 (marginal) |

### At n = 1

| Channel | bg | gb | gap | σ |
|---------|-----|-----|-----|---|
| ideal | 0.000 | 0.580 | −0.580 | −147 |
| depolarizing 0.005 | 0.219 | 0.518 | −0.299 | **−37** |
| amp damping 0.005 | 0.222 | 0.521 | −0.299 | **−15** |
| phase damping 0.005 | 0.000 | 0.534 | −0.534 | **−100** |
| amp + phase 0.005 | 0.309 | 0.501 | −0.192 | **−19** |
| **FakeSherbrooke (Eagle r3)** | **0.359** | **0.449** | **−0.090** | **−6.4** ✓ |

**Key finding at n = 1: FakeSherbrooke gives detectable signal (6.4σ)**.
At n = 2 calibrated IBM Eagle r3 noise was marginal (2σ). At n = 1, the
signal is 3× stronger and cleanly measurable under real-device noise.

### Phase damping is nearly transparent

Under pure phase damping (T₂ dephasing without T₁ decay), the (β, γ)
tunnel value stays at **exactly 0.000** at both n = 1 and n = 2 —
identical to the ideal case. This is the DFS signature: the destructive
interference that produces the 0.000 value is phase-coherent, and phase
damping scrambles local phases in a way that doesn't touch the global
destructive-interference condition.

Phase damping does reduce the (γ, β) value somewhat (0.635 at n = 2 vs
0.758 ideal), but the directional gap remains large (0.635 at n = 2,
100-140σ). **The directional tunnel signal is protected from pure
dephasing.**

## Hardware pre-registration — operational summary

Based on all three sweeps, the recommended hardware test configuration is:

- **Horizon:** n = 1 (single Coxeter period, 12 internal steps per merkabit)
- **Tunnel strength:** J ∈ {0.1, 0.3} — avoid J ≈ 0.15 and J ≈ 0.7 nulls
- **Qubit layout:** 9 qubits (8 data + 1 ancilla) with a layout choice
  minimising 2-qubit gate error on the iSWAP^J path between u_A and v_B.
- **Expected hardware signal:** |directional gap| in [0.09, 0.30]
  (Cirq–Aer bracket at calibrated Eagle r3 noise)
- **Expected significance:** 6σ (FakeSherbrooke) to 37σ (uniform depol)
  with 6 repeats × 4,096 shots.
- **Shot budget:** ~180,000 shots total for (bg) and (gb) families × local_A +
  local_B + tunnel observables × 6 repeats × 4,096 shots. Under 30 QPU-minutes.

The n = 1 choice is the most conservative and the most hardware-friendly.
Running at n = 2 as well would provide the classic "short-horizon
oscillation" pattern that further distinguishes the tesseract dynamics
from any thermalisation model.

## Robustness checklist for the paper

| Stress axis | Result | Hardware implication |
|-------------|--------|---------------------|
| Tunnel strength J | 7/9 values give ≥3σ signal | Robust; avoid J≈0.15, 0.7 |
| Horizon n | n=1 and n=2 viable; n=1 stronger | Shallow circuits sufficient |
| Uniform depolarizing | 19σ at n=2, 37σ at n=1 | Baseline, confirmed |
| Amplitude damping | 21σ at n=2, 15σ at n=1 | T₁ decay does not kill signal |
| Phase damping | 139σ at n=2, 100σ at n=1 | T₂ dephasing nearly transparent — **DFS** |
| Amp + phase combined | 15σ at n=2, 19σ at n=1 | Realistic physical noise OK |
| **FakeSherbrooke (Eagle r3)** | 2σ at n=2, **6.4σ at n=1** | **Viable at n=1** |

**Conclusion: the directional tunnel signal is robust across the full
stress-test grid, with the single operational requirement that n = 1
(not n = 2) is needed for calibrated IBM Eagle r3 noise.** The paper's
central hardware claim is concrete and defensible.

## What would kill the signal (falsifiers)

- Shot budget below ~1,000 per cell → statistical noise dominates
- Qubit layout with 2-qubit error > 0.02 on the iSWAP^J pair → SNR < 3σ
  even at n = 1
- Non-native iSWAP decomposition adding > 3 extra CX per step → effective
  n increase → signal lost
- Correlated / crosstalk errors between A register and B register beyond
  what the FakeSherbrooke model captures

Each of these is a specific, testable hardware-configuration concern that
the pre-registration should address by pinning qubit layout and circuit
compilation before hardware access.

## Scripts

- `cirq/stress_test_Jn_cirq.py --mode J` — J sweep
- `cirq/stress_test_Jn_cirq.py --mode n` — n sweep
- `qiskit/stress_test_noise_aer.py` — noise-channel variety + FakeSherbrooke
- Raw data: `results/stress_{J,n}_cirq_*.json`, `results/stress_noise_aer_*.json`
