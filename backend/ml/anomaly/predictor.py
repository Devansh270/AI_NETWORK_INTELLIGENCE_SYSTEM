import torch
import numpy as np
import os
import joblib
from ml.anomaly.lstm_autoencoder import LSTMAutoencoder

SEQ_LEN = 30
INPUT_SIZE = 5
HIDDEN_SIZE = 64

# Threshold configurable via env var — default 0.05
ANOMALY_THRESHOLD = float(os.getenv("ANOMALY_THRESHOLD", "0.05"))

CHECKPOINT = os.path.join(os.path.dirname(__file__), "lstm_best.pt")
SCALER_PATH = os.path.join(os.path.dirname(__file__), "scaler.joblib")


class AnomalyPredictor:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.model = LSTMAutoencoder(input_size=INPUT_SIZE, hidden_size=HIDDEN_SIZE)

        self.model.load_state_dict(torch.load(CHECKPOINT, map_location=self.device))

        self.model.to(self.device)
        self.model.eval()

        self.scaler = joblib.load(SCALER_PATH)

        print(
            f"AnomalyPredictor loaded from {CHECKPOINT} | "
            f"threshold={ANOMALY_THRESHOLD}"
        )

    def predict(self, window: list[list[float]]) -> dict:
        """
        window: list of SEQ_LEN rows, each row has INPUT_SIZE features.
        [[packet_rate, avg_latency, byte_rate, flow_count, protocol_ratio], ...]

        Returns:
        {
            "anomaly_score": float,
            "reconstruction_error": float,
            "is_anomaly": bool,
            "severity": str
        }
        """

        if len(window) != SEQ_LEN:
            raise ValueError(
                f"Window must have exactly {SEQ_LEN} timesteps, got {len(window)}"
            )

        if len(window[0]) != INPUT_SIZE:
            raise ValueError(
                f"Each row must have {INPUT_SIZE} features, got {len(window[0])}"
            )

        # Apply same scaling used during training
        window_np = np.array(window)
        window_scaled = self.scaler.transform(window_np)

        tensor = torch.FloatTensor(window_scaled).unsqueeze(0).to(self.device)

        with torch.no_grad():
            reconstruction = self.model(tensor)

        # Mean reconstruction error
        error = torch.mean((tensor - reconstruction) ** 2).item()

        # Normalize score to 0–1
        score = min(error / (ANOMALY_THRESHOLD * 2), 1.0)

        is_anomaly = error > ANOMALY_THRESHOLD

        if score > 0.8:
            severity = "critical"
        elif score > 0.5:
            severity = "warning"
        else:
            severity = "normal"

        return {
            "anomaly_score": round(score, 4),
            "reconstruction_error": round(error, 6),
            "is_anomaly": is_anomaly,
            "severity": severity,
        }
