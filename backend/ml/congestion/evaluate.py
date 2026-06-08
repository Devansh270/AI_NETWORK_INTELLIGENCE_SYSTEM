"""
ml/congestion/evaluate.py

Generates evaluation artifacts for the trained XGBoost congestion model:
    - Confusion matrix
    - ROC curve
    - Feature importance chart

All three saved as a single PNG to backend/ml/congestion/evaluation_plots.png.
Also prints classification report and reads metrics.json for summary.
"""

import json
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    classification_report,
    confusion_matrix,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split


FEATURE_COLS = [
    "packet_rate",
    "avg_latency_ms",
    "byte_rate",
    "flow_count",
    "tcp_ratio",
]
LABEL_COL = "congested"

MODEL_DIR = Path("backend/ml/congestion")
DATA_PATH = Path("backend/ml/data/synthetic_traffic.csv")


def evaluate():
    df = pd.read_csv(DATA_PATH)
    X = df[FEATURE_COLS].values
    y = df[LABEL_COL].values

    _, X_test, _, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = joblib.load(MODEL_DIR / "model.joblib")
    scaler = joblib.load(MODEL_DIR / "scaler.joblib")

    X_test_scaled = scaler.transform(X_test)
    y_pred = model.predict(X_test_scaled)
    y_proba = model.predict_proba(X_test_scaled)[:, 1]

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    cm = confusion_matrix(y_test, y_pred)
    disp = ConfusionMatrixDisplay(cm, display_labels=["Normal", "Congested"])
    disp.plot(ax=axes[0], colorbar=False, cmap="Blues")
    axes[0].set_title("Confusion Matrix")

    fpr, tpr, _ = roc_curve(y_test, y_proba)
    roc_auc = roc_auc_score(y_test, y_proba)
    axes[1].plot(fpr, tpr, color="darkorange", lw=2, label=f"ROC AUC = {roc_auc:.3f}")
    axes[1].plot([0, 1], [0, 1], color="navy", lw=1, linestyle="--")
    axes[1].set_xlabel("False Positive Rate")
    axes[1].set_ylabel("True Positive Rate")
    axes[1].set_title("ROC Curve")
    axes[1].legend(loc="lower right")

    importance = model.feature_importances_
    sorted_idx = np.argsort(importance)
    axes[2].barh(
        [FEATURE_COLS[i] for i in sorted_idx],
        importance[sorted_idx],
        color="steelblue",
    )
    axes[2].set_title("Feature Importance")
    axes[2].set_xlabel("Score")

    plt.tight_layout()
    output_path = MODEL_DIR / "evaluation_plots.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"Plots saved to {output_path}")

    print("\n" + "=" * 50)
    print("CLASSIFICATION REPORT")
    print("=" * 50)
    print(classification_report(y_test, y_pred, target_names=["Normal", "Congested"]))

    metrics_path = MODEL_DIR / "metrics.json"
    if metrics_path.exists():
        with open(metrics_path) as f:
            metrics = json.load(f)
        print("Saved metrics:", json.dumps(metrics, indent=2))


if __name__ == "__main__":
    evaluate()
