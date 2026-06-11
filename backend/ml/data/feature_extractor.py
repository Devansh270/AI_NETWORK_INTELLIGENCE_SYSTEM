import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional

FEATURE_COLS = [
    "packet_rate",
    "avg_latency_ms",
    "byte_rate",
    "flow_count",
    "tcp_ratio",
    "udp_ratio",
    "icmp_ratio",
]

LABEL_COL = "congested"


class FeatureExtractor:

    def from_csv(self, csv_path: str) -> pd.DataFrame:
        path = Path(csv_path)

        if not path.exists():
            raise FileNotFoundError(f"Dataset not found: {path}")

        df = pd.read_csv(path)

        missing = [c for c in FEATURE_COLS if c not in df.columns]

        if missing:
            raise ValueError(f"CSV missing columns: {missing}")

        return df

    def get_Xy(self, df: pd.DataFrame):
        if LABEL_COL not in df.columns:
            raise ValueError(f"Label column '{LABEL_COL}' not found.")

        X = df[FEATURE_COLS].to_numpy(dtype=np.float32)
        y = df[LABEL_COL].to_numpy(dtype=np.int32)

        return X, y

    def from_packet_window(self, packets: list[dict]) -> Optional[np.ndarray]:
        if not packets:
            return None

        n = len(packets)

        lengths = [p.get("length", 0) for p in packets]
        protocols = [p.get("protocol", "OTHER").upper() for p in packets]

        timestamps = [p.get("timestamp", 0.0) for p in packets]

        if len(timestamps) > 1:
            time_span = max(timestamps) - min(timestamps)
        else:
            time_span = 1.0

        time_span = max(time_span, 1.0)

        packet_rate = n / time_span
        byte_rate = sum(lengths) / time_span

        avg_latency_ms = max(1.0, (byte_rate / max(packet_rate, 1)) * 0.05)

        flows = set((p.get("src_ip", ""), p.get("dst_ip", "")) for p in packets)

        flow_count = len(flows)

        tcp_count = protocols.count("TCP")
        udp_count = protocols.count("UDP")
        icmp_count = protocols.count("ICMP")

        tcp_ratio = tcp_count / n
        udp_ratio = udp_count / n
        icmp_ratio = icmp_count / n

        vector = np.array(
            [
                [
                    packet_rate,
                    avg_latency_ms,
                    byte_rate,
                    float(flow_count),
                    tcp_ratio,
                    udp_ratio,
                    icmp_ratio,
                ]
            ],
            dtype=np.float32,
        )

        return vector

    def get_feature_names(self):
        return FEATURE_COLS.copy()


if __name__ == "__main__":

    extractor = FeatureExtractor()

    mock_packets = [
        {
            "protocol": "TCP",
            "length": 1500,
            "src_ip": "10.0.0.1",
            "dst_ip": "10.0.0.2",
            "timestamp": 1000.0,
        },
        {
            "protocol": "UDP",
            "length": 500,
            "src_ip": "10.0.0.3",
            "dst_ip": "10.0.0.4",
            "timestamp": 1002.0,
        },
        {
            "protocol": "ICMP",
            "length": 64,
            "src_ip": "10.0.0.1",
            "dst_ip": "10.0.0.2",
            "timestamp": 1004.0,
        },
    ]

    vec = extractor.from_packet_window(mock_packets)

    print("[extractor] Feature names:")
    print(extractor.get_feature_names())

    print("\n[extractor] Vector shape:")
    print(vec.shape)

    print("\n[extractor] Vector:")
    print(vec)
