"""
ml/data/dataloader.py

Training data utility.

Loads the synthetic CSV, normalizes features with StandardScaler,
and produces train/test splits ready for model training.

Also handles saving and loading the fitted scaler so that the
same normalization is applied during live inference.

Usage:
    loader = DataLoader()
    X_train, X_test, y_train, y_test = loader.load_and_split(
        "backend/ml/data/synthetic_traffic.csv"
    )
    loader.save_scaler("backend/ml/congestion/scaler.pkl")
"""

import numpy as np
import joblib
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from backend.ml.data.feature_extractor import FeatureExtractor


class DataLoader:

    def __init__(self):
        self.scaler = StandardScaler()
        self.extractor = FeatureExtractor()
        self._fitted = False

    def load_and_split(
        self,
        csv_path: str,
        test_size: float = 0.2,
        seed: int = 42,
    ):
        """
        Load CSV, normalize features, split into train/test.

        Returns:
            X_train, X_test, y_train, y_test  (all np.ndarray)
        """
        df = self.extractor.from_csv(csv_path)
        X, y = self.extractor.get_Xy(df)

        # Fit scaler on full dataset BEFORE split so it sees all variation,
        # then transform. In production you'd fit only on train — this is fine
        # for synthetic data where the distribution is known and fixed.
        X_scaled = self.scaler.fit_transform(X)
        self._fitted = True

        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y,
            test_size=test_size,
            random_state=seed,
            stratify=y,   # preserve congested/normal ratio in both splits
        )

        print(f"[dataloader] Train: {X_train.shape[0]} | Test: {X_test.shape[0]}")
        print(f"[dataloader] Train congested: {y_train.sum()} | Test congested: {y_test.sum()}")

        return X_train, X_test, y_train, y_test

    def transform(self, X: np.ndarray) -> np.ndarray:
        """
        Apply the fitted scaler to new data (used at inference time).
        Raises if scaler has not been fitted yet.
        """
        if not self._fitted:
            raise RuntimeError(
                "Scaler not fitted. Call load_and_split() or load_scaler() first."
            )
        return self.scaler.transform(X)

    def save_scaler(self, path: str) -> None:
        """Persist the fitted scaler to disk."""
        if not self._fitted:
            raise RuntimeError("Cannot save unfitted scaler.")
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.scaler, out)
        print(f"[dataloader] Scaler saved to {out}")

    def load_scaler(self, path: str) -> None:
        """Load a previously saved scaler from disk."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Scaler not found: {p}")
        self.scaler = joblib.load(p)
        self._fitted = True
        print(f"[dataloader] Scaler loaded from {p}")


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    loader = DataLoader()
    X_train, X_test, y_train, y_test = loader.load_and_split(
        "backend/ml/data/synthetic_traffic.csv"
    )
    print(f"[dataloader] X_train dtype: {X_train.dtype}")
    print(f"[dataloader] Sample scaled row: {X_train[0]}")

    # verify transform works on a single vector
    import numpy as np
    single = np.array([[100.0, 20.0, 5000.0, 3.0, 0.7, 0.2, 0.1]], dtype=np.float32)
    scaled = loader.transform(single)
    print(f"[dataloader] Single vector scaled: {scaled}")