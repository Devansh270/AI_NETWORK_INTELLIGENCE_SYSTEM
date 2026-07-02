"""
InfluxDB client wrapper for AINIS.

This module provides MetricsClient, a thin wrapper around the official
InfluxDB Python client. It centralizes all InfluxDB I/O so the rest of
the system doesn't need to know the underlying API.

Reads configuration from environment variables (loaded from infra/.env):
    INFLUXDB_URL      - default: http://localhost:8086
    INFLUXDB_TOKEN    - required, the admin token from .env
    INFLUXDB_ORG      - default: ainis_org
    INFLUXDB_BUCKET   - default: network_metrics
"""

import os
import logging
from pathlib import Path

from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# Load .env file from the infra/ directory (same folder as this file)
ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(ENV_PATH)

# Read configuration with sensible defaults
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
INFLUXDB_TOKEN = os.getenv("DOCKER_INFLUXDB_INIT_ADMIN_TOKEN", "")
INFLUXDB_ORG = os.getenv("DOCKER_INFLUXDB_INIT_ORG", "ainis_org")
INFLUXDB_BUCKET = os.getenv("DOCKER_INFLUXDB_INIT_BUCKET", "network_metrics")

# Module-level logger — using __name__ means logs are tagged "infra.influx_client"
logger = logging.getLogger(__name__)


class MetricsClient:
    """
    Wrapper around the InfluxDB client for writing and querying network metrics.

    Implements Contract 2 from docs/architecture.md (Worker -> InfluxDB) and
    serves queries for the dashboard's historical data views.

    Usage:
        client = MetricsClient()
        client.write_packet_metric({...})
        rows = client.query_recent_packets(last_seconds=60)
        client.close()
    """

    def __init__(self):
        if not INFLUXDB_TOKEN:
            raise ValueError(
                "INFLUXDB token is missing. Check infra/.env for "
                "DOCKER_INFLUXDB_INIT_ADMIN_TOKEN."
            )

        self._client = InfluxDBClient(
            url=INFLUXDB_URL,
            token=INFLUXDB_TOKEN,
            org=INFLUXDB_ORG,
        )
        self._write_api = self._client.write_api(write_options=SYNCHRONOUS)
        self._query_api = self._client.query_api()
        logger.info(
            f"MetricsClient connected to {INFLUXDB_URL} (org={INFLUXDB_ORG}, bucket={INFLUXDB_BUCKET})")

    # -------------------------------------------------------------------------
    # WRITE METHODS
    # -------------------------------------------------------------------------

    def write_packet_metric(self, packet_data: dict) -> None:
        """
        Write one captured packet to InfluxDB.

        Expected keys in packet_data:
            src_ip          (str)  - source IP address
            dst_ip          (str)  - destination IP address
            protocol        (str)  - TCP, UDP, ICMP, OTHER
            packet_length   (int)  - size of packet in bytes
            ttl             (int)  - time-to-live
            src_port        (int, optional)
            dst_port        (int, optional)
            timestamp       (str, optional) - ISO-8601 timestamp
        """
        point = (
            Point("packet_flow")
            .tag("protocol", packet_data.get("protocol", "UNKNOWN"))
            .tag("src_ip", packet_data.get("src_ip", ""))
            .tag("dst_ip", packet_data.get("dst_ip", ""))
            .field("packet_length", int(packet_data.get("packet_length", 0)))
            .field("ttl", int(packet_data.get("ttl", 0)))
        )

        # Optional numeric fields — only add if present
        if packet_data.get("src_port") is not None:
            point = point.field("src_port", int(packet_data["src_port"]))
        if packet_data.get("dst_port") is not None:
            point = point.field("dst_port", int(packet_data["dst_port"]))

        self._write_api.write(bucket=INFLUXDB_BUCKET, record=point)

    def write_flow_summary(
        self,
        packets_per_sec: float,
        bytes_per_sec: float,
        protocol_counts: dict,
    ) -> None:
        """
        Write an aggregated flow summary (called once per 1-second window).

        Args:
            packets_per_sec  - total packets in this window
            bytes_per_sec    - total bytes in this window
            protocol_counts  - dict like {"TCP": 30, "UDP": 10, "ICMP": 2}
        """
        point = (
            Point("flow_summary")
            .field("packets_per_sec", float(packets_per_sec))
            .field("bytes_per_sec", float(bytes_per_sec))
            .field("tcp_count", int(protocol_counts.get("TCP", 0)))
            .field("udp_count", int(protocol_counts.get("UDP", 0)))
            .field("icmp_count", int(protocol_counts.get("ICMP", 0)))
        )
        self._write_api.write(bucket=INFLUXDB_BUCKET, record=point)

    # -------------------------------------------------------------------------
    # READ METHODS
    # -------------------------------------------------------------------------

    def query_recent_packets(self, last_seconds: int = 60) -> list[dict]:
        """
        Query packet_flow data from the last N seconds.

        Returns a list of dicts, one per packet, sorted newest first.
        """
        query = f"""
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: -{last_seconds}s)
          |> filter(fn: (r) => r._measurement == "packet_flow")
          |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
          |> sort(columns: ["_time"], desc: true)
          |> limit(n: 100)
        """
        result = self._query_api.query(query=query, org=INFLUXDB_ORG)

        rows = []
        for table in result:
            for record in table.records:
                rows.append({
                    "time": record.get_time().isoformat(),
                    "protocol": record.values.get("protocol", ""),
                    "src_ip": record.values.get("src_ip", ""),
                    "dst_ip": record.values.get("dst_ip", ""),
                    "packet_length": record.values.get("packet_length"),
                    "ttl": record.values.get("ttl"),
                })
        return rows

    # -------------------------------------------------------------------------
    # LIFECYCLE
    # -------------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying InfluxDB connection. Call when done."""
        self._client.close()
        logger.info("MetricsClient connection closed")
