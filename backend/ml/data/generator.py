"""
ml/data/generator.py

Generates a synthetic labeled dataset for training the congestion predictor.
Each row represents one 5-second aggregation window of network traffic.

Features:
    packet_rate     - packets per second in this window
    avg_latency_ms  - simulated average round-trip latency
    byte_rate       - bytes per second
    flow_count      - number of distinct src_ip:dst_ip pairs
    tcp_ratio       - fraction of traffic that is TCP (0.0-1.0)
    udp_ratio       - fraction of traffic that is UDP (0.0-1.0)
    icmp_ratio      - fraction that is ICMP (0.0-1.0)

Label:
    congested       - 1 if the window is congested, 0 if normal
"""

import numpy as np
import pandas as pd
from pathlib import Path


def generate_dataset(n_samples: int = 12000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    # Generate NORMAL traffic (70% of dataset)
    n_normal = int(n_samples * 0.70)

    normal = pd.DataFrame({
        "packet_rate":    rng.uniform(10,  300,  n_normal),
        "avg_latency_ms": rng.uniform(1,   50,   n_normal),
        "byte_rate":      rng.uniform(500, 50_000, n_normal),
        "flow_count":     rng.integers(1,  20,   n_normal),
        "tcp_ratio":      rng.uniform(0.5, 0.9,  n_normal),
    })
    normal["udp_ratio"]  = rng.uniform(0.05, 0.4, n_normal)
    normal["udp_ratio"]  = np.minimum(normal["udp_ratio"], 1.0 - normal["tcp_ratio"])
    normal["icmp_ratio"] = np.maximum(0.0, 1.0 - normal["tcp_ratio"] - normal["udp_ratio"])
    normal["congested"]  = 0

    # Generate CONGESTED traffic (30% of dataset)
    n_congested = n_samples - n_normal

    congested = pd.DataFrame({
        "packet_rate":    rng.uniform(400,  2000,    n_congested),
        "avg_latency_ms": rng.uniform(80,   500,     n_congested),
        "byte_rate":      rng.uniform(80_000, 500_000, n_congested),
        "flow_count":     rng.integers(15,  100,     n_congested),
        "tcp_ratio":      rng.uniform(0.6,  1.0,     n_congested),
    })
    congested["udp_ratio"]  = rng.uniform(0.0, 0.3, n_congested)
    congested["udp_ratio"]  = np.minimum(congested["udp_ratio"], 1.0 - congested["tcp_ratio"])
    congested["icmp_ratio"] = np.maximum(0.0, 1.0 - congested["tcp_ratio"] - congested["udp_ratio"])
    congested["congested"]  = 1

    # Combine, shuffle, reset index
    df = pd.concat([normal, congested], ignore_index=True)
    df = df.sample(frac=1, random_state=seed).reset_index(drop=True)

    # round floats for readability
    float_cols = ["packet_rate", "avg_latency_ms", "byte_rate",
                  "tcp_ratio", "udp_ratio", "icmp_ratio"]
    df[float_cols] = df[float_cols].round(4)

    return df


def save_dataset(output_dir: str = "backend/ml/data") -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    df = generate_dataset()
    path = out / "synthetic_traffic.csv"
    df.to_csv(path, index=False)

    print(f"[generator] Saved {len(df)} rows to {path}")
    print(f"[generator] Congested: {df['congested'].sum()} | Normal: {(df['congested']==0).sum()}")
    print(f"[generator] Columns: {list(df.columns)}")
    return path


if __name__ == "__main__":
    save_dataset()
