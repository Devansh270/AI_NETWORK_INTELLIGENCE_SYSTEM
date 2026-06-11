import pandas as pd
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, roc_auc_score
import xgboost as xgb
import joblib
import json
import os

DATA_PATH = "ml/data/synthetic_traffic.csv"
MODEL_DIR = "ml/congestion"


def train():
    # Load dataset
    df = pd.read_csv(DATA_PATH)

    print(f"Dataset shape: {df.shape}")
    print("\nLabel distribution:")
    print(df["congested"].value_counts())

    # Use columns that actually exist in synthetic_traffic.csv
    feature_cols = [
        "packet_rate",
        "avg_latency",
        "byte_rate",
        "flow_count",
        "tcp_ratio",
    ]

    X = df[feature_cols].values
    y = df["congested"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    scaler = StandardScaler()

    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    param_grid = {
        "max_depth": [3, 5, 7],
        "learning_rate": [0.05, 0.1, 0.2],
        "n_estimators": [100, 200],
        "subsample": [0.8, 1.0],
    }

    model = xgb.XGBClassifier(
        eval_metric="logloss",
        random_state=42,
    )

    grid = GridSearchCV(
        estimator=model,
        param_grid=param_grid,
        cv=3,
        scoring="f1",
        verbose=1,
        n_jobs=-1,
    )

    print("\nStarting Grid Search...")
    grid.fit(X_train_scaled, y_train)

    best_model = grid.best_estimator_

    print("\nBest Parameters:")
    print(grid.best_params_)

    y_pred = best_model.predict(X_test_scaled)
    y_proba = best_model.predict_proba(X_test_scaled)[:, 1]

    report = classification_report(
        y_test,
        y_pred,
        output_dict=True,
    )

    roc_auc = roc_auc_score(y_test, y_proba)

    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))

    print(f"\nROC-AUC: {roc_auc:.4f}")

    os.makedirs(MODEL_DIR, exist_ok=True)

    joblib.dump(best_model, f"{MODEL_DIR}/model.joblib")
    joblib.dump(scaler, f"{MODEL_DIR}/scaler.joblib")

    metrics = {
        "best_params": grid.best_params_,
        "accuracy": round(report["accuracy"], 4),
        "precision": round(report["1"]["precision"], 4),
        "recall": round(report["1"]["recall"], 4),
        "f1_score": round(report["1"]["f1-score"], 4),
        "roc_auc": round(roc_auc, 4),
    }

    with open(f"{MODEL_DIR}/metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    print("\nArtifacts saved:")
    print(f"Model   -> {MODEL_DIR}/model.joblib")
    print(f"Scaler  -> {MODEL_DIR}/scaler.joblib")
    print(f"Metrics -> {MODEL_DIR}/metrics.json")


if __name__ == "__main__":
    train()