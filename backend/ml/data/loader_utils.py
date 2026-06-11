"""
ml/data/loader_utils.py

Public convenience functions used by training scripts and the FastAPI
inference pipeline. Keeps the rest of the codebase from importing
DataLoader directly.
"""

from pathlib import Path
import numpy as np

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

DEFAULT_CSV = BASE_DIR / "synthetic_traffic.csv"

DEFAULT_SCALER_CONGESTION = (
    BASE_DIR.parent / "congestion" / "scaler.pkl"
)

DEFAULT_SCALER_ANOMALY = (
    BASE_DIR.parent / "anomaly" / "scaler.pkl"
)


def get_training_data(
    csv_path: str | Path = DEFAULT_CSV,
    test_size: float = 0.2,
    seed: int = 42,
):
    """
    One-call function: load CSV → normalize → split.

    Returns:
        (X_train, X_test, y_train, y_test, loader)

    The loader is returned so the caller can save the scaler:
        X_train, X_test, y_train, y_test, loader = get_training_data()
        loader.save_scaler("backend/ml/congestion/scaler.pkl")
    """
    from backend.ml.data.dataloader import DataLoader

    loader = DataLoader()

    X_train, X_test, y_train, y_test = loader.load_and_split(
        str(csv_path),
        test_size=test_size,
        seed=seed,
    )

    return X_train, X_test, y_train, y_test, loader


def load_scaler(scaler_path: str | Path):
    """
    Load a saved StandardScaler from disk.
    Returns a fitted DataLoader instance ready to call .transform().
    """
    from backend.ml.data.dataloader import DataLoader

    loader = DataLoader()
    loader.load_scaler(str(scaler_path))

    return loader


def describe_dataset(csv_path: str | Path = DEFAULT_CSV) -> dict:
    """
    Returns a summary dict about the dataset.
    Used by training scripts to print a header before training starts.
    """
    import pandas as pd

    df = pd.read_csv(csv_path)

    total = len(df)

    congested = (
        int(df["congested"].sum())
        if "congested" in df.columns
        else -1
    )

    normal = total - congested if congested >= 0 else -1

    return {
        "total_rows": total,
        "congested": congested,
        "normal": normal,
        "features": [
            c for c in df.columns
            if c != "congested"
        ],
        "path": str(csv_path),
    }


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # must run generator first:
    # python backend/ml/data/generator.py

    info = describe_dataset()
    print("[loader_utils] Dataset info:", info)

    X_train, X_test, y_train, y_test, loader = get_training_data()

    print(
        f"[loader_utils] Shapes — "
        f"X_train: {X_train.shape}, "
        f"X_test: {X_test.shape}"
    )

    loader.save_scaler(str(DEFAULT_SCALER_CONGESTION))
    loader.save_scaler(str(DEFAULT_SCALER_ANOMALY))

    reloaded = load_scaler(DEFAULT_SCALER_CONGESTION)

    sample = np.array(
        [[100.0, 20.0, 5000.0, 3.0, 0.7, 0.2, 0.1]],
        dtype=np.float32,
    )

    print(
        "[loader_utils] Reloaded scaler transform:",
        reloaded.transform(sample),
    )