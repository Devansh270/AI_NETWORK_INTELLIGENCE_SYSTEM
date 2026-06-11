"""
End-to-end smoke test for MetricsClient.

Run this to verify InfluxDB is reachable and the wrapper works:
    python infra/scripts/test_influx.py

Expected outcome:
    1. 5 packet metrics written
    2. 1 flow summary written
    3. Query returns the 5 packets we just wrote
"""

import sys
import time
import logging
from pathlib import Path

# Make sure Python can find the infra/ package when running from project root.
# This MUST happen before importing from `infra`.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from infra.influx_client import MetricsClient   # noqa: E402

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")


def main():
    print("=" * 60)
    print("MetricsClient smoke test")
    print("=" * 60)

    client = MetricsClient()

    # ---- 1. Write 5 test packets ----
    print("\n[1/3] Writing 5 test packets...")
    test_packets = [
        {"src_ip": "10.0.0.1", "dst_ip": "10.0.0.100", "protocol": "TCP",
         "packet_length": 100, "ttl": 64, "src_port": 50000, "dst_port": 80},
        {"src_ip": "10.0.0.2", "dst_ip": "10.0.0.100", "protocol": "UDP",
         "packet_length": 300, "ttl": 64, "src_port": 50001, "dst_port": 53},
        {"src_ip": "10.0.0.3", "dst_ip": "10.0.0.100", "protocol": "TCP",
         "packet_length": 500, "ttl": 64, "src_port": 50002, "dst_port": 443},
        {"src_ip": "10.0.0.4", "dst_ip": "10.0.0.100", "protocol": "ICMP",
         "packet_length": 700, "ttl": 64},
        {"src_ip": "10.0.0.5", "dst_ip": "10.0.0.100", "protocol": "TCP",
         "packet_length": 900, "ttl": 64, "src_port": 50004, "dst_port": 8080},
    ]
    for pkt in test_packets:
        client.write_packet_metric(pkt)
    print(f"      Wrote {len(test_packets)} packets.")

    # ---- 2. Write one aggregated flow summary ----
    print("\n[2/3] Writing one flow summary...")
    client.write_flow_summary(
        packets_per_sec=42.5,
        bytes_per_sec=65000.0,
        protocol_counts={"TCP": 30, "UDP": 10, "ICMP": 2},
    )
    print("      Wrote flow_summary.")

    # ---- 3. Query the data back ----
    print("\n[3/3] Querying the last 30 seconds of packet_flow...")
    time.sleep(1)  # give InfluxDB a moment to index
    rows = client.query_recent_packets(last_seconds=30)
    print(f"      Query returned {len(rows)} rows:")
    for row in rows:
        print(f"        {row}")

    client.close()

    print("\n" + "=" * 60)
    if len(rows) >= 5:
        print("✅  SUCCESS — wrapper works end-to-end.")
    else:
        print(
            f"⚠️  Got {len(rows)} rows, expected at least 5. Check InfluxDB.")
    print("=" * 60)


if __name__ == "__main__":
    main()
