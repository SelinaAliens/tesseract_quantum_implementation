#!/usr/bin/env python3
"""
Protocol 4S-Tunnel noise-variety stress test.

The tunnel result used uniform depolarizing noise. Real superconducting
hardware has other decoherence channels. Stress-test:

  - Uniform depolarizing (baseline)       p = 0.005 per 2q gate
  - Amplitude damping (T1 decay)          gamma = 0.005 per 2q gate
  - Phase damping (T2 dephasing)          lambda = 0.005 per 2q gate
  - Combined amp + phase damping          both 0.005
  - FakeSherbrooke calibrated noise       IBM Eagle r3 production
                                          calibration (T1, T2,
                                          per-qubit per-gate errors)

Measure the (beta, gamma) vs (gamma, beta) directional tunnel gap
at n = 2, J = 0.1 for each channel. The paper's central claim is
that the directional signal survives *realistic* hardware noise --
this experiment quantifies what "realistic" means.

Usage: python stress_test_noise_aer.py
"""
import argparse
import json
import math
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from qiskit import transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import (
    NoiseModel, depolarizing_error,
    amplitude_damping_error, phase_damping_error,
)

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))
from run_p4s_tunnel_aer import build_tunnel_snapshot, T_CYCLE
from run_p4s_aer import overlap_from_swap, zeros_from_counts
from run_p4s_Z3_three_aer import z3_eigenstate

RESULTS_DIR = SCRIPT_DIR.parent / "results"

ONE_Q = ["id", "x", "y", "z", "h", "s", "sdg", "t", "tdg",
         "rx", "ry", "rz", "u", "u1", "u2", "u3", "sx", "sxdg"]
TWO_Q = ["cx", "cz", "swap", "ecr", "iswap"]


def build_noise_model(kind: str, p: float) -> NoiseModel:
    """Construct a NoiseModel for one noise-channel type."""
    nm = NoiseModel()
    if kind == "depolarizing":
        nm.add_all_qubit_quantum_error(depolarizing_error(0.1 * p, 1), ONE_Q)
        nm.add_all_qubit_quantum_error(depolarizing_error(p, 2), TWO_Q)
        nm.add_all_qubit_quantum_error(depolarizing_error(1.5 * p, 3), ["cswap", "ccx"])
    elif kind == "amp_damp":
        # amp damping on each qubit of each gate. Arity-scaled.
        nm.add_all_qubit_quantum_error(amplitude_damping_error(0.1 * p), ONE_Q)
        err2 = amplitude_damping_error(p).tensor(amplitude_damping_error(p))
        nm.add_all_qubit_quantum_error(err2, TWO_Q)
    elif kind == "phase_damp":
        nm.add_all_qubit_quantum_error(phase_damping_error(0.1 * p), ONE_Q)
        err2 = phase_damping_error(p).tensor(phase_damping_error(p))
        nm.add_all_qubit_quantum_error(err2, TWO_Q)
    elif kind == "amp_and_phase":
        # both simultaneously on each qubit
        e1 = amplitude_damping_error(0.1 * p).compose(phase_damping_error(0.1 * p))
        nm.add_all_qubit_quantum_error(e1, ONE_Q)
        e2_single = amplitude_damping_error(p).compose(phase_damping_error(p))
        err2 = e2_single.tensor(e2_single)
        nm.add_all_qubit_quantum_error(err2, TWO_Q)
    else:
        raise ValueError(f"unknown noise kind: {kind}")
    return nm


def make_simulator(config):
    """config is ('depol', p), ('amp_damp', p), etc., or ('fake', backend_name)."""
    kind = config[0]
    if kind == "ideal":
        return AerSimulator()
    if kind == "fake":
        from qiskit_ibm_runtime.fake_provider import FakeProviderForBackendV2
        provider = FakeProviderForBackendV2()
        target = f"fake_{config[1].lower()}"
        for b in provider.backends():
            if b.name == target:
                return AerSimulator.from_backend(b)
        raise ValueError(f"backend not found: {target}")
    return AerSimulator(noise_model=build_noise_model(kind, config[1]))


BASIS = ["id", "rz", "sx", "x", "cx", "cz", "ecr"]


def _transpile(qc, sim, use_backend_calibration):
    if use_backend_calibration:
        return transpile(qc, backend=sim, optimization_level=1)
    return transpile(qc, basis_gates=BASIS, optimization_level=1)


def measure_directional_gap(config, n_repeats=6, shots=4096, n_periods=2, J=0.1):
    beta  = z3_eigenstate(1)
    gamma = z3_eigenstate(2)
    sim = make_simulator(config)
    use_cal = (config[0] == "fake")

    def run_one(uA, vA, uB, vB):
        vals = []
        for _ in range(n_repeats):
            qc = build_tunnel_snapshot(uA, vA, uB, vB,
                                       steps_so_far=n_periods * T_CYCLE,
                                       which="tunnel", J=J)
            tqc = _transpile(qc, sim, use_cal)
            res = sim.run(tqc, shots=shots).result()
            counts = res.get_counts()
            vals.append(overlap_from_swap(zeros_from_counts(counts), shots))
        return np.array(vals)

    bg = run_one(beta, beta, gamma, gamma)
    gb = run_one(gamma, gamma, beta, beta)
    bg_mean = float(np.mean(bg)); gb_mean = float(np.mean(gb))
    bg_sem  = float(np.std(bg, ddof=1) / math.sqrt(n_repeats))
    gb_sem  = float(np.std(gb, ddof=1) / math.sqrt(n_repeats))
    gap     = bg_mean - gb_mean
    sem_tot = math.sqrt(bg_sem ** 2 + gb_sem ** 2)
    return {
        "bg_mean": bg_mean, "bg_sem": bg_sem,
        "gb_mean": gb_mean, "gb_sem": gb_sem,
        "gap":     gap,
        "sem_tot": sem_tot,
        "sigma":   gap / max(sem_tot, 1e-9),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-repeats", type=int, default=6)
    ap.add_argument("--shots",     type=int, default=4096)
    ap.add_argument("--n-periods", type=int, default=2)
    ap.add_argument("--J",         type=float, default=0.1)
    args = ap.parse_args()

    p = 0.005
    channels = [
        ("ideal",),
        ("depolarizing", p),
        ("amp_damp", p),
        ("phase_damp", p),
        ("amp_and_phase", p),
        ("fake", "sherbrooke"),
    ]

    print(f"# Noise-variety stress test | n={args.n_periods}, J={args.J}, "
          f"n_repeats={args.n_repeats}")
    print(f"{'channel':>22} | {'bg tunnel':>12} {'gb tunnel':>12} {'gap':>8} {'sigma':>8}")
    print("-" * 72)

    results = {}
    for cfg in channels:
        label = cfg[0] if len(cfg) == 1 else f"{cfg[0]}({cfg[1]})"
        r = measure_directional_gap(cfg, args.n_repeats, args.shots,
                                    args.n_periods, args.J)
        results[label] = r
        print(f"{label:>22} | {r['bg_mean']:>12.4f} {r['gb_mean']:>12.4f} "
              f"{r['gap']:>+8.4f} {r['sigma']:>+8.2f}")

    surviving = sum(1 for r in results.values() if abs(r["sigma"]) > 3)
    total = len(results)
    print(f"\n{surviving}/{total} noise channels preserve the directional signal")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "stack":     "qiskit_aer",
        "n_periods": args.n_periods,
        "J":         args.J,
        "n_repeats": args.n_repeats,
        "shots":     args.shots,
        "p_depol":   p,
        "results":   results,
        "surviving": f"{surviving}/{total}",
    }
    out = RESULTS_DIR / f"stress_noise_aer_{datetime.now():%Y%m%dT%H%M%S}.json"
    out.write_text(json.dumps(payload, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
