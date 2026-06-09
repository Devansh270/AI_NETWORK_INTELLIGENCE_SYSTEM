import logging
import os

import joblib
import numpy as np
import torch

from ml.anomaly.lstm_autoencoder import LSTMAutoencoder

logger = logging.getLogger(__name__)

SEQ_LEN = 30
INPUT_SIZE = 5
HIDDEN_SIZE = 64

# Thresholds configurable via env vars
ANOMALY_THRESHOLD = float(os.getenv("ANOMALY_THRESHOLD", "0.05"))
SEVERITY_CRITICAL = float(os.getenv("SEVERITY_CRITICAL_THRESHOLD", "0.8"))
SEVERITY_WARNING = float(os.getenv("SEVERITY_WARNING_THRESHOLD", "0.5"))

CHECKPOINT = os.path.join(os.path.dirname(__file__), "lstm_best.pt")
SCALER_PATH = os.path.join(os.path.dirname(__file__), "scaler.joblib")


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

        logger.info(
            "AnomalyPredictor loaded",
            extra={
                "checkpoint": CHECKPOINT,
                "device": str(self.device),
                "anomaly_threshold": ANOMALY_THRESHOLD,
            },
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

        # Normalize to 0–1 relative to the threshold.
        # score < 1.0 means below threshold; score == 1.0 means at or above threshold.
        score = min(error / ANOMALY_THRESHOLD, 1.0)

        is_anomaly = error > ANOMALY_THRESHOLD

        if score >= SEVERITY_CRITICAL:
            severity = "critical"
        elif score >= SEVERITY_WARNING:
            severity = "warning"
        else:
            severity = "normal"

        return {
            "anomaly_score": round(score, 4),
            "reconstruction_error": round(error, 6),
            "is_anomaly": is_anomaly,
            "severity": severity,
        }
