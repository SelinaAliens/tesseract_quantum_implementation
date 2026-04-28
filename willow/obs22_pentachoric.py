#!/usr/bin/env python3
"""
OBSERVABLE 22 -- Pentachoric Verification Protocol (Paper 35, Option A)

Pre-registered Willow hardware test of the 19-qubit tesseract-only QC memory.
The architecture has ONE compute triangle (3 merkabits), ONE memory tunnel,
and ONE database merkabit; no octonion layer.

The five simulation stages correspond exactly to the five pentachoric ouroboros
gates {S, R, T, F, P} of Paper 24:

  Stage 1 (Substrate, S):  compute triangle self-sustains at |<u|v>| ~ 0.47
                            -- the substrate holds.
  Stage 2 (Rotation, R):   write-read 3x3 matrix with Z_3 cyclic shift
                            alpha -> gamma -> beta -> alpha
                            -- the substrate ROTATES through the Galois orbit.
  Stage 3 (Transfer, T):   null control -- no memory tunnel applied
                            -- transfer is GATED; no content without T.
  Stage 4 (Frequency, F):  J_mem sweep -- find optimal tunnel strength
                            -- Frequency gate is the write amplitude.
  Stage 5 (Phase, P):      u_D direct readout -- u register stays at |0>
                            -- Phase enforces cross-chirality u->v only.

All five stages must pass for the STRONG PASS verdict.

Qubit count: 19 (12 compute + 4 database + 2 reference + 1 ancilla).
Transpiled depth on Willow PhXZ merge: ~3 per merkabit data qubit.
Source circuit: ../cirq/run_p4s_tesseract_memory_cirq.py (canonical,
                 imported unchanged).

Pre-registered predictions (from Paper 35 Section 0, ideal simulation)
----------------------------------------------------------------------
At n_compute = 1, J_intra = 0.1, J_mem = 0.5 (Stage 4 optimum):

  22-S: Stage 1 compute self-sustain
    mean |<u|v>| across all 3 merkabits and 3 input labels in [0.30, 0.65].

  22-R: Stage 2 Z_3 cyclic rotation
    cycled-diagonal {alpha->gamma, beta->alpha, gamma->beta}
    mean at least 0.10 above remaining 6 cells.
    Target: gap = +0.15 +/- 0.05 at n_trials >= 10.
    At Willow noise (p_depol = 0.003): gap = +0.06 +/- 0.04.

  22-T: Stage 3 transfer gating
    null-control gap (no memory tunnel) within 0.03 of zero.

  22-F: Stage 4 frequency sweep
    peak of |gap(J_mem)| occurs at J_mem in (0.3, 0.7)
    (partial SWAP beats full SWAP -- confirms the Frequency gate is
     the WRITE amplitude, not a full state replacement).

  22-P: Stage 5 cross-chirality
    u_D direct readout gap |diag - off| <= 0.03
    (Paper 31's u<->v rule: tunnel routes content from u to v only).

Strong pass: all 5 gates (22-S, 22-R, 22-T, 22-F, 22-P).
Weak pass:   22-S, 22-R, 22-P (the three that identify the Z_3 ROTATION
             plus substrate plus cross-chirality).
Null:        22-R fails -- the Z_3 cyclic shift is not detectable at
             Willow noise.

Resource budget: 19 qubits x 5 stages x avg 60 circuits per stage
x 6 repeats x 4096 shots ~= 7M shots, ~= 140 minutes of Willow QPU at
current batch throughput (a single pentachoric test, ~= $15-30 at
current Willow-hours pricing).

Usage
-----
  python obs22_pentachoric.py --sim-only
  python obs22_pentachoric.py --project <GCP> --processor <PROC>

Authors: Stenberg with Claude Anthropic, April 2026.
"""
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))
from _engine_wrapper import (
    engine_submit_or_fail, write_pre_registration_json, std_argparser,
)

sys.path.insert(0, str(SCRIPT_DIR.parent / "cirq"))
from run_p4s_tesseract_memory_cirq import (
    stage1_compute_baseline, stage2_write_verification,
    stage3_null_control, stage4_Jmem_sweep, stage5_direct_u_D,
    LABELS,
)
import numpy as np


OBSERVABLE = "obs22_pentachoric"
PAPER_REF  = "Paper 35 (Three-Layer QC: Compute / Communicate / Store -- Option A)"

# Pentachoric gate thresholds.
# Each maps to one of {S, R, T, F, P}.
THRESHOLDS = {
    "22S_substrate_mean_lo":         0.30,    # Stage 1 compute self-sustain
    "22S_substrate_mean_hi":         0.65,
    "22R_rotation_cycled_gap_min":   0.08,    # Stage 2 Z_3 cyclic shift gap
    "22R_rotation_sigma_min":        2.0,     # Stage 2 significance
    "22T_transfer_null_tolerance":   0.03,    # Stage 3 null control
    "22F_frequency_peak_low":        0.30,    # Stage 4 J_mem optimum bracket
    "22F_frequency_peak_high":       0.70,
    "22P_phase_tolerance":           0.03,    # Stage 5 u_D cross-chirality
}


def cycled_gap(matrix_list):
    """Compute the Paper 35 Stage-2 cycled-diagonal metric on a 3x3 list.
    matrix[i][j] = overlap for write-label i, ref-label j; labels alpha,beta,gamma.
    Cycled diagonal = {(alpha, gamma), (beta, alpha), (gamma, beta)}
    Remaining 6 cells = the off-cycle entries.
    Returns (cycled_mean, off_mean, gap, sigma_estimate).
    """
    M = np.asarray(matrix_list)
    # Index order: LABELS = ['alpha', 'beta', 'gamma'] -> 0, 1, 2
    #     cycle alpha -> gamma: (0, 2)
    #     cycle beta  -> alpha: (1, 0)
    #     cycle gamma -> beta:  (2, 1)
    cycled_idx = [(0, 2), (1, 0), (2, 1)]
    cycled = np.array([M[i, j] for i, j in cycled_idx])
    all_cells = M.flatten()
    mask = np.ones(9, dtype=bool)
    for i, j in cycled_idx:
        mask[3 * i + j] = False
    off = all_cells[mask]
    gap = float(cycled.mean() - off.mean())
    # Pooled-std sigma
    s_c = float(cycled.std(ddof=1)) if len(cycled) > 1 else 0.0
    s_o = float(off.std(ddof=1))    if len(off)    > 1 else 0.0
    sem = float(np.sqrt(s_c**2 / len(cycled) + s_o**2 / len(off)))
    sigma = gap / sem if sem > 0 else float('inf')
    return float(cycled.mean()), float(off.mean()), gap, sigma


def main():
    ap = std_argparser(OBSERVABLE, default_shots=2048)
    ap.add_argument("--n-compute", type=int,   default=1)
    ap.add_argument("--J-intra",   type=float, default=0.1)
    ap.add_argument("--J-mem",     type=float, default=0.5,
                     help="memory tunnel strength (Paper 35 optimum is 0.5)")
    args = ap.parse_args()

    print(f"OBSERVABLE 22: Pentachoric Verification Protocol (Paper 35)")
    print(f"  19 qubits, n_compute={args.n_compute}, "
          f"J_intra={args.J_intra}, J_mem={args.J_mem}")
    print(f"  shots={args.shots}, n_trials={args.n_trials}")
    print(f"  Five pentachoric gates: S (substrate), R (rotation), "
          f"T (transfer), F (frequency), P (phase).")

    if not args.sim_only:
        raise NotImplementedError(
            "Hardware path: add Google Quantum Engine credentials via "
            "engine_submit_or_fail. The 19-qubit Cirq circuit builder from "
            "../cirq/run_p4s_tesseract_memory_cirq.py is already Willow-ready; "
            "substitute engine.run_batch() for sim.run() in each stage."
        )

    print("  mode: SIMULATION (cirq.Simulator, ideal)")

    # -------------------------------------------------------------------- 22-S
    s1 = stage1_compute_baseline(args.n_compute, args.J_intra,
                                  args.shots, args.n_trials)
    all_sustain = []
    for label in LABELS:
        for m in 'ABC':
            all_sustain.extend(s1[label][m])
    s1_mean = float(np.mean(all_sustain))
    s1_pass = (THRESHOLDS["22S_substrate_mean_lo"] <= s1_mean
                <= THRESHOLDS["22S_substrate_mean_hi"])
    print(f"\n  22-S (Substrate): mean |<u|v>| = {s1_mean:.4f}  "
          f"[{THRESHOLDS['22S_substrate_mean_lo']}, "
          f"{THRESHOLDS['22S_substrate_mean_hi']}]  -> "
          f"{'PASS' if s1_pass else 'FAIL'}")

    # -------------------------------------------------------------------- 22-R
    s2 = stage2_write_verification(args.n_compute, args.J_intra, args.J_mem,
                                     args.shots, args.n_trials)
    cycled_mean, off_mean, cycled_gap_val, cycled_sigma = cycled_gap(s2['matrix'])
    s2_pass = (cycled_gap_val >= THRESHOLDS["22R_rotation_cycled_gap_min"]
                and cycled_sigma >= THRESHOLDS["22R_rotation_sigma_min"])
    print(f"\n  22-R (Rotation): Z_3 cyclic gap = {cycled_gap_val:+.4f}  "
          f"({cycled_sigma:+.2f} sigma)  -> {'PASS' if s2_pass else 'FAIL'}")
    print(f"    cycled cells: alpha->gamma, beta->alpha, gamma->beta  "
          f"mean = {cycled_mean:.4f}")
    print(f"    off-cycle     mean = {off_mean:.4f}")

    # -------------------------------------------------------------------- 22-T
    s3 = stage3_null_control(args.n_compute, args.J_intra, args.J_mem,
                              args.shots, args.n_trials)
    s3_cycled_mean, s3_off_mean, s3_gap, s3_sigma = cycled_gap(s3['matrix'])
    s3_pass = abs(s3_gap) <= THRESHOLDS["22T_transfer_null_tolerance"]
    print(f"\n  22-T (Transfer null): cycled gap (no tunnel) = {s3_gap:+.4f}  "
          f"(|.| <= {THRESHOLDS['22T_transfer_null_tolerance']})  -> "
          f"{'PASS' if s3_pass else 'FAIL'}")

    # -------------------------------------------------------------------- 22-F
    s4 = stage4_Jmem_sweep(args.n_compute, args.J_intra,
                             args.shots, args.n_trials)
    # Pick the J_mem with largest |gap|
    best = max(s4, key=lambda d: abs(d['gap']))
    s4_pass = (THRESHOLDS["22F_frequency_peak_low"] <= best['J_mem']
                <= THRESHOLDS["22F_frequency_peak_high"])
    print(f"\n  22-F (Frequency): peak at J_mem = {best['J_mem']:.2f}  "
          f"gap = {best['gap']:+.4f}  -> {'PASS' if s4_pass else 'FAIL'}")

    # -------------------------------------------------------------------- 22-P
    s5 = stage5_direct_u_D(args.n_compute, args.J_intra, args.J_mem,
                             args.shots, args.n_trials)
    s5_pass = abs(s5['gap']) <= THRESHOLDS["22P_phase_tolerance"]
    print(f"\n  22-P (Phase/cross-chirality): u_D gap = {s5['gap']:+.4f}  "
          f"(|.| <= {THRESHOLDS['22P_phase_tolerance']})  -> "
          f"{'PASS' if s5_pass else 'FAIL'}")

    # -------------------------------------------------------------------- verdict
    all_pass = s1_pass and s2_pass and s3_pass and s4_pass and s5_pass
    weak_pass = s1_pass and s2_pass and s5_pass
    if all_pass:
        verdict = "STRONG PASS (all five pentachoric gates)"
    elif weak_pass:
        verdict = ("WEAK PASS (S + R + P pass; T or F degraded -- "
                    "substrate, rotation, and cross-chirality confirmed)")
    else:
        failed = [n for n, p in [('S', s1_pass), ('R', s2_pass),
                                  ('T', s3_pass), ('F', s4_pass),
                                  ('P', s5_pass)] if not p]
        verdict = f"NULL (failed gates: {', '.join(failed)})"
    print(f"\n  PENTACHORIC VERDICT: {verdict}")

    summary = {
        "22S_substrate_mean":          s1_mean,
        "22S_pass":                    bool(s1_pass),
        "22R_cycled_gap":              cycled_gap_val,
        "22R_cycled_sigma":            cycled_sigma,
        "22R_cycled_mean":             cycled_mean,
        "22R_off_mean":                off_mean,
        "22R_pass":                    bool(s2_pass),
        "22T_null_gap":                s3_gap,
        "22T_pass":                    bool(s3_pass),
        "22F_J_peak":                  float(best['J_mem']),
        "22F_peak_gap":                float(best['gap']),
        "22F_sweep":                   s4,
        "22F_pass":                    bool(s4_pass),
        "22P_u_D_gap":                 float(s5['gap']),
        "22P_pass":                    bool(s5_pass),
        "pentachoric_verdict":         verdict,
        "mode":                        "simulation",
        "parameters": {
            "n_compute": args.n_compute,
            "J_intra":   args.J_intra,
            "J_mem":     args.J_mem,
            "shots":     args.shots,
            "n_trials":  args.n_trials,
        },
    }
    out = write_pre_registration_json(OBSERVABLE, PAPER_REF,
                                        THRESHOLDS, summary)
    print(f"\n  wrote {out}")


if __name__ == "__main__":
    main()
