#!/usr/bin/env python3
"""Re-run Paper 34 Stage C (entropy spectrum sweep) at complex128.

Drops the cirq.Simulator default (complex64) for full double precision so
period-12 residuals tighten from ~1e-8 to ~1e-16. 324 configurations:
36 phase offsets x 9 (X,Y) input pairs in {alpha, beta, gamma}^2.

Memory: 4.3 GB state vector at complex128, ~5 GB peak resident.
Runtime: ~90-120 s per config x 324 = ~8-11 hours on a laptop.

Incremental checkpointing: writes
  outputs/stage_c_complex128_progress.json     after every config
  outputs/stage_c_complex128_FINAL.json        on clean exit
so an interrupted run can be resumed (skip configs already in progress
JSON) and partial evidence is never lost.
"""
from __future__ import annotations
import json
import sys
import time
import gc
from datetime import datetime
from pathlib import Path

import numpy as np
import cirq

HERE = Path(__file__).resolve().parent
CIRQ_DIR = HERE.parent / "cirq"
sys.path.insert(0, str(CIRQ_DIR))
from run_p4s_double_triangle_cirq import (        # type: ignore
    build_double_triangle_circuit,
    vD_full_spectrum,
    LABEL_IDX,
)

OUT_DIR = HERE / "outputs"
OUT_DIR.mkdir(exist_ok=True)
PROGRESS_PATH = OUT_DIR / "stage_c_complex128_progress.json"
FINAL_PATH    = OUT_DIR / f"stage_c_complex128_FINAL_{datetime.now():%Y%m%dT%H%M%S}.json"


def run_one_config_complex128(labels1, labels2, n_compute, J_intra, J_mem,
                                offset_T2):
    qc = build_double_triangle_circuit(
        labels1=labels1, labels2=labels2,
        n_compute=n_compute, J_intra=J_intra,
        J_mem1=J_mem, J_mem2=J_mem, offset_T2=offset_T2,
    )
    sim = cirq.Simulator(dtype=np.complex128)
    result = sim.simulate(qc)
    psi = np.asarray(result.final_state_vector).astype(np.complex128, copy=False)
    spec = vD_full_spectrum(psi)
    del psi
    gc.collect()
    # rho_Z3 is a list-of-lists of Python complex (not JSON-serializable);
    # split into real / imag arrays so the checkpoint stays JSONable.
    if "rho_Z3" in spec:
        rho = spec["rho_Z3"]
        spec["rho_Z3_real"] = [[float(c.real) for c in row] for row in rho]
        spec["rho_Z3_imag"] = [[float(c.imag) for c in row] for row in rho]
        del spec["rho_Z3"]
    return spec


def main():
    n_compute = 1
    J_intra = 0.1
    J_mem = 0.5
    offsets = list(range(36))
    refs = [(X, Y) for X in ("alpha", "beta", "gamma")
                    for Y in ("alpha", "beta", "gamma")]
    n_total = len(offsets) * len(refs)

    # Resume support: load any prior progress
    done: dict[tuple[int, str, str], dict] = {}
    records: list[dict] = []
    if PROGRESS_PATH.exists():
        prior = json.loads(PROGRESS_PATH.read_text())
        for rec in prior.get("records", []):
            key = (int(rec["offset"]), rec["X"], rec["Y"])
            done[key] = rec["spec"]
            records.append(rec)
        print(f"[resume] loaded {len(done)} prior records from {PROGRESS_PATH.name}")

    start = time.time()
    n_completed = len(done)

    print(f"Stage C @ complex128 — {n_total} configs (already done: {n_completed})")
    print(f"  J_intra = {J_intra}, J_mem = {J_mem}, n_compute = {n_compute}")
    print(f"  output:  {FINAL_PATH.name}")
    print()

    for offset in offsets:
        for X, Y in refs:
            key = (offset, X, Y)
            if key in done:
                continue
            t1 = time.time()
            labels1 = (X, X, X)
            labels2 = (Y, Y, Y)
            spec = run_one_config_complex128(
                labels1, labels2, n_compute, J_intra, J_mem, offset)
            t2 = time.time()
            n_completed += 1
            elapsed_total = time.time() - start
            done[key] = spec
            records.append({"offset": offset, "X": X, "Y": Y, "spec": spec})

            eta_s = (n_total - n_completed) * (t2 - t1)
            print(
                f"  [{n_completed:>3d}/{n_total}]  offset={offset:>2d}  "
                f"({X[:3]},{Y[:3]})  S={spec['entropy']:.10f}  "
                f"sim={t2-t1:.1f}s  eta~{eta_s/60:.0f} min"
            )
            # Incremental checkpoint after every config
            PROGRESS_PATH.write_text(json.dumps(
                {"timestamp": datetime.now().isoformat(),
                 "n_completed": n_completed,
                 "n_total": n_total,
                 "elapsed_s": elapsed_total,
                 "records": records},
                separators=(",", ":")))

    elapsed = time.time() - start
    print(f"\nDone in {elapsed/60:.1f} min")

    # Build the final structured output (mean entropy, purity, off-diag mag,
    # FFT-ready arrays)
    spectrum = {}
    for rec in records:
        spectrum.setdefault(rec["offset"], {})[(rec["X"], rec["Y"])] = rec["spec"]

    mean_entropy = {}
    for offset in offsets:
        entropies = [spectrum[offset][(X, Y)]["entropy"] for X, Y in refs]
        mean_entropy[offset] = float(np.mean(entropies))

    out = {
        "stage": "C",
        "dtype": "complex128",
        "timestamp": datetime.now().isoformat(),
        "parameters": {
            "n_compute": n_compute, "J_intra": J_intra, "J_mem": J_mem,
            "offsets": offsets, "ref_configs": refs,
        },
        "runtime_s": elapsed,
        "mean_entropy": mean_entropy,
        "spectrum": {str(o): {f"{X},{Y}": s for (X, Y), s in v.items()}
                      for o, v in spectrum.items()},
    }
    FINAL_PATH.write_text(json.dumps(out, indent=2))
    print(f"\nFinal output: {FINAL_PATH}")


if __name__ == "__main__":
    main()
