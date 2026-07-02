"""
app/services/metrics_service.py

Queries the /metrics/summary endpoint data from InfluxDB.
Reads from "network_traffic" (raw packets written by scapy_agent via POST /metrics).
"""

from influxdb_client import InfluxDBClient
import os
import asyncio


def _query_influx_sync(window_seconds: int = 60):
    try:
        bucket = os.getenv("INFLUXDB_BUCKET", "metrics")
        client = InfluxDBClient(
            url=os.getenv("INFLUXDB_URL", "http://localhost:8086"),
            token=os.getenv("INFLUXDB_TOKEN", ""),
            org=os.getenv("INFLUXDB_ORG", "myorg"),
        )
        query_api = client.query_api()
        org = os.getenv("INFLUXDB_ORG", "myorg")

        combined_q = f"""
        from(bucket: "{bucket}")
          |> range(start: -{window_seconds}s)
          |> filter(fn: (r) => r._measurement == "network_traffic")
          |> filter(fn: (r) => r._field == "packet_length")
          |> reduce(
              fn: (r, accumulator) => ({{
                  count: accumulator.count + 1,
                  sum: accumulator.sum + r._value
              }}),
              identity: {{count: 0, sum: 0.0}}
          )
        """

        proto_q = f"""
        from(bucket: "{bucket}")
          |> range(start: -{window_seconds}s)
          |> filter(fn: (r) => r._measurement == "network_traffic")
          |> filter(fn: (r) => r._field == "packet_length")
          |> group(columns: ["protocol"])
          |> count()
        """

        total_packets = 0
        total_bytes = 0
        for table in query_api.query(combined_q, org=org):
            for record in table.records:
                total_packets = int(record.values.get("count", 0))
                total_bytes = int(record.values.get("sum", 0))

        proto_breakdown = {}
        for table in query_api.query(proto_q, org=org):
            for record in table.records:
                proto = record.values.get("protocol", "OTHER")
                proto_breakdown[proto] = int(record.get_value() or 0)

        client.close()

        return {
            "total_packets": total_packets,
            "total_bytes": total_bytes,
            "active_flows": len(proto_breakdown),
            "packets_per_sec": round(total_packets / window_seconds, 2),
            "bytes_per_sec": round(total_bytes / window_seconds, 2),
            "proto_breakdown": proto_breakdown,
        }

    except Exception:
        return {
            "total_packets": 0,
            "total_bytes": 0,
            "active_flows": 0,
            "packets_per_sec": 0.0,
            "bytes_per_sec": 0.0,
            "proto_breakdown": {},
        }


async def get_metrics_summary(window_seconds: int = 60) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _query_influx_sync, window_seconds)
