"""
app/api/topology.py - GET /topology endpoint
"""

from fastapi import APIRouter
import os

router = APIRouter(prefix="/topology", tags=["topology"])

STATIC_NODES = [
    {"id": "h1", "label": "h1", "type": "host", "ip": "10.0.0.1"},
    {"id": "h2", "label": "h2", "type": "host", "ip": "10.0.0.2"},
    {"id": "h3", "label": "h3", "type": "host", "ip": "10.0.0.3"},
    {"id": "h4", "label": "h4", "type": "host", "ip": "10.0.0.4"},
    {"id": "s1", "label": "s1", "type": "switch", "ip": ""},
]

STATIC_EDGES = [
    {"id": "h1-s1", "source": "h1", "target": "s1", "bw_mbps": 10, "delay": "5ms"},
    {"id": "h2-s1", "source": "h2", "target": "s1", "bw_mbps": 10, "delay": "2ms"},
    {"id": "h3-s1", "source": "h3", "target": "s1", "bw_mbps": 10, "delay": "2ms"},
    {"id": "h4-s1", "source": "h4", "target": "s1", "bw_mbps": 10, "delay": "2ms"},
]


def _get_utilization() -> dict:
    try:
        from influxdb_client import InfluxDBClient

        client = InfluxDBClient(
            url=os.getenv("INFLUXDB_URL", "http://localhost:8086"),
            token=os.getenv("INFLUXDB_TOKEN", ""),
            org=os.getenv("INFLUXDB_ORG", "myorg"),
        )
        bucket = os.getenv("INFLUXDB_BUCKET", "metrics")
        org = os.getenv("INFLUXDB_ORG", "myorg")
        query = (
            f'from(bucket: "{bucket}")'
            " |> range(start: -30s)"
            ' |> filter(fn: (r) => r._measurement == "network_traffic")'
            ' |> filter(fn: (r) => r._field == "packet_length")'
            ' |> group(columns: ["src_ip"])'
            " |> sum()"
        )
        tables = client.query_api().query(query, org=org)
        totals = {}
        for table in tables:
            for record in table.records:
                src = record.values.get("src_ip", "")
                totals[src] = totals.get(src, 0) + (record.get_value() or 0)
        client.close()
        max_val = max(totals.values(), default=1) or 1
        util = {}
        for edge in STATIC_EDGES:
            src_node = edge["source"]
            src_ip = next((n["ip"] for n in STATIC_NODES if n["id"] == src_node), "")
            util[edge["id"]] = round(min(totals.get(src_ip, 0) / max_val, 1.0), 3)
        return util
    except Exception:
        return {e["id"]: 0.0 for e in STATIC_EDGES}


@router.get("")
async def get_topology():
    utilization = _get_utilization()
    edges_with_util = []
    for edge in STATIC_EDGES:
        e = dict(edge)
        e["utilization"] = utilization.get(edge["id"], 0.0)
        edges_with_util.append(e)
    return {"nodes": STATIC_NODES, "edges": edges_with_util}
