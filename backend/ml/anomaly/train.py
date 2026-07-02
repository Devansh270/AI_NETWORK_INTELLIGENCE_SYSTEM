"""
ml/anomaly/train.py

Trains an LSTM autoencoder on NORMAL network traffic windows.
The model learns to reconstruct normal patterns; high reconstruction error
at inference time = anomaly.

Reads: backend/ml/data/synthetic_traffic.csv
Saves: backend/ml/anomaly/lstm_best.pt
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset

# Allow importing the LSTM architecture from sibling module
sys.path.append(str(Path(__file__).resolve().parents[2]))
from lstm_autoencoder import LSTMAutoencoder


# Config
SEQ_LEN = 30
INPUT_SIZE = 5
HIDDEN_SIZE = 64
BATCH_SIZE = 32
EPOCHS = 50
LR = 1e-3
PATIENCE = 7

ANOMALY_DIR = Path(__file__).resolve().parent
CHECKPOINT = ANOMALY_DIR / "lstm_best.pt"
SCALER_PATH = ANOMALY_DIR / "scaler.joblib"
CSV_PATH = Path(__file__).resolve().parents[1] / "data" / "synthetic_traffic.csv"

FEATURE_COLS = [
    "packet_rate",
    "avg_latency",
    "byte_rate",
    "flow_count",
    "tcp_ratio",
]
LABEL_COL = "congested"


def load_normal_data(csv_path: Path) -> np.ndarray:
    """Load only the NORMAL (congested=0) rows for training."""
    df = pd.read_csv(csv_path)
    normal = df[df[LABEL_COL] == 0][FEATURE_COLS].values
    print(f"Loaded {len(normal)} normal samples from {csv_path.name}")
    return normal


def make_sequences(data: np.ndarray, seq_len: int) -> np.ndarray:
    """Build overlapping sliding windows of shape (n_seq, seq_len, n_features)."""
    seqs = []
    for i in range(len(data) - seq_len):
        seqs.append(data[i:i + seq_len])
    return np.array(seqs)


def train():
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found at {CSV_PATH}. Run ml/data/generator.py first."
        )

    raw = load_normal_data(CSV_PATH)

    scaler = StandardScaler()
    raw_scaled = scaler.fit_transform(raw)
    print(f"Scaled data mean: {raw_scaled.mean():.4f}, std: {raw_scaled.std():.4f}")

    sequences = make_sequences(raw_scaled, SEQ_LEN)
    print(f"Created {len(sequences)} sequences of length {SEQ_LEN}")

    # train/val split
    split = int(0.85 * len(sequences))
    train_seqs = sequences[:split]
    val_seqs = sequences[split:]

    train_tensor = torch.FloatTensor(train_seqs)
    val_tensor = torch.FloatTensor(val_seqs)

    train_loader = DataLoader(
        TensorDataset(train_tensor), batch_size=BATCH_SIZE, shuffle=True
    )
    val_loader = DataLoader(TensorDataset(val_tensor), batch_size=BATCH_SIZE)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    model = LSTMAutoencoder(input_size=INPUT_SIZE, hidden_size=HIDDEN_SIZE).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    criterion = nn.MSELoss()

    best_val_loss = float("inf")
    patience_counter = 0

    for epoch in range(1, EPOCHS + 1):
        # Train
        model.train()
        train_loss = 0.0
        for (batch,) in train_loader:
            batch = batch.to(device)
            optimizer.zero_grad()
            recon = model(batch)
            loss = criterion(recon, batch)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
        train_loss /= len(train_loader)

        # Validate
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for (batch,) in val_loader:
                batch = batch.to(device)
                recon = model(batch)
                loss = criterion(recon, batch)
                val_loss += loss.item()
        val_loss /= len(val_loader)

        print(f"Epoch {epoch:3d}/{EPOCHS} | train_loss={train_loss:.6f} | val_loss={val_loss:.6f}")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save(model.state_dict(), CHECKPOINT)
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= PATIENCE:
                print(f"Early stopping at epoch {epoch}")
                break

    # Save scaler so inference uses the same normalization
    import joblib
    joblib.dump(scaler, SCALER_PATH)

    print(f"\nTraining done. Best val_loss={best_val_loss:.6f}")
    print(f"Checkpoint -> {CHECKPOINT}")
    print(f"Scaler     -> {SCALER_PATH}")


if __name__ == "__main__":
    train()
