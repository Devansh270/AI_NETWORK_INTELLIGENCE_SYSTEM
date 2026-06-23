"""
app/services/feature_aggregator.py

Converts raw network_traffic points into network_metrics feature windows.

Every 5 seconds:
  1. Reads last 30s of raw "network_traffic" from InfluxDB
  2. Computes: packet_rate, avg_latency, byte_rate, flow_count, tcp_ratio
  3. Writes one "network_metrics" point back to InfluxDB
  4. Publishes the feature vector to Redis "features" channel

inference_scheduler.py reads "network_metrics" - this feeds it.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger("ainis.aggregator")

AGGREGATION_INTERVAL = 5
WINDOW_SECONDS = 30


def _compute_features(records: list) -> dict:
    if not records:
        return None

    n = len(records)
    time_span = max(WINDOW_SECONDS, 1)
    total_bytes = sum(r.get("packet_length", 0) for r in records)
    packet_rate = round(n / time_span, 4)
    byte_rate = round(total_bytes / time_span, 4)

    avg_pkt_size = total_bytes / n if n > 0 else 0
    avg_latency = round(max(1.0, avg_pkt_size * 0.05), 4)

    flows = set((r.get("src_ip", ""), r.get("dst_ip", "")) for r in records)
    flow_count = len(flows)

    protocols = [r.get("protocol", "OTHER") for r in records]
    tcp_ratio = round(protocols.count("TCP") / n, 4) if n > 0 else 0.0

    return {
        "packet_rate": packet_rate,
        "avg_latency": avg_latency,
        "byte_rate": byte_rate,
        "flow_count": float(flow_count),
        "tcp_ratio": tcp_ratio,
    }


def _query_raw_packets(influx_client, bucket: str, org: str) -> list:
    try:
        query = f"""
        from(bucket: "{bucket}")
          |> range(start: -{WINDOW_SECONDS}s)
          |> filter(fn: (r) => r._measurement == "network_traffic")
          |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
        """
        tables = influx_client.query_api().query(query=query, org=org)
        records = []
        for table in tables:
            for row in table.records:
                records.append(
                    {
                        "packet_length": int(row.values.get("packet_length") or 0),
                        "src_port": int(row.values.get("src_port") or 0),
                        "dst_port": int(row.values.get("dst_port") or 0),
                        "protocol": str(row.values.get("protocol") or "OTHER"),
                        "src_ip": str(row.values.get("src_ip") or ""),
                        "dst_ip": str(row.values.get("dst_ip") or ""),
                    }
                )
        return records
    except Exception as e:
        logger.warning(f"[aggregator] InfluxDB raw query failed: {e}")
        return []


def _write_network_metrics(
    influx_client, bucket: str, org: str, features: dict
) -> None:
    try:
        from influxdb_client import Point
        from influxdb_client.client.write_api import SYNCHRONOUS

        write_api = influx_client.write_api(write_options=SYNCHRONOUS)
        point = (
            Point("network_metrics")
            .field("packet_rate", features["packet_rate"])
            .field("avg_latency", features["avg_latency"])
            .field("byte_rate", features["byte_rate"])
            .field("flow_count", features["flow_count"])
            .field("tcp_ratio", features["tcp_ratio"])
            .time(datetime.now(timezone.utc))
        )
        write_api.write(bucket=bucket, org=org, record=point)
        logger.info(
            f"[aggregator] Wrote network_metrics: "
            f"pkt_rate={features['packet_rate']:.2f} "
            f"byte_rate={features['byte_rate']:.0f} "
            f"flows={int(features['flow_count'])} "
            f"tcp={features['tcp_ratio']:.2f}"
        )
    except Exception as e:
        logger.error(f"[aggregator] InfluxDB write failed: {e}")


async def run_feature_aggregation_loop(app_state: dict) -> None:
    influx_client = app_state["influx_client"]
    redis_client = app_state["redis_client"]
    settings = app_state["settings"]
    bucket = getattr(settings, "influxdb_bucket", "metrics")
    org = getattr(settings, "influxdb_org", "myorg")

    logger.info("[aggregator] Feature aggregation loop starting.")

    while True:
        try:
            await asyncio.sleep(AGGREGATION_INTERVAL)

            records = _query_raw_packets(influx_client, bucket, org)
            features = _compute_features(records)

            if features is None:
                logger.debug("[aggregator] No packets in window, skipping write.")
                continue

            _write_network_metrics(influx_client, bucket, org, features)

            await redis_client.publish(
                "features",
                json.dumps(
                    {
                        **features,
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "n_pkts": len(records),
                    }
                ),
            )

        except asyncio.CancelledError:
            logger.info("[aggregator] Feature aggregation loop cancelled.")
            break
        except Exception as e:
            logger.error(f"[aggregator] Unexpected error: {e}")
            await asyncio.sleep(AGGREGATION_INTERVAL)
