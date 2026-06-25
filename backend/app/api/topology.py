"""
app/api/topology.py - GET /topology endpoint + WebSocket for live updates
"""

import json
import asyncio
import os

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect

from app.core.limiter import limiter

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
            src_ip = next((n["ip"]
                          for n in STATIC_NODES if n["id"] == src_node), "")
            util[edge["id"]] = round(
                min(totals.get(src_ip, 0) / max_val, 1.0), 3)
        return util
    except Exception:
        return {e["id"]: 0.0 for e in STATIC_EDGES}


def _build_topology() -> dict:
    """Builds the full topology payload with current utilization."""
    utilization = _get_utilization()
    edges_with_util = []
    for edge in STATIC_EDGES:
        e = dict(edge)
        e["utilization"] = utilization.get(edge["id"], 0.0)
        edges_with_util.append(e)
    return {"nodes": STATIC_NODES, "edges": edges_with_util}


@router.get("")
@limiter.limit("100/minute")
async def get_topology(request: Request):
    return _build_topology()


@router.websocket("/ws")
async def topology_ws(websocket: WebSocket):
    """Stream topology updates via WebSocket. Pushes current state on connect, then every 5 sec."""
    await websocket.accept()

    try:
        # Send initial state immediately
        initial = _build_topology()
        await websocket.send_text(json.dumps(initial))

        # Then poll + push every 5 sec
        while True:
            await asyncio.sleep(5)
            update = _build_topology()
            await websocket.send_text(json.dumps(update))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        import logging
        logging.getLogger("ainis.topology_ws").warning(f"WS ended: {e}")
