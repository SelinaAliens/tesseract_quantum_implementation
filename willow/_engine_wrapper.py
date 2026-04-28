"""
Common Google Quantum Engine submission wrapper for Papers 31-35 Willow
hardware pre-registrations.

All Willow-submit scripts in this folder follow the same pattern:
  1. Import the canonical Cirq circuit builder from tesseract_quantum_implementation/cirq/
  2. Simulation path (default): run on cirq.Simulator with noise model, report pass/fail
  3. Hardware path: --project <GCP> --processor <processor_id> submits via cirq_google.Engine

The Cirq circuits in this folder are identical to the canonical simulation
circuits. No re-implementation; the hardware submission is a thin wrapper
that adds credentials and job metadata.

Pre-registration: each script has its observable's pass/fail thresholds baked
in, matching the numbers in the corresponding paper. Raw job IDs and counts
are written to outputs/ within 48 hours of any hardware run, per the Willow
pre-registration discipline (see ../willow_hardware_merkabit/README.md).
"""
import sys
from pathlib import Path
from datetime import datetime
import json

import cirq

SCRIPT_DIR = Path(__file__).parent.resolve()
CIRQ_DIR   = SCRIPT_DIR.parent / "cirq"
OUTPUTS    = SCRIPT_DIR / "outputs"
sys.path.insert(0, str(CIRQ_DIR))


def engine_submit_or_fail(project, processor, circuits, shots, job_label):
    """Submit a batch of circuits to Google Quantum Engine.

    If --project and --processor are provided, submits via cirq_google.Engine.
    Otherwise raises NotImplementedError with a clear message pointing to the
    credentials stub. The Cirq circuits are fully specified; the hardware
    path is the same protocol with engine.run_batch() substituted for
    cirq.Simulator().run().
    """
    if project is None or processor is None:
        raise NotImplementedError(
            "Hardware path requires --project <GCP_project> and --processor "
            "<Willow_processor_id>. The Cirq circuits are fully specified "
            "and no circuit modification is needed for hardware execution; "
            "the Engine submission is a one-line substitution. See README."
        )

    try:
        import cirq_google
    except ImportError:
        raise RuntimeError(
            "cirq_google is required for Willow submission. Install via "
            "'pip install cirq-google' and re-run."
        )

    # The Engine submission pattern (authentication assumed via gcloud auth
    # application-default login or GOOGLE_APPLICATION_CREDENTIALS env var)
    engine = cirq_google.Engine(project_id=project)
    # NOTE: specific processor qubit layout must be compatible with the
    # LineQubit(n) used in the Cirq circuits below. Caller is responsible
    # for ensuring processor has the required qubit count and connectivity.
    results = engine.run_batch(
        programs=circuits,
        processor_ids=[processor],
        repetitions=shots,
        job_labels=[job_label],
    )
    return results


def write_pre_registration_json(observable_name, paper_ref, predicted_thresholds,
                                  results_summary, out_dir=OUTPUTS):
    """Standard JSON output for a Willow pre-registration run (simulation or
    hardware). Includes the pre-registered thresholds alongside the actual
    measurement so pass/fail can be reconstructed from the file alone.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp":         datetime.utcnow().isoformat() + "Z",
        "observable":        observable_name,
        "paper_ref":         paper_ref,
        "thresholds":        predicted_thresholds,
        "measurement":       results_summary,
    }
    fname = f"{observable_name}_{datetime.utcnow():%Y%m%dT%H%M%S}.json"
    out_file = out_dir / fname
    out_file.write_text(json.dumps(payload, indent=2))
    return out_file


def std_argparser(observable_name, default_shots=4096):
    """Return a ready-made argparser for Willow observable scripts."""
    import argparse
    ap = argparse.ArgumentParser(description=f"Willow submit: {observable_name}")
    ap.add_argument("--sim-only", action="store_true",
                     help="run on cirq.Simulator only (no hardware)")
    ap.add_argument("--project",   default=None,
                     help="GCP project ID for Google Quantum Engine")
    ap.add_argument("--processor", default=None,
                     help="Willow processor ID (e.g., 'willow_rainbow')")
    ap.add_argument("--shots",     type=int, default=default_shots,
                     help=f"shots per circuit (default {default_shots})")
    ap.add_argument("--n-trials",  type=int, default=10,
                     help="number of independent trials (default 10)")
    return ap
