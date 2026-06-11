import joblib
import numpy as np
from pathlib import Path

MODEL_PATH = Path(__file__).parent / "model.joblib"
SCALER_PATH = Path(__file__).parent / "scaler.joblib"


class CongestionPredictor:
    def __init__(self):
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"Model not found: {MODEL_PATH}")

        if not SCALER_PATH.exists():
            raise FileNotFoundError(f"Scaler not found: {SCALER_PATH}")

        self.model = joblib.load(MODEL_PATH)
        self.scaler = joblib.load(SCALER_PATH)

        self.feature_names = [
            "packet_rate",
            "avg_latency",
            "byte_rate",
            "flow_count",
            "tcp_ratio",
        ]

    def _validate_features(self, features: dict) -> np.ndarray:
        missing = [f for f in self.feature_names if f not in features]

        if missing:
            raise ValueError(f"Missing features: {missing}")

        return np.array([[features[f] for f in self.feature_names]])

    def predict(self, features: dict) -> int:
        X = self._validate_features(features)

        X_scaled = self.scaler.transform(X)

        prediction = self.model.predict(X_scaled)

        return int(prediction[0])

    def predict_proba(self, features: dict) -> float:
        X = self._validate_features(features)

        X_scaled = self.scaler.transform(X)

        probability = self.model.predict_proba(X_scaled)

        return float(probability[0][1])

    def predict_with_confidence(self, features: dict) -> dict:
        probability = self.predict_proba(features)

        prediction = 1 if probability >= 0.5 else 0

        return {
            "prediction": prediction,
            "probability": round(probability, 4),
            "label": "CONGESTED" if prediction else "NORMAL",
        }


_predictor_instance = None


def get_predictor():
    global _predictor_instance

    if _predictor_instance is None:
        _predictor_instance = CongestionPredictor()

    return _predictor_instance
