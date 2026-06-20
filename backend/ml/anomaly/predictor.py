import json
import logging
import os
from pathlib import Path

import joblib
import numpy as np
import torch

from ml.anomaly.lstm_autoencoder import LSTMAutoencoder

logger = logging.getLogger(__name__)

SEQ_LEN = 30
INPUT_SIZE = 5
HIDDEN_SIZE = 64

CHECKPOINT = os.path.join(os.path.dirname(__file__), "lstm_best.pt")
SCALER_PATH = os.path.join(os.path.dirname(__file__), "scaler.joblib")
CALIBRATION_PATH = Path(os.path.dirname(__file__)) / "calibration.json"

# Severity thresholds in z-score space (std devs above baseline mean).
# Tunable via env vars but defaults are based on calibration.json statistics.
SEVERITY_WARNING_Z = float(os.getenv("SEVERITY_WARNING_Z", "2.0"))   # ~p97
SEVERITY_CRITICAL_Z = float(os.getenv("SEVERITY_CRITICAL_Z", "3.0"))  # ~p99.7


class AnomalyPredictor:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.model = LSTMAutoencoder(input_size=INPUT_SIZE, hidden_size=HIDDEN_SIZE)

        # weights_only=True avoids arbitrary pickle execution (PyTorch 2.0+)
        self.model.load_state_dict(
            torch.load(CHECKPOINT, map_location=self.device, weights_only=True)
        )

        self.model.to(self.device)
        self.model.eval()

        self.scaler = joblib.load(SCALER_PATH)

        # Load calibration baseline. If missing, fall back to neutral defaults
        # (score = 0.5 for everything) and log a warning - the system stays up
        # but produces useless scores until calibrate.py is rerun.
        self.baseline_mean = 0.5
        self.baseline_std = 1e-6
        if CALIBRATION_PATH.exists():
            with open(CALIBRATION_PATH) as f:
                cal = json.load(f)
            self.baseline_mean = float(cal["baseline_error_mean"])
            self.baseline_std = float(cal["baseline_error_std"]) or 1e-6
            logger.info(
                "AnomalyPredictor loaded with calibration",
                extra={
                    "baseline_mean": self.baseline_mean,
                    "baseline_std": self.baseline_std,
                },
            )
        else:
            logger.warning(
                "calibration.json missing - run `python -m ml.anomaly.calibrate`. "
                "Scores will be uncalibrated until then."
            )

    def predict(self, window: list[list[float]]) -> dict:
        """
        window: list of SEQ_LEN rows, each row has INPUT_SIZE features.
        Expected shape: (30, 5)
        Features per row: [packet_rate, avg_latency, byte_rate, flow_count, protocol_ratio]

        Returns:
        {
            "anomaly_score": float,       # 0.0–1.0, proportional to threshold
            "reconstruction_error": float,
            "is_anomaly": bool,
            "severity": str               # "normal" | "warning" | "critical"
        }
        """
        if len(window) == 0:
            raise ValueError("Window must not be empty.")

        if len(window) != SEQ_LEN:
            raise ValueError(
                f"Window must have exactly {SEQ_LEN} timesteps, got {len(window)}"
            )

        if len(window[0]) != INPUT_SIZE:
            raise ValueError(
                f"Each row must have {INPUT_SIZE} features, got {len(window[0])}"
            )

        # Shape: (SEQ_LEN, INPUT_SIZE) — scaler expects (n_samples, n_features)
        window_np = np.array(window, dtype=np.float32)
        assert window_np.shape == (
            SEQ_LEN,
            INPUT_SIZE,
        ), f"Unexpected shape after conversion: {window_np.shape}"
        window_scaled = self.scaler.transform(window_np)

        # Add batch dimension → (1, SEQ_LEN, INPUT_SIZE)
        tensor = torch.FloatTensor(window_scaled).unsqueeze(0).to(self.device)

        with torch.no_grad():
            reconstruction = self.model(tensor)

        # Mean squared reconstruction error across all timesteps and features
        error = torch.mean((tensor - reconstruction) ** 2).item()

        # Z-score normalize against baseline computed from validation traffic.
        # z = how many std devs above the mean of normal reconstruction error.
        # Then sigmoid-squash to 0-1 so the score is a probability-like number.
        z = (error - self.baseline_mean) / self.baseline_std
        score = 1.0 / (1.0 + np.exp(-z))

        is_anomaly = z >= SEVERITY_WARNING_Z

        if z >= SEVERITY_CRITICAL_Z:
            severity = "critical"
        elif z >= SEVERITY_WARNING_Z:
            severity = "warning"
        else:
            severity = "normal"

        return {
            "anomaly_score": round(float(score), 4),
            "reconstruction_error": round(error, 6),
            "z_score": round(float(z), 4),
            "is_anomaly": bool(is_anomaly),
            "severity": severity,
        }
