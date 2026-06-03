from influxdb_client import InfluxDBClient
import os
import asyncio


def _query_influx_sync(window_seconds: int = 60):
    """
    Query InfluxDB for aggregated metrics over the last `window_seconds`.
    Returns a MetricsSummary-compatible dict.
    This is sync because influxdb-client is sync; we'll run it in a thread.
    """

    bucket = os.getenv("INFLUXDB_BUCKET", "network")

    client = InfluxDBClient(
        url=os.getenv("INFLUXDB_URL", "http://localhost:8086"),
        token=os.getenv("INFLUXDB_TOKEN"),
        org=os.getenv("INFLUXDB_ORG"),
    )

    query_api = client.query_api()

    # Total packets in window
    total_q = f'''
    from(bucket: "{bucket}")
      |> range(start: -{window_seconds}s)
      |> filter(fn: (r) => r._measurement == "packets")
      |> filter(fn: (r) => r._field == "len")
      |> count()
      |> sum()
    '''

    # Bytes in window
    bytes_q = f'''
    from(bucket: "{bucket}")
      |> range(start: -{window_seconds}s)
      |> filter(fn: (r) => r._measurement == "packets")
      |> filter(fn: (r) => r._field == "len")
      |> sum()
    '''

    # Per-protocol breakdown
    proto_q = f'''
    from(bucket: "{bucket}")
      |> range(start: -{window_seconds}s)
      |> filter(fn: (r) => r._measurement == "packets")
      |> filter(fn: (r) => r._field == "len")
      |> group(columns: ["proto"])
      |> count()
    '''

    def safe_sum(tables):
        total = 0
        for table in tables:
            for record in table.records:
                value = record.get_value()
                if value is not None:
                    total += int(value)
        return total

    total_packets = safe_sum(query_api.query(total_q))
    total_bytes = safe_sum(query_api.query(bytes_q))

    proto_breakdown = {}

    for table in query_api.query(proto_q):
        for record in table.records:
            proto = record.values.get("proto", "OTHER")
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


async def get_metrics_summary(window_seconds: int = 60) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        _query_influx_sync,
        window_seconds,
    )