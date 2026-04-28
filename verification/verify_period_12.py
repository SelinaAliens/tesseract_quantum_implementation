#!/usr/bin/env python3
"""Verify period-12 exactness of the Stage C ternary-spectrum result.

Implements the bit-identical state-vector check (Option C) at configurable
precision (Option B). Builds the same Stage C double-triangle circuit at
offset_T2 = base and offset_T2 = base + 12 (which reduce to identical
dynamics modulo T_CYCLE = 12) and reports two metrics:

1. State-vector L2 distance ||psi(base) - psi(base+12)||_2
   At complex128 this should be at machine precision (~1e-13 to 1e-14)
   since the dynamics are identical mod T_CYCLE.

2. Entropy delta |S(rho_v_D(base)) - S(rho_v_D(base+12))|
   Same expectation.

Compares against the complex64 baseline (~1e-8 measured in the original
Stage C run, p4s_double_triangle_stageC_20260421T171812.json).

Usage:
    python verify_period_12.py --dtype complex64
    python verify_period_12.py --dtype complex128

Output: JSON record with measured deviations at three base offsets
{0, 4, 8} (the canonical Z_3 triadic points within one Coxeter period).

Memory budget:
    complex64:   2 GB state vector  (~3-4 GB peak)
    complex128:  4 GB state vector  (~6-8 GB peak)

Runtime per circuit (laptop, 28 qubits, n_compute=1):
    complex64:   ~10-20 s
    complex128:  ~25-50 s
Six circuits total: ~2-5 min.
"""
from __future__ import annotations
import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import cirq

# Locate the Stage C builder (sibling cirq/ directory)
HERE = Path(__file__).resolve().parent
CIRQ_DIR = HERE.parent / "cirq"
sys.path.insert(0, str(CIRQ_DIR))
from run_p4s_double_triangle_cirq import (        # type: ignore
    build_double_triangle_circuit,
    z3_eigenstate,
    LABEL_IDX,
)

T_CYCLE = 12
N_QUBITS = 28


def state_vector_at(offset_T2: int, labels1, labels2, dtype,
                     n_compute: int = 1, J_intra: float = 0.1,
                     J_mem: float = 0.5) -> np.ndarray:
    """Build and simulate the Stage C circuit at one offset; return state vector."""
    qc = build_double_triangle_circuit(
        labels1=labels1, labels2=labels2,
        n_compute=n_compute, J_intra=J_intra,
        J_mem1=J_mem, J_mem2=J_mem, offset_T2=offset_T2,
    )
    sim = cirq.Simulator(dtype=dtype)
    result = sim.simulate(qc)
    psi = np.asarray(result.final_state_vector)
    # Cirq may upcast internally; force the requested dtype for the comparison.
    return psi.astype(dtype, copy=False)


def entropy_of_v_D(psi: np.ndarray, dtype) -> float:
    """v_D von Neumann entropy at the requested precision.

    Promote rho computation to the requested dtype to avoid float32 dragging
    the entropy result back to ~1e-7 noise even when the state vector is
    complex128.
    """
    psi2 = psi.reshape(2 ** (N_QUBITS - 2), 4)
    if dtype == np.complex128:
        psi2 = psi2.astype(np.complex128, copy=False)
    rho = np.einsum("ia,ib->ab", psi2, psi2.conj())
    if dtype == np.complex128:
        rho = rho.astype(np.complex128, copy=False)
    evals = np.linalg.eigvalsh(rho).real
    # Tighter clip for complex128 (machine eps ~1e-16); looser for complex64.
    floor = 1e-16 if dtype == np.complex128 else 1e-8
    evals = np.clip(evals, floor, 1.0)
    return float(-np.sum(evals * np.log(evals)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dtype", choices=["complex64", "complex128"],
                    default="complex128")
    ap.add_argument("--bases", type=int, nargs="+", default=[0, 4, 8],
                    help="Base offsets to test (each compared against +12)")
    ap.add_argument("--label-pair", nargs=2, default=["alpha", "alpha"],
                    metavar=("X", "Y"), help="Z_3 label on T1 and T2")
    ap.add_argument("--out", default=None)
    ap.add_argument("--low-memory", action="store_true",
                    help="Stage psi_base to disk between simulations and stream "
                         "the L2 diff from a memory-mapped file. Required for "
                         "complex128 on machines with <16 GB RAM.")
    args = ap.parse_args()

    dtype = np.complex128 if args.dtype == "complex128" else np.complex64
    state_dtype = "complex128" if dtype == np.complex128 else "complex64"

    if args.label_pair[0] not in LABEL_IDX or args.label_pair[1] not in LABEL_IDX:
        ap.error(f"label-pair must be from {list(LABEL_IDX.keys())}")

    L1 = (args.label_pair[0],) * 3
    L2 = (args.label_pair[1],) * 3

    print("=" * 72)
    print(f"Period-12 exactness verification")
    print(f"  dtype:      {state_dtype}")
    print(f"  label_pair: T1={args.label_pair[0]}  T2={args.label_pair[1]}")
    print(f"  bases:      {args.bases}")
    print(f"  state vec:  2^{N_QUBITS} * "
          f"{16 if dtype == np.complex128 else 8} B = "
          f"{2**N_QUBITS * (16 if dtype == np.complex128 else 8) / 1e9:.1f} GB")
    print("=" * 72)

    # Tempdir for low-memory staging
    import tempfile, gc, os
    tmpdir = Path(tempfile.mkdtemp(prefix="psi_stage_"))

    def chunked_L2_and_max(p1: np.ndarray, p2_mmap: np.ndarray,
                            chunk: int = 1 << 22) -> tuple[float, float]:
        """L2 norm and per-component max of (p1 - p2_mmap), streamed."""
        sum_sq = 0.0
        cmax = 0.0
        for i in range(0, p1.size, chunk):
            j = min(i + chunk, p1.size)
            d = p1[i:j] - p2_mmap[i:j]
            sum_sq += float(np.sum(np.abs(d) ** 2))
            cm = float(np.max(np.abs(d)))
            if cm > cmax:
                cmax = cm
        return float(np.sqrt(sum_sq)), cmax

    t_start = time.time()
    results = []
    for base in args.bases:
        print(f"\n[{base:>2d} vs {base+12:>2d}] simulating both circuits...")

        if args.low_memory:
            # Sim psi_base, compute its entropy, save, free, then sim psi_p12.
            t1 = time.time()
            psi_base = state_vector_at(base, L1, L2, dtype)
            t2 = time.time()
            S_base = entropy_of_v_D(psi_base, dtype)
            n_base = float(np.linalg.norm(psi_base))
            stage_path = tmpdir / f"psi_base_{base}.npy"
            np.save(stage_path, psi_base)
            del psi_base
            gc.collect()
            print(f"  staged psi(base) -> {stage_path.name} ({stage_path.stat().st_size/1e9:.2f} GB)")

            psi_p12 = state_vector_at(base + 12, L1, L2, dtype)
            t3 = time.time()
            S_p12 = entropy_of_v_D(psi_p12, dtype)
            S_delta = abs(S_base - S_p12)
            n_p12 = float(np.linalg.norm(psi_p12))

            # Stream the diff against the on-disk psi_base
            psi_base_mmap = np.load(stage_path, mmap_mode="r")
            diff_L2, diff_max = chunked_L2_and_max(psi_p12, psi_base_mmap)
            del psi_p12, psi_base_mmap
            gc.collect()
            stage_path.unlink()
        else:
            t1 = time.time()
            psi_base = state_vector_at(base, L1, L2, dtype)
            t2 = time.time()
            psi_p12 = state_vector_at(base + 12, L1, L2, dtype)
            t3 = time.time()

            diff = psi_base - psi_p12
            diff_L2 = float(np.linalg.norm(diff))
            diff_max = float(np.max(np.abs(diff)))
            del diff
            S_base = entropy_of_v_D(psi_base, dtype)
            S_p12 = entropy_of_v_D(psi_p12, dtype)
            S_delta = abs(S_base - S_p12)
            n_base = float(np.linalg.norm(psi_base))
            n_p12 = float(np.linalg.norm(psi_p12))
            del psi_base, psi_p12
            gc.collect()

        rec = {
            "base_offset": base,
            "compare_offset": base + 12,
            "psi_diff_L2": diff_L2,
            "psi_diff_max": diff_max,
            "norm_base": n_base,
            "norm_p12": n_p12,
            "S_base": S_base,
            "S_p12": S_p12,
            "S_delta": S_delta,
            "sim_s_base": t2 - t1,
            "sim_s_p12": t3 - t2,
        }
        results.append(rec)

        print(f"  norm psi(base)        = {n_base:.16f}")
        print(f"  norm psi(base+12)     = {n_p12:.16f}")
        print(f"  ||psi(b) - psi(b+12)||_L2 = {diff_L2:.3e}")
        print(f"  max|psi diff component|   = {diff_max:.3e}")
        print(f"  S(base)               = {S_base:.16f}")
        print(f"  S(base+12)            = {S_p12:.16f}")
        print(f"  |S delta|             = {S_delta:.3e}")
        print(f"  sim runtimes          = {t2-t1:.1f} s + {t3-t2:.1f} s")

    total = time.time() - t_start
    print(f"\n{'-'*40}\nTotal runtime: {total:.1f} s")

    # Headline numbers
    print(f"\n{'='*72}")
    print(f"HEADLINE: max ||psi diff||_L2 across {len(results)} base offsets")
    print(f"          = {max(r['psi_diff_L2'] for r in results):.3e}")
    print(f"          max |S delta|")
    print(f"          = {max(r['S_delta'] for r in results):.3e}")
    machine_eps = 2.22e-16 if dtype == np.complex128 else 1.19e-7
    print(f"          float machine eps for {state_dtype}: ~{machine_eps:.2e}")
    print("=" * 72)

    out = {
        "timestamp": datetime.now().isoformat(),
        "dtype": state_dtype,
        "n_qubits": N_QUBITS,
        "T_CYCLE": T_CYCLE,
        "label_pair": list(args.label_pair),
        "n_compute": 1,
        "J_intra": 0.1,
        "J_mem": 0.5,
        "results": results,
        "total_runtime_s": total,
        "summary": {
            "max_psi_diff_L2": max(r["psi_diff_L2"] for r in results),
            "max_S_delta":     max(r["S_delta"]     for r in results),
            "machine_eps":     machine_eps,
        },
    }

    out_path = (HERE / "outputs" / (
        args.out or
        f"verify_period_12_{state_dtype}_"
        f"{datetime.now():%Y%m%dT%H%M%S}.json"))
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nOutput saved: {out_path}")


if __name__ == "__main__":
    main()
