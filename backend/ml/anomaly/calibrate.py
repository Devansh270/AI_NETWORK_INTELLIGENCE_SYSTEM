"""
ml/anomaly/calibrate.py - one-time calibration script.

Computes baseline reconstruction-error distribution on the validation split
of normal traffic (matching what train.py used). Saves mean + std to
calibration.json so predictor.py can normalize scores against actual data
instead of a hardcoded threshold.

Run:
    cd backend
    python -m ml.anomaly.calibrate

Output:
    backend/ml/anomaly/calibration.json
"""

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch

# Make ml/ importable when run as a module
sys.path.append(str(Path(__file__).resolve().parents[2]))
from ml.anomaly.lstm_autoencoder import LSTMAutoencoder


SEQ_LEN = 30
INPUT_SIZE = 5
HIDDEN_SIZE = 64

# Mirror train.py exactly so the split matches what the model was tuned on
FEATURE_COLS = [
    "packet_rate",
    "avg_latency",
    "byte_rate",
    "flow_count",
    "tcp_ratio",
]
LABEL_COL = "congested"

ANOMALY_DIR = Path(__file__).resolve().parent
CHECKPOINT = ANOMALY_DIR / "lstm_best.pt"
SCALER_PATH = ANOMALY_DIR / "scaler.joblib"
CSV_PATH = Path(__file__).resolve().parents[1] / "data" / "synthetic_traffic.csv"
CALIBRATION_PATH = ANOMALY_DIR / "calibration.json"


def make_sequences(data: np.ndarray, seq_len: int) -> np.ndarray:
    seqs = []
    for i in range(len(data) - seq_len):
        seqs.append(data[i : i + seq_len])
    return np.array(seqs)


def main():
    print(f"Loading dataset: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)

    normal = df[df[LABEL_COL] == 0][FEATURE_COLS].values
    print(f"  {len(normal)} normal samples")

    print(f"Loading scaler: {SCALER_PATH}")
    scaler = joblib.load(SCALER_PATH)

    raw_scaled = scaler.transform(normal)
    sequences = make_sequences(raw_scaled, SEQ_LEN)
    print(f"  {len(sequences)} sequences of length {SEQ_LEN}")

    # Use the same train/val split train.py uses (85/15)
    split = int(0.85 * len(sequences))
    val_seqs = sequences[split:]
    print(f"  {len(val_seqs)} validation sequences")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    print(f"Loading model: {CHECKPOINT}")
    model = LSTMAutoencoder(input_size=INPUT_SIZE, hidden_size=HIDDEN_SIZE).to(device)
    model.load_state_dict(
        torch.load(CHECKPOINT, map_location=device, weights_only=True)
    )
    model.eval()

    # Compute reconstruction error for each validation sequence
    errors = []
    with torch.no_grad():
        for seq in val_seqs:
            tensor = torch.FloatTensor(seq).unsqueeze(0).to(device)
            recon = model(tensor)
            error = torch.mean((tensor - recon) ** 2).item()
            errors.append(error)

    errors = np.array(errors)

    calibration = {
        "baseline_error_mean": float(np.mean(errors)),
        "baseline_error_std": float(np.std(errors)),
        "baseline_error_min": float(np.min(errors)),
        "baseline_error_max": float(np.max(errors)),
        "baseline_error_p50": float(np.percentile(errors, 50)),
        "baseline_error_p95": float(np.percentile(errors, 95)),
        "baseline_error_p99": float(np.percentile(errors, 99)),
        "n_val_sequences": int(len(val_seqs)),
        "seq_len": SEQ_LEN,
        "input_size": INPUT_SIZE,
        "source_csv": str(CSV_PATH.relative_to(ANOMALY_DIR.parents[2])),
    }

    print("\nCalibration result:")
    for k, v in calibration.items():
        print(f"  {k}: {v}")

    with open(CALIBRATION_PATH, "w") as f:
        json.dump(calibration, f, indent=2)

    print(f"\nSaved -> {CALIBRATION_PATH}")
    print("\nSuggested predictor.py thresholds based on data:")
    print(f"  ANOMALY_THRESHOLD     = ~{calibration['baseline_error_p95']:.4f}  (p95)")
    print(f"  SEVERITY_CRITICAL_THRESHOLD = ~{calibration['baseline_error_p99']:.4f}  (p99)")


if __name__ == "__main__":
    main()
