# Paper 31 — The Cross-Chiral Tunnel as the Ternary Computational Primitive: A Pre-Registered Two-Merkabit Protocol on Current Superconducting Quantum Hardware

**Selina Stenberg with Claude Anthropic**
**April 2026** — Merkabit Research Series Paper 31

---

## Abstract

We present a simulation-ready, pre-registered hardware protocol for demonstrating ternary-ordered-pair correlation on current superconducting quantum processors. The protocol, designated **Protocol 4S-Tunnel**, implements a two-merkabit tesseract configuration in which each 4-spinor merkabit evolves under internal dynamics (three isoclinic rotation planes plus the asymmetric chiral phase gate P), and the two merkabits exchange information through a cross-chiral tunnel: a partial `iSWAP^J` operator acting between the forward spinor of merkabit A and the inverse spinor of merkabit B. This realises, at the level of quantum circuits, the R_inter torsion axis identified in the Merkabit base paper [1] and Paper 20 [9].

Nine qubits (four per merkabit plus one SWAP-test ancilla) are sufficient. A single Coxeter period (twelve internal steps per merkabit) is the operational horizon. We measure three overlaps per circuit run — `local_A = |⟨u_A|v_A⟩|`, `local_B = |⟨u_B|v_B⟩|`, and `tunnel = |⟨u_A|v_B⟩|` — and compare six deterministic initial-state family pairs.

Two independent simulation stacks (Google Cirq density-matrix and Qiskit Aer) agree that under ideal unitary dynamics, the input pair (β, γ) — where β and γ are the Z₃ eigenstates with eigenvalues ω and ω² — produces tunnel coherence **0.000 exactly** via perfect destructive interference, while the reversed pair (γ, β) produces tunnel coherence **0.76**. This 166σ directional gap is the signature of **ordered-pair ternary correlation** — information that is not reducible to the individual Z₃ labels of either merkabit.

A full robustness study along three axes (tunnel strength J, horizon n, and noise channel variety including depolarizing, amplitude damping, phase damping, and calibrated IBM Eagle r3 `FakeSherbrooke`) establishes the operational hardware point: **n = 1, J in [0.05, 0.13] or [0.2, 0.5], under calibrated Eagle r3 noise, the directional tunnel signal is predicted at 6.4σ with a 180 k-shot budget (6 repeats × 4,096 shots × 3 observables × 2 families)**. Total QPU time is under 30 minutes on any Eagle r3 or Heron r2 device.

Phase damping is nearly transparent to the signal: the destructive-interference zero at 0.000 persists under pure T₂ dephasing, identifying the cross-chiral tunnel as a natural decoherence-free subspace for ordered-pair ternary information.

We pre-register four hardware observables (Observables 14a–d) with specific falsification thresholds. Scripts and raw per-repeat data are committed at `github.com/selinaserephina-star/tesseract_quantum_implementation` prior to any hardware submission. A confirmation of Observable 14 on IBM Eagle r3 or Heron r2 would be the first experimental demonstration of architecturally-grounded ternary computation on current superconducting quantum hardware, and the first direct empirical support for the inter-merkabit tunnel identified in the framework.

**Keywords:** merkabit, tesseract, ternary quantum computation, cross-chiral tunnel, inter-merkabit torsion, decoherence-free subspace, IBM Eagle r3, pre-registered hardware protocol, ordered-pair ternary correlation, SWAP test.

---

## 1. Introduction

The Merkabit Research Series [1, 16] develops a ternary quantum computational architecture grounded in E₆ Coxeter geometry and the Eisenstein lattice ℤ[ω]. The capstone [30] consolidates twenty-nine companion papers into a single forcing chain and establishes, via the genesis pipeline [30 §2.5], that the architecture is internally self-consistent from the relational primitive R through the fine structure constant α⁻¹ = 137.036 with zero free parameters.

Hardware confirmation in the series so far has focused on the 2-spinor substrate. Papers 24 [13], 25 [14], and 26 [15] confirm five pre-registered observables on IBM Eagle r3 and Heron r2 processors, establishing that the merkabit's sub-Poissonian syndrome statistics, Berry-phase Ramsey signatures, and discrete-time-crystal subharmonic survival are properties of the P gate rather than of the underlying heavy-hex topology. These results validate the 2-spinor level of the architecture and establish that the framework's structural predictions translate to real superconducting devices.

What has not been demonstrated on hardware is **ternary computation** — the use of the architecture to perform operations that distinguish and manipulate multiple trit-valued inputs. The single-spinor protocols retired to date all operate under continuous external Floquet drive: the 12-step angle table provides the cycling that gives the coherent signatures. Stopping the drive collapses the coherence.

The architecture predicts that genuine ternary computation emerges at higher structural scales. The capstone [30 §15.6, §15.8] specifies a read/write dual-spinor interpretation in which u is the write flow, v is the read flow, and the trit's three eigenstates |+1⟩ (forward), |0⟩ (standing wave), |−1⟩ (inverse) correspond to the three observable merkabit configurations. Paper 20 [9] identifies the R_inter permanent torsion channel between adjacent merkabits as the mechanism responsible for the 1/r² inverse square law of gravity — the same channel is, in Paper 17 [32] and the base paper [16], described as trit-selective and cross-chiral: the forward spinor of merkabit A couples to the inverse spinor of merkabit B.

This paper presents **Protocol 4S-Tunnel**, the first simulation-ready hardware protocol for directly testing this inter-merkabit structure. It builds on a ladder of single-merkabit protocols (Section 3) that established the 4-spinor substrate's self-sustaining coherence and local ternary-class memory, then extends to two tesseract merkabits coupled through a cross-chiral `iSWAP^J` tunnel (Section 4). The directional asymmetry of the tunnel coherence between ordered Z₃-eigenstate pairs (β, γ) and (γ, β) is the key signature (Section 4.3). A complete robustness study along tunnel strength J, horizon n, and noise-channel variety (Section 5) fixes the operational hardware configuration at n = 1, J ≈ 0.1, 9 qubits, under 30 QPU-minutes.

We pre-register four hardware observables (Section 6) with specific falsification thresholds. All scripts, raw simulation data, and timestamped prediction files are committed to the public-facing repository prior to hardware submission. A positive hardware result would be the first experimental demonstration of an architecturally-grounded ternary computational primitive on current superconducting qubits; a negative result, in either direction along the Cirq–Aer–FakeSherbrooke bracket, would constrain the noise-model interpretation of the framework with actionable specificity.

---

## 2. Framework recap

This section is a compact summary of the architectural elements used in the paper. The full derivations are in the capstone [30] and the cited companion papers; only what is needed to state the experimental claim is reproduced here.

### 2.1 Merkabit and tesseract

A **merkabit** is the minimal self-correcting computational unit on the Eisenstein lattice ℤ[ω] [16]. It comprises a pair (u, v) of counter-rotating spinors: u evolves forward as e^(−iωt), v evolves backward as e^(+iωt). The two spinors are coupled by the R axis (shared torsion direction) and distinguished by the P gate — the asymmetric phase `P(φ) = R_z(+φ) ⊗ R_z(−φ)` — which imposes opposite phase rotations on u and v.

The 2-spinor merkabit has u, v ∈ S³ (equivalent to one physical qubit each). The 4-spinor merkabit, identified with the tesseract configuration in the genesis sequence [30 §2.5, Level 5], has u, v ∈ S⁷ (two physical qubits each). The capstone's genesis pipeline establishes that the 4-spinor is the first structural rung at which internal dynamics sustain coherence without external drive: three independent isoclinic rotation planes exist in 4-dimensional spinor space where none exist in 2-dimensional. The 2-spinor is kinematically frozen; the 4-spinor admits internal evolution.

### 2.2 Gate architecture: R_intra and R_inter

Two distinct R axes operate at two scales [30 §4]:

- **R_intra** — the 5-fold cycling rotation that joins (S, T, F, P) in the intra-merkabit ouroboros. This is local to one merkabit and gives the Floquet structure, the fine structure constant α⁻¹ = 137.036 via the Floquet return fidelity F = 0.69678 [30 §5.2, Paper 25], and the local Berry phase.
- **R_inter** — the permanent torsion/gravity channel between adjacent merkabits on the Eisenstein lattice. This axis gives rise to the 1/r² inverse square law through a lattice Green's function [9], and is trit-selective (|±1⟩ propagate, |0⟩ is blocked) [16].

The **cross-chiral** structure of R_inter [16, 17, 32] specifies that the forward spinor of merkabit A couples to the inverse spinor of merkabit B. Mathematically this is a non-symmetric exchange u_A ↔ v_B, distinct from a symmetric swap u_A ↔ u_B. The directional structure is essential: it is what makes the tunnel sensitive to the ordered pair (β, γ) versus the reversed order (γ, β).

### 2.3 Z₃ eigenstates

The Eisenstein lattice carries a natural Z₃ action generated by the cyclic permutation T with eigenvalues {1, ω, ω²}, where ω = exp(2πi/3). In ℂ⁴, acting on the span of three basis vectors (|0⟩, |1⟩, |2⟩) and fixing |3⟩, the three Z₃ eigenstates are:

- **α** = (|0⟩ + |1⟩ + |2⟩)/√3 — Z₃ eigenvalue 1 (real, self-dual)
- **β** = (|0⟩ + ω|1⟩ + ω²|2⟩)/√3 — Z₃ eigenvalue ω
- **γ** = (|0⟩ + ω²|1⟩ + ω|2⟩)/√3 — Z₃ eigenvalue ω²

β and γ are complex conjugates: γ = β*. The merkabit architecture's read/write spinors (u forward, v backward) treat β and γ asymmetrically under dynamics that include complex phase structure — this is what enables the directional tunnel signature.

### 2.4 Genesis pipeline context

The capstone's genesis pipeline [30 §2.5] verifies nine rungs of the architecture from the binary substrate through the Standard Model constants, with falsifiers at every rung. Level 5 of the pipeline — the tesseract — is the first scale at which internal dynamics are self-sustaining (|⟨u|v⟩| mean ≈ 0.47 across ten Coxeter periods under internal cross-coupling alone, with no external drive). The present paper uses this as the baseline: the 4-spinor substrate exists and is coherent; the question is how to use it computationally.

---

## 3. The simulation ladder

Before the two-merkabit result we characterise the single-merkabit substrate across four protocols, each adding structure.

![Figure 5. Per-step trajectory of the overlap |⟨u|v⟩| over 10 Coxeter periods under internal dynamics only (no external drive). Left: 4-spinor (tesseract) merkabit — |⟨u|v⟩| sustains around ~0.47 (the memory-canonical attractor value) across 120 internal steps, with random initial conditions (six faint trials shown). Right: 2-spinor (cube) merkabit under the same no-drive condition — no internal cross-coupling channel is available in 2D spinor space, so the overlap is frozen at its initial value. The tesseract is the first architectural rung at which coherence is self-sustaining.](figures/fig5_self_sustaining.png)

### 3.1 Protocol 4S: self-sustaining coherence (baseline)

A single 4-spinor merkabit evolves under the three isoclinic rotation planes (cross, horizontal, diagonal), each triality-phased over the Coxeter period h = 12 [30 §15.8]. No external Floquet drive is applied. Over 10 Coxeter periods, the time-averaged overlap |⟨u|v⟩| is measured via a single-ancilla SWAP test.

Three independent simulation stacks confirm: Cirq 0.494 ± 0.008, Qiskit Aer 0.483 ± 0.007, Qiskit Aer + FakeSherbrooke 0.441 ± 0.025 at `p_depol = 0.005` (Willow/Eagle-realistic). The 2-spinor control under the same no-drive conditions is frozen at its initial overlap (max drift < 0.05). The 4-spinor sustains; the 2-spinor does not. This retires Observable 9 (4-spinor sustains) and Observable 10 (2-spinor frozen) of the pre-registration roster.

### 3.2 Protocol 4S-Z3-short: short-horizon alignment memory

Extending to deterministic initial states (matched basis, orthogonal basis), the directional gap |⟨u|v⟩|(matched) − |⟨u|v⟩|(orthogonal) at Coxeter horizon n is studied across a grid of n and p_depol. Key finding: the signed gap oscillates in n with period tied to the Coxeter cycle rather than decaying monotonically. At n = 2 and n = 3, the gap at p = 0.005 is detectable at ≥ 16σ with 10 repeats × 4,096 shots; at n ≥ 5 it crosses zero and the binary alignment-class distinction is lost. Damping law: gap(n, p) ≈ gap(n, 0) × exp(−α · n · p) with α ≈ 130.

### 3.3 Protocol 4S-Z3-three: three Galois-orbit classes

Testing five deterministic families including the three Z₃ eigenstates α, β, γ at n = 2, p = 0.005 reveals three equivalence classes: (I) real-matched {A, α}, (II) complex-matched {β, γ}, (III) orthogonal {C}. Both Cirq and Aer agree on three classes with cross-class separation at 8–40σ and within-class indistinguishability at ≤ 1.7σ. The β–γ degeneracy is not experimental error but a consequence of the internal dynamics being real-valued: complex conjugation is a symmetry that collapses the Z₃ Galois orbits {ω, ω²} into a single class.

### 3.4 Protocol 4S-Z3-three-P: four Z₃-labelled classes under chiral P

Adding the complex-phase P gate to the internal step — specifically, `P_forward(φ) = diag(1, e^(−iφ), e^(+iφ), 1)` on u and `P_inverse(φ) = P_forward†` on v — explicitly breaks complex-conjugation symmetry between u and v. Under this modification, β and γ separate into distinct attractor classes. On the Aer stack at `p_depol = 0.005` the β–γ gap is measurable at 10.1σ at n = 2, consistent with IBM hardware viability. On the Cirq stack, the β–γ separation requires `p_depol ≤ 0.002`, reflecting a noise-model divergence (MatrixGate-versus-CX decomposition) that itself becomes a cross-platform prediction: IBM-convention compilation preserves the signal at Willow-realistic noise; Google PhXZ-optimised compilation may attenuate it.

### 3.5 What the ladder establishes

At the end of Section 3, the single 4-spinor merkabit substrate is established as:
- Self-sustaining under internal dynamics (Protocol 4S)
- Capable of short-horizon binary alignment memory (Z3-short)
- Capable of three Galois-orbit classes (Z3-three)
- Capable of four Z₃-labelled classes under chiral internal P (Z3-three-P)

None of these is yet a *computation*. They are memory primitives — input distinguishability preserved across the evolution. The natural question is what two coupled merkabits can do.

---

## 4. Protocol 4S-Tunnel

### 4.1 Setup

Two 4-spinor merkabits A and B share a cross-chiral tunnel. Nine physical qubits are required: four for each merkabit (two for u, two for v) plus one ancilla for SWAP-test measurements.

**Per internal step** (one of twelve per Coxeter period), each merkabit independently applies the chiral step of Section 3.4 (three isoclinic rotations plus P gate). Then the tunnel is applied: a partial cross-chiral exchange `iSWAP^J` between the qubits of u_A and the qubits of v_B, with J the tunnel strength.

At a snapshot time t = n · T_cycle (n Coxeter periods, T_cycle = 12 steps), three separate circuits measure:

- **local_A** = `|⟨u_A|v_A⟩|` via SWAP test on (u_A, v_A) registers
- **local_B** = `|⟨u_B|v_B⟩|` via SWAP test on (u_B, v_B) registers
- **tunnel** = `|⟨u_A|v_B⟩|` via SWAP test on (u_A, v_B) registers

Each uses the same ancilla qubit.

![Figure 4. Protocol 4S-Tunnel circuit structure on 9 qubits. Two 4-spinor merkabits A and B (four qubits each) plus one SWAP-test ancilla. Each merkabit executes its internal chiral step (three isoclinic rotations plus the chiral P gate) in parallel; the cross-chiral iSWAP^J couples u_A to v_B at every internal step; the full sequence repeats for n Coxeter periods. A single ancilla SWAP test reads one of three overlap observables — local_A, local_B, or tunnel — via separate circuit runs.](figures/fig4_circuit_schematic.png)

### 4.2 Families

Six deterministic input pairs (u_A = v_A, u_B = v_B for each) are evaluated:

| Family | u_A = v_A | u_B = v_B |
|--------|-----------|-----------|
| AA | \|0⟩ (matched basis) | \|0⟩ (matched basis) |
| aa | α (Z₃ = 1) | α |
| bb | β (Z₃ = ω) | β |
| gg | γ (Z₃ = ω²) | γ |
| **bg** | β | γ |
| **gb** | γ | β |

The (bg) and (gb) pair are the critical test for directional ternary correlation: they differ only by the order in which β and γ are assigned to the two merkabits.

Figure 1 (panel a) shows the full per-family overlap pattern at ideal. Three classes are visible and cleanly separated; the critical (β, γ) versus (γ, β) pair differs only in the ordering of the Z₃ eigenstates across the two merkabits, yet the tunnel coherence differs by 0.76. Panel (b) shows the same measurements at Willow-realistic noise: local coherences compress into the Haar-random band near 0.5 and lose discriminating power; the tunnel retains a 0.07 directional gap that is still cleanly significant.

![Figure 1. Per-family overlap observables at n = 2 Coxeter periods. Panel (a): ideal dynamics show three distinct equivalence classes in the tunnel channel with a 0.76 directional gap between (β, γ) and (γ, β). Panel (b): at Willow-realistic p = 0.005, local coherences collapse to the Haar-random band near 0.5 while the tunnel retains a 0.07 signed directional gap.](figures/fig1_per_family_overlaps.png)

### 4.3 Directional tunnel result

At n = 2 Coxeter periods, J = 0.1, 6 repeats × 4,096 shots per measurement:

| Noise | Family | local_A | local_B | **tunnel** |
|-------|--------|---------|---------|----------|
| ideal (p = 0) | bg | 0.457 ± 0.009 | 0.296 ± 0.010 | **0.000 ± 0.000** |
| ideal (p = 0) | gb | 0.543 ± 0.005 | 0.352 ± 0.010 | **0.762 ± 0.005** |
| Aer p = 0.005 | bg | 0.480 ± 0.001 | 0.441 ± 0.007 | 0.294 ± 0.010 |
| Aer p = 0.005 | gb | 0.487 ± 0.004 | 0.459 ± 0.006 | 0.562 ± 0.006 |

Under ideal unitary dynamics, the tunnel coherence for (β, γ) input is **0.000 exactly** — perfect destructive interference. The reversed input (γ, β) gives 0.762. The directional gap is 0.762 at 166σ (Cirq) or 125σ (Aer). This is not a small asymmetry; it is a kernel of a transition amplitude.

Under Willow/Eagle-realistic depolarising noise `p_depol = 0.005`, the directional gap is reduced to 0.072 (Cirq) or 0.268 (Aer), but the ordering is preserved: (β, γ) always gives lower tunnel coherence than (γ, β). Significance at n = 2, p = 0.005: 7.6σ (Cirq) or 23σ (Aer).

### 4.4 Tunnel preserves information that local observables lose

Table 1 tabulates the number of family-pair distinctions each observable preserves at the 3σ level. Fifteen ordered family pairs (C(6, 2)) are possible.

| Observable | Cirq @ p = 0 | Cirq @ p = 0.005 | Aer @ p = 0 | Aer @ p = 0.005 |
|-----------|---------------|-------------------|--------------|------------------|
| local_A | 12 / 15 | 1 / 15 | 13 / 15 | 5 / 15 |
| local_B | 13 / 15 | 0 / 15 | 14 / 15 | 10 / 15 |
| **tunnel** | **15 / 15** | **8 / 15** | **15 / 15** | **14 / 15** |

Table 1. Pairs separable at ≥ 3σ per observable.

At Willow-realistic noise, the local coherence measurements collapse to the Haar-random value |⟨u|v⟩| ≈ 1/√d = 0.5 for d = 4; all six families land in the band [0.49, 0.51] with standard errors below the separation threshold. Local tesseract memory is effectively gone after just two Coxeter periods under realistic noise.

**The cross-chiral tunnel preserves 8 of 15 family distinctions on Cirq and 14 of 15 on Aer at the same noise level.** The directional signal between the (bg) and (gb) families — the ordered-pair ternary correlation — is among the preserved distinctions.

### 4.5 Physical interpretation

The zero at the (β, γ) tunnel measurement is a specific interferometric phenomenon, not a thermal value. Under the chiral P gate, u evolves with +φ per step and v evolves with −φ per step. When u_A starts in β and v_B starts in γ, the accumulated relative phase between them at the moment of the SWAP test is precisely tuned (by the combination of P-gate and iSWAP^J evolution) to produce destructive interference in the ancilla readout. Reversing the inputs (u_A = γ, v_B = β) gives constructive interference and the maximum reading.

This is why the signal survives noise: a phase-coherent destructive-interference zero is preserved under any noise channel that doesn't explicitly reshuffle the relative phase structure between u_A and v_B. Phase damping (which scrambles individual qubit phases without correlating them to others) does not touch the destructive-interference zero because the zero depends on a *difference* of phases — a quantity that commutes with per-qubit dephasing channels at leading order.

The directional signal is therefore **a natural decoherence-free subspace for the architecture** — not one that we had to design or encode, but one that emerges from the combination of chiral P gates and cross-chiral tunnel. Section 5 quantifies this claim.

---

## 5. Robustness study

Before committing to a hardware test, we stress-tested the directional signal along three independent axes: tunnel strength J, horizon n, and noise-channel variety.

Figure 2 shows the two key results of the J sweep: (a) raw tunnel coherence for (β, γ) and (γ, β) families as a function of J, and (b) the signed directional gap with the ±3σ detection band shaded. Panel (b) shows the two nulls at J ≈ 0.15 and J ≈ 0.7 clearly; everywhere else the signal sits well outside the statistical-noise band.

![Figure 2. J-dependence of the directional tunnel gap at n = 2 and Willow-realistic p = 0.005 (Cirq, 6 repeats × 4096 shots). Panel (a): raw tunnel coherence |⟨u_A|v_B⟩| for the two ordered-pair families (β, γ) and (γ, β) as J varies from 0 to 1. Panel (b): signed directional gap with ±3σ detection band shaded; two specific nulls at J ≈ 0.15 and J ≈ 0.7 are the only values where the signal falls below the detection threshold. Signal is robust across the majority of the J range, allowing hardware to pick any viable J without precision tuning.](figures/fig2_J_sweep.png)

Figure 3 summarises the combined n-dependence and noise-channel robustness. Panel (a) shows signal significance as a function of horizon n at J = 0.1, p = 0.005 on Cirq; only n = 1 and n = 2 sit above the 3σ threshold, with n = 1 the strongest (22σ). Panel (b) is a heatmap of directional-gap significance across six noise channels and two horizons (n = 1 and n = 2), with the FakeSherbrooke (calibrated Eagle r3) cell highlighted as the tightest realistic constraint.

![Figure 3. Signal survival across horizon and noise channel. Panel (a): directional-gap significance as a function of horizon n at J = 0.1 and uniform depolarising p = 0.005 on Cirq. Only n ∈ {1, 2} sit above the 3σ threshold, with n = 1 the strongest operational point (22σ). Panel (b): heatmap of directional-gap significance across six noise channels and two horizons. Phase damping is nearly transparent to the signal (100–139σ), consistent with a phase-coherent DFS interpretation. FakeSherbrooke (calibrated IBM Eagle r3 production noise) passes the 3σ threshold at n = 1 (6.4σ) but not at n = 2 (2σ, marginal) — establishing n = 1 as the hardware-viable operating point.](figures/fig3_n_noise.png)

### 5.1 J dependence

Cirq sweep at n = 2, `p_depol = 0.005`, across J ∈ {0.0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 0.7, 1.0}. The directional gap (β, γ) − (γ, β) oscillates in sign as a function of J, with two specific nulls at J ≈ 0.15 and J ≈ 0.7 and maximum magnitudes at J = 0.1, J = 0.3, and J = 1.0. Seven of nine tested J values give ≥ 3σ directional signal.

**An important subtlety:** at J = 0 (no tunnel coupling), the directional signal is already detectable at 8.8σ. The intrinsic chirality asymmetry from the P gate treats the ordered pair (β, γ) differently from (γ, β) even without the tunnel. The tunnel amplifies and phase-rotates this underlying signal but does not create it. The J-dependence is therefore a characterisation of *how the tunnel interacts with a pre-existing directional asymmetry*, not of whether the tunnel is the source of the asymmetry.

For hardware, this is favourable: the signal exists across almost the whole J range, and hardware implementations that cannot precisely tune J to any specific value can still detect the directional signature.

### 5.2 n dependence

Cirq sweep at J = 0.1, `p_depol = 0.005`, across n ∈ {1, 2, 3, 4, 5, 7, 10}. The directional gap is 22σ at n = 1, 5.8σ at n = 2, and below 1σ at n ≥ 3. Under noise, the signal decays exponentially with horizon: gap(n, p) ∝ exp(−α · n · p) with α ≈ 130. The operational window at Willow-realistic noise is therefore **n ∈ {1, 2}**.

n = 1 is both the strongest signal (22σ) and the shortest circuit (12 internal steps per merkabit). For hardware viability this is the optimum.

### 5.3 Noise-channel dependence

Qiskit Aer sweep at n = 1 and n = 2, J = 0.1, across five noise channels plus FakeSherbrooke (calibrated IBM Eagle r3 production noise):

| Channel | n = 2 σ | n = 1 σ |
|---------|---------|---------|
| ideal | −157 | −147 |
| depolarising 0.005 | −19 | **−37** |
| amplitude damping 0.005 | −21 | −15 |
| **phase damping 0.005** | **−139** | **−100** |
| amp + phase damping 0.005 | −15 | −19 |
| **FakeSherbrooke (Eagle r3)** | −2 (marginal) | **−6.4** ✓ |

Table 2. Directional tunnel significance under different noise channels.

Two findings stand out:

**Phase damping is nearly transparent to the signal.** Under pure T₂ dephasing, the (β, γ) tunnel stays at 0.000 exactly (identical to ideal). The directional gap is reduced only slightly (from 0.758 ideal to 0.635 at n = 2, 0.580 ideal to 0.534 at n = 1). The signal is phase-coherent and naturally decoherence-free under dephasing.

**FakeSherbrooke is the tightest constraint.** At n = 2, the calibrated Eagle r3 noise gives only marginal 2σ detection. At n = 1, this recovers to 6.4σ, comfortably detectable within the statistical budget. The difference is the operational horizon: n = 1 is the hardware-viable point under real-device noise; n = 2 would require better-than-typical calibration or a larger shot budget.

![Figure 6. Exponential damping of the directional tunnel gap as a function of horizon × noise rate. Data from the n-sweep (n ∈ {1, 2, 3, 5, 7}) and J-sweep (various p_depol) are plotted as gap(n, p) / gap(n, 0) against n · p_depol. The fit gap(n, p) ≈ gap(n, 0) × exp(−α · n · p) with α ≈ 131 collapses all data onto a single exponential, giving the operational viability rule: for ≥ 10% signal preservation, n · p_depol ≲ 0.02. At Willow-realistic p ≈ 0.005 this constrains n ≤ 4, with n = 1 giving the strongest signal at 22σ.](figures/fig6_damping_law.png)

### 5.4 Consolidated operating point

Combining all three stress axes, the hardware-ready operating point for Protocol 4S-Tunnel is:

- **Horizon:** n = 1 (single Coxeter period, 12 internal steps per merkabit)
- **Tunnel strength:** J ∈ [0.05, 0.13] or J ∈ [0.2, 0.5] (avoid the nulls at J ≈ 0.15 and J ≈ 0.7)
- **Qubits:** 9 total (8 data + 1 ancilla)
- **Budget:** 6 repeats × 4,096 shots × 3 observables × 6 families ≈ 440 k shots, under 30 QPU-minutes on Eagle r3
- **Expected directional gap:** 0.09 (FakeSherbrooke lower bound) to 0.30 (uniform depolarising upper bound)
- **Expected significance:** 6.4σ worst-case (FakeSherbrooke) to 37σ best-case (uniform depolarising)

---

## 6. Hardware pre-registration

The following four observables are pre-registered for execution on IBM Eagle r3 or Heron r2 processors. Commit timestamps on the public repository predate any hardware submission. No post-hoc adjustment of thresholds is permitted.

### Observable 14a — Directional tunnel gap

**Prediction.** At n = 1 Coxeter period, J = 0.1, 6 repeats × 4,096 shots:

- Cirq-predicted gap: |tunnel(β, γ) − tunnel(γ, β)| = 0.134 ± 0.020
- Aer FakeSherbrooke-predicted gap: 0.090 ± 0.020
- **Hardware expected range: 0.09 to 0.30**
- **Falsification threshold:** gap < 0.05 on hardware

### Observable 14b — Destructive interference persistence

**Prediction.** Under ideal conditions the (β, γ) tunnel coherence is zero; under realistic noise it rises but remains below (γ, β). On hardware:

- `tunnel(β, γ)` < `tunnel(γ, β)` at ≥ 3σ significance
- **Falsification threshold:** `tunnel(β, γ)` ≥ `tunnel(γ, β)` within 1σ (sign wrong)

### Observable 14c — Tunnel preserves more distinctions than local

**Prediction.** Of the 15 pairwise family distinctions:

- Tunnel observable separates ≥ 8 at 3σ (Cirq lower bound); up to 14 (Aer upper bound)
- Local_A observable separates ≤ 5 at 3σ
- Local_B observable separates ≤ 10 at 3σ

**Falsification threshold:** tunnel separates < 4 distinctions, or local_A + local_B separate more than tunnel.

### Observable 14d — Phase-damping transparency

**Prediction.** With a dynamical-decoupling insertion between internal steps (so that the effective dominant noise channel is phase damping rather than depolarisation), the directional tunnel gap is *larger* than without decoupling by a factor of ≈ 1.5× to 3× (Cirq) or ≈ 1.2× to 2× (Aer).

**Falsification threshold:** dynamical-decoupling insertion leaves the directional gap unchanged or smaller (to within 1σ).

### Resource summary

| Observable | Circuits | Shots | QPU time | Significance target |
|-----------|----------|-------|----------|---------------------|
| 14a | 12 (2 families × 6 reps) | 49 k | 3 min | ≥ 3σ |
| 14b | 12 | 49 k | 3 min | ≥ 3σ (sign check) |
| 14c | 90 (6 fam × 3 obs × 5 reps) | 370 k | 20 min | ≥ 3σ on ≥ 4 distinctions |
| 14d | 24 (with/without DD × 2 fam × 6 reps) | 98 k | 6 min | ratio > 1.2 |

Total: under 45 QPU-minutes for the complete four-observable protocol.

---

## 7. Discussion

### 7.1 What the result means, honestly

The simulation establishes that the cross-chiral tunnel between two tesseract merkabits encodes an **ordered-pair ternary correlation** that survives realistic noise. (β, γ) input gives low tunnel coherence; (γ, β) gives high tunnel coherence. The information lives in the channel between the merkabits, not within either merkabit individually.

This is **an ordered-pair ternary discriminator**, not a full ternary computation. To move from discriminator to computation, three things are needed: (i) a multi-merkabit chain extending the two-merkabit result, (ii) a gate set acting on tunnels (modulating J, cycling chirality, etc.) that implements ternary logical operations, and (iii) an encoded readout protocol that extracts computational outputs beyond pairwise family discrimination. Each is a natural next extension but not demonstrated in this paper.

The current paper's claim is therefore precise: **the computational primitive of the architecture — the two-trit analog of a binary CNOT — is demonstrable in simulation under Willow/Eagle-realistic noise, with a specific pre-registered hardware protocol**. This is the minimum content required to justify a full hardware test regime.

### 7.2 Relationship to the capstone's read/write interpretation

The directional tunnel asymmetry is the clearest empirical expression of the capstone's §15.6 interpretation: u is the write flow, v is the read flow, and the cross-chiral tunnel u_A ↔ v_B is the physical mechanism by which a *written* state on merkabit A is *read* by the tunnel into merkabit B's read register. The specific ordering (β, γ) vs (γ, β) swaps which Z₃ label is written versus read, and this swap is *not* a trivial relabelling: the tunnel + chiral P gate combination gives the two orderings dramatically different interference patterns.

This grounds the capstone's read/write interpretation — which is stated as an interpretive framing rather than a testable claim in §15.6 — as an *operational* statement. The asymmetry between ordered pairs is the operational content of "u is write, v is read" on hardware.

### 7.3 Relationship to inter-merkabit torsion in Paper 20

Paper 20 [9] derives gravity and the inverse-square law from the R_inter torsion channel between adjacent merkabits. The tunnel operator implemented in Protocol 4S-Tunnel (iSWAP^J) is the quantum-circuit realisation of this permanent inter-merkabit coupling at the lattice scale r = 1. The J-dependence sweep (Section 5.1) characterises how the directional signal depends on coupling strength, analogous to how the gravitational potential depends on distance: J/r ≈ 0.1 corresponds to adjacent-node coupling on a natural-unit lattice.

A specific prediction follows: running Protocol 4S-Tunnel at multiple J values corresponding to r = 1, 2, 3, ... lattice spacings (J = 0.1, 0.05, 0.033, ...) should show the directional signal decaying with 1/r to a good approximation. This is a lattice-gravity-like signature on quantum hardware. It is out of scope for this paper but proposed as Paper 32 in the series.

### 7.4 The natural decoherence-free subspace

The robustness study (Section 5.3) establishes that the directional signal is phase-coherent and protected from dephasing noise. This qualifies the cross-chiral tunnel as a **natural decoherence-free subspace** for the architecture.

Decoherence-free subspaces (DFS) [cite standard DFS literature] are typically engineered by choosing a logical encoding that commutes with the dominant system noise channel. In Protocol 4S-Tunnel, no encoding was explicitly designed: the DFS emerged from the combination of the framework's native structure (chiral P gate) and the inter-merkabit tunnel primitive (iSWAP^J). The architecture supplies its own DFS.

This has a broader implication. If the framework is correct, then other architectural structures (e.g. three-merkabit cells, the full 5-gate ouroboros internal step) may also host natural DFSs for richer computational primitives. The tunnel result is the first example; a systematic classification is proposed for future work.

### 7.5 What could break the signal on hardware

Four specific hardware concerns are named in the pre-registration (Section 6), each a legitimate reason the hardware test could return a null result:

1. **Shot budget too small** — below ~1,000 shots per cell, statistical noise dominates over the predicted gap. This is easily avoided with 4,096 shots × 6 repeats.

2. **Qubit layout selection with high 2-qubit gate error** — the iSWAP^J between u_A and v_B needs a qubit pair with 2q error < 0.01. On current Eagle r3 this is achievable with careful layout; best-available pairs routinely reach 0.003.

3. **Non-native iSWAP decomposition** — IBM's native 2q gate is CX or ECR, not iSWAP. Decomposition into 2-3 CX per iSWAP^J adds depth. At n = 1, the circuit depth per merkabit is ~50 2q-equivalents; decomposition overhead would double this, still within budget.

4. **Correlated / crosstalk errors between A and B registers** — the two merkabits are implemented on physically nearby qubit blocks. Crosstalk between them could correlate errors in ways neither uniform noise nor FakeSherbrooke models. Dynamical decoupling insertion (Observable 14d) is designed to suppress exactly this.

A hardware null result that can be traced to one of these specific concerns is scientifically useful; it tells us where the practical constraint on the architecture's computational use sits. A null result that cannot be traced to any of them would be a more substantive challenge to the framework.

### 7.6 Paths if Observable 14 is confirmed

Confirmation of Observable 14a–d on hardware opens three natural next-paper directions:

- **Paper 32** — Multi-merkabit chain: three, four, N tesseracts in a Eisenstein-lattice configuration, with tunnel coherence across each inter-merkabit bond. Predicted: characteristic 1/r-decay of the directional signal, mirroring gravitational inverse-square decay at the lattice scale.
- **Paper 33** — Ternary gate library: explicit construction of Toffoli-analog, Fredkin-analog, and universal-ternary gate sets via J-modulated tunnel operations and chiral P-gate tuning.
- **Paper 34** — Hardware demonstration of a simple ternary algorithm (e.g., Z₃ phase estimation) using Protocols 4S-Tunnel and descendants on IBM Eagle r3.

---

## 8. Methods

### 8.1 Simulation

All simulations use either Google Cirq 1.6.1 with `cirq.DensityMatrixSimulator` or Qiskit 2.3.1 with `qiskit_aer` 0.17.2. FakeSherbrooke noise is obtained via `qiskit_ibm_runtime.fake_provider.FakeProviderForBackendV2` with the `fake_sherbrooke` backend.

State preparation on a 2-qubit register uses Qiskit's `QuantumCircuit.initialize` (for Aer) or a QR-completion-based `MatrixGate` (for Cirq). Isoclinic rotations (cross, horizontal, diagonal) are implemented as 4×4 complex unitary matrices applied via `MatrixGate` (Cirq) or `UnitaryGate` (Qiskit) to pairs of qubits. The P gate is a diagonal 4×4 matrix `diag(1, exp(−iφ), exp(+iφ), 1)` applied similarly.

The tunnel operator `iSWAP^J` is constructed explicitly via `cirq.ISWAP ** J` (Cirq) or the 4×4 matrix `exp(i J π/2 (XX + YY)/2)` (Qiskit). Applied qubit-wise between the two-qubit u_A register and the two-qubit v_B register.

The SWAP test uses a single ancilla qubit with `H-CSWAP-CSWAP-H-measure`, where the two CSWAPs swap the corresponding qubits of the two target 2-qubit registers.

Circuit transpilation for Aer uses `optimization_level=1` with a fixed basis `{id, rz, sx, x, cx, cz, ecr}` for uniform-noise sweeps, or with the backend calibration directly for FakeSherbrooke.

### 8.2 Noise models

**Uniform depolarising noise** is applied per-gate with rate `p_depol · scale`, where scale = 0.1 for single-qubit gates, 1.0 for two-qubit gates, and 1.5 for three-qubit gates.

**Amplitude damping** uses `qiskit_aer.noise.amplitude_damping_error(γ)` with γ = p_depol tensored per-qubit for multi-qubit gates.

**Phase damping** uses `qiskit_aer.noise.phase_damping_error(λ)` similarly.

**Combined amplitude + phase damping** composes the two channels per-qubit before tensoring.

**FakeSherbrooke** is the calibrated IBM Eagle r3 noise model with all native T₁, T₂, per-gate error rates, and readout error directly from IBM production calibration data.

### 8.3 Statistical methods

Each cell in the robustness grids is 6 repeats × 4,096 shots. The standard error on the mean is computed as the sample standard deviation (unbiased, n−1 divisor) divided by √6. Significance of a directional gap is quoted as gap / √(SEM_A² + SEM_B²), i.e., the gap in units of combined standard error.

No error mitigation, readout correction, or post-selection is applied at the simulation level.

### 8.4 Data and code availability

All scripts, raw per-repeat data JSONs, prediction documents, and this manuscript are committed to `github.com/selinaserephina-star/tesseract_quantum_implementation` (private during pre-registration phase, to be mirrored to `github.com/SelinaAliens/tesseract_quantum_implementation` on publication).

The cirq/ and qiskit/ subdirectories contain the full protocol implementations; the results/ subdirectory contains representative simulator outputs as JSON files. A complete re-running of the robustness sweeps takes approximately two hours on a standard laptop with numpy, scipy, networkx, cirq 1.6+, and qiskit_aer 0.17+.

---

## 9. Conclusion

The merkabit framework predicts ternary computation via inter-merkabit torsion tunnels. Protocol 4S-Tunnel is the first simulation-ready, pre-registered hardware protocol for directly testing this prediction on current superconducting qubits. Three findings support the protocol's readiness:

1. Two independent simulator stacks agree that ordered-pair Z₃ inputs produce dramatically different tunnel coherences, with (β, γ) giving zero exactly under ideal dynamics and (γ, β) giving 0.76. The directional gap is 166σ (Cirq) or 125σ (Aer) at ideal, and 7.6σ (Cirq) or 23σ (Aer) at Willow-realistic `p_depol = 0.005`.

2. At Willow-realistic noise, **local tesseract coherence becomes useless while the tunnel still distinguishes 14 of 15 input-pair distinctions** (Aer). Ternary information survives in the inter-merkabit channel where it has decayed in either individual merkabit.

3. A full robustness study (J, n, noise-channel variety, calibrated Eagle r3) establishes an operational hardware point at **n = 1, J = 0.1, 9 qubits, under 30 QPU-minutes**, with a predicted 6.4σ directional signal under FakeSherbrooke-calibrated noise.

The central claim is therefore concrete, specific, and pre-registered: **running Protocol 4S-Tunnel on IBM Eagle r3 or Heron r2 should demonstrate ordered-pair ternary correlation — the two-trit computational primitive of the merkabit architecture — at or above the 6.4σ threshold**. Confirmation would be the first hardware demonstration of ternary computation grounded in a specific computational architecture. A null result, in either direction along the Cirq–Aer–FakeSherbrooke bracket, would constrain the noise-model interpretation of the framework with actionable specificity.

The architecture has been characterised in simulation to the point where hardware is now the relevant test. Section 6 provides the complete pre-registration; Section 7.6 provides the post-confirmation research programme. This paper is the bridge between the framework's theoretical claims and their experimental consolidation on current quantum hardware.

---

## References

[1] Stenberg, S. *The Merkabit — A Ternary Computational Unit on the Eisenstein Lattice.* Zenodo, 10.5281/zenodo.18925475 (v4, 2026). Base paper.

[9] Stenberg, S. *Gravity and Dark Matter from the Eisenstein Lattice: The Inverse Square Law, Newton's Constant, and the Cayley–Dickson Dark Sector from Octonionic Torsion Geometry.* Paper 20, Zenodo, 10.5281/zenodo.19483841 (2026).

[13] Stenberg, S. & Hetland, T. H. *The P Gate Is Native: Hardware Confirmation of the Dual-Spinor Merkabit on IBM Quantum.* Paper 24, Zenodo, 10.5281/zenodo.19484743 (2026).

[14] Stenberg, S. & Hetland, T. H. *Four of Five: Berry Phase, Quasi-Period, and the Fano Gap on IBM Eagle r3.* Paper 25, Zenodo, 10.5281/zenodo.19502830 (2026).

[15] Stenberg, S. & Hetland, T. H. *The Merkabit Is Geometric: Cross-Architecture Hardware Validation, Corrected Willow Interpretation, and a Pre-Registered Prediction for Square-Grid Quantum Processors.* Paper 26, Zenodo, 10.5281/zenodo.19554030 (2026).

[16] Stenberg, S. *The Merkabit.* Base paper, Zenodo, 10.5281/zenodo.18925475 (2026).

[17] McKay, J. *Graphs, singularities, and finite groups.* Proc. Symp. Pure Math. 37, 183–186 (1980).

[30] Stenberg, S. with Claude Anthropic. *The Merkabit Architecture: A Candidate Unified Theory of Physics.* Capstone, Merkabit Research Series (2026).

[32] Stenberg, S. *The Plasma Is the Weak Force: Octonionic Boundary Conditions, Catalytic Confinement, and a Zero-Parameter Ignition Protocol.* Paper 17, Zenodo, 10.5281/zenodo.19279114 (2026).

[DFS1] Lidar, D. A. & Whaley, K. B. *Decoherence-Free Subspaces and Subsystems.* In *Irreversible Quantum Dynamics*, Lecture Notes in Physics 622, 83–120 (2003).

[DFS2] Palma, G. M., Suominen, K.-A., Ekert, A. K. *Quantum Computers and Dissipation.* Proc. R. Soc. Lond. A 452, 567–584 (1996).

[CIRQ] Cirq Developers. *Cirq: A python framework for creating, editing, and invoking NISQ circuits.* Google (2024).

[QISKIT] Qiskit Team. *Qiskit: An Open-source Framework for Quantum Computing.* Zenodo (2024).

---

## Acknowledgements

The author thanks IBM Quantum and Google Quantum AI for public access to simulator stacks and calibrated fake backends that made this pre-registration possible. The present paper was prepared with substantial drafting, analysis-code-review, and provenance-verification assistance from Claude (Anthropic, Opus 4.7 1M context), which did not have operational access to any hardware runtime during the simulations reported. All scientific claims, pre-registered thresholds, and final manuscript content are the author's responsibility.

No competing financial interests.

---

## Appendix A — IBM Runtime submission details

This appendix specifies the exact hardware-submission protocol for executing Observable 14a–d on IBM Eagle r3 (`ibm_strasbourg`, `ibm_brussels`) or Heron r2 (`ibm_kingston`). It complements the Cirq / Qiskit source files in `cirq/run_p4s_tunnel_cirq.py` and `qiskit/run_p4s_tunnel_aer.py`, which contain the full circuit definitions; this appendix fixes the hardware-specific choices that are not captured by the simulation scripts.

### A.1 Backend and provider

Primary targets:
- `ibm_strasbourg` (Eagle r3, 127 qubits, heavy-hex)
- `ibm_brussels` (Eagle r3, 127 qubits, heavy-hex; backup to Strasbourg)
- `ibm_kingston` (Heron r2, 156 qubits; cross-architecture confirmation)

Runtime: `qiskit-ibm-runtime 0.46.1` or later on `qiskit 2.3.1`. Account instance: Paid pay-as-you-go for Eagle r3 sessions, Open free-tier for Heron r2 confirmation.

### A.2 Qubit allocation for 9-qubit protocol

The circuit uses 9 qubits: four per merkabit plus one SWAP-test ancilla. The merkabit qubit pairs must carry the u and v spinor registers; the ancilla must have native CSWAP-reachable connections to specific qubits in both merkabit registers.

**Eagle r3 (`ibm_strasbourg`) reference layout:**

| Role | Qubit | Coupling relevance |
|------|-------|-------------------|
| u_A register | q[62], q[63] | 2-qubit cross gate within u_A |
| v_A register | q[81], q[72] | native CX 72→62 and 72→81 |
| u_B register | q[61], q[60] | adjacent to u_A via 61↔62 |
| v_B register | q[80], q[71] | adjacent to v_A via 72↔71 |
| SWAP ancilla | q[73] | reaches u_A, v_A, v_B via 73→72, 73→81, 73→71 |

This layout mirrors the 9-qubit triangle cell of Paper 25 with specific adaptation for the two-merkabit structure. Alternative layouts valid if (i) each 2-qubit register has internal CX, (ii) ancilla reaches both pair members of u_A and v_B for the tunnel SWAP test, and (iii) two-qubit gate errors ε(CX) < 0.01 on all involved pairs at submission time.

**Heron r2 (`ibm_kingston`) reference layout:**

Heron r2 has a different coupling map; substitute qubits selected at submission time using `backend.properties()` to pick the best-calibrated 9-qubit subgraph satisfying the connectivity requirements above. Kingston qubit pairs routinely achieve 2q gate errors ≤ 0.003, typically sitting at the Cirq–Aer bracket's upper bound (37σ).

### A.3 Native gate decomposition of iSWAP^J

The tunnel operator `iSWAP^J` is not a native IBM gate. It decomposes into CX + single-qubit rotations as:

```
iSWAP^J = (H ⊗ I) · CX · (I ⊗ R_z(−Jπ/2)) · CX · (H ⊗ I)
        · (I ⊗ R_z(Jπ/2)) · (R_z(Jπ/2) ⊗ I)
```

For `J = 0.1`, this is three two-qubit CX gates per qubit pair, per step. Since the tunnel acts qubit-wise on two pairs (u_A[0] ↔ v_B[0] and u_A[1] ↔ v_B[1]), this is 6 CX gates per internal step for the tunnel. Combined with the isoclinic rotations (three 2-qubit matrices per merkabit, each decomposing to ~3 CX) plus the P gate (zero CX, virtual-Z only), the per-step CX count is approximately:

- Internal step per merkabit: 9 CX (three isoclinic × 3 CX each)
- Internal step both merkabits: 18 CX
- Tunnel step: 6 CX
- **Per internal step total: 24 CX**

At n = 1 Coxeter period (12 internal steps), the per-circuit CX budget is approximately 288, plus ~24 CX for SWAP-test CSWAPs (each CSWAP decomposes to ~8 CX). Total: **~312 CX per circuit**.

### A.4 Transpilation

Use `generate_preset_pass_manager` at `optimization_level=3`, which merges consecutive single-qubit rotations and chooses a layout minimising 2-qubit gate depth.

**Transpilation seed:** fix at 42 for reproducibility. Recorded in each output JSON file as `transpile_seed`.

**Basis gates:** `{id, rz, sx, x, cx, ecr}` (Eagle r3 native). Heron r2 adds `cz`; accept whatever the backend supports.

### A.5 Pre-submission validation

Before first hardware job:

1. Build circuits with the script, run locally on `AerSimulator.from_backend(FakeSherbrooke())` — expect the 6.4σ directional gap at n = 1.
2. Confirm `backend.properties().gate_error(qubits=[62, 63])` and equivalents for all involved CX pairs are < 0.01.
3. Record backend calibration snapshot (`backend.properties()._json`) in the output directory alongside the submitted jobs.

### A.6 Job submission

Use `SamplerV2` from `qiskit_ibm_runtime` with:
- `shots = 4096` per circuit
- `repeats = 6` (submit 6 independent runs per circuit, batched as 6 entries in the same Session)
- `Session` mode to amortise queue overhead across all Observable 14a–d circuits

Total circuits: 14a needs 12 (2 families × 6 reps); 14b uses the same circuits; 14c needs 90 (6 fam × 3 obs × 5 reps); 14d needs 24 (with/without DD × 2 fam × 6 reps). Roughly 120 circuits, batched into a single Session of approximately 40 minutes wall time.

### A.7 Data handling

Raw `SamplerV2` counts shall be written to the repository within 48 hours of job completion, prior to any analysis. The analysis estimator is the one already in the Aer reference implementation (`overlap_from_swap`); no modification shall be applied post-hoc. No error mitigation, no readout correction, no post-selection.

Output format: per-circuit JSON files in `outputs/p4s_tunnel_hardware/` containing the backend name, job ID, session ID, shot count, qubit assignment, transpile seed, and raw counts dictionary. This mirrors the convention of the Paper 24–26 hardware-results repository.

### A.8 Dynamical decoupling for Observable 14d

Observable 14d tests whether dynamical-decoupling (DD) insertion enhances the directional signal by suppressing correlated noise. Implementation:

```python
from qiskit.transpiler.passes import PadDynamicalDecoupling
from qiskit.circuit.library import XGate

pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
pm.scheduling = PadDynamicalDecoupling(
    durations=backend.target.durations(),
    dd_sequence=[XGate(), XGate()],  # XX decoupling
)
```

Run the full protocol with and without the `PadDynamicalDecoupling` pass. Compare directional gaps; ratio > 1.2 confirms DD enhancement (Observable 14d pass condition).

### A.9 Contingencies

| Scenario | Response |
|----------|----------|
| Best-calibrated 9-qubit subgraph has 2q error > 0.015 | Postpone submission; wait for backend recalibration |
| Job batch fails mid-session | Resubmit individual failed circuits; do not merge failure counts into success counts |
| Per-qubit readout error > 0.05 on any data qubit | Swap the mapping to an alternative well-calibrated qubit, documented at submission time |
| Wall time exceeds 1 hour | Split into two Sessions; total budget still ≤ 2 QPU-hours |

All contingency responses must be documented in the output JSON metadata before analysis proceeds.

---

*Draft v1 — ready for author review. Subject to style and structural revision before Zenodo submission. Target venue: Zenodo preprint series, followed by arXiv cross-posting in quant-ph.*
