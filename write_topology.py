import pathlib

content = (
    '"""\n'
    "app/api/topology.py - GET /topology endpoint\n"
    '"""\n'
    "from fastapi import APIRouter\n"
    "import os\n"
    "\n"
    'router = APIRouter(prefix="/topology", tags=["topology"])\n'
    "\n"
    "STATIC_NODES = [\n"
    '    {"id": "h1", "label": "h1", "type": "host",   "ip": "10.0.0.1"},\n'
    '    {"id": "h2", "label": "h2", "type": "host",   "ip": "10.0.0.2"},\n'
    '    {"id": "h3", "label": "h3", "type": "host",   "ip": "10.0.0.3"},\n'
    '    {"id": "h4", "label": "h4", "type": "host",   "ip": "10.0.0.4"},\n'
    '    {"id": "s1", "label": "s1", "type": "switch", "ip": ""},\n'
    "]\n"
    "\n"
    "STATIC_EDGES = [\n"
    '    {"id": "h1-s1", "source": "h1", "target": "s1", "bw_mbps": 10, "delay": "5ms"},\n'
    '    {"id": "h2-s1", "source": "h2", "target": "s1", "bw_mbps": 10, "delay": "2ms"},\n'
    '    {"id": "h3-s1", "source": "h3", "target": "s1", "bw_mbps": 10, "delay": "2ms"},\n'
    '    {"id": "h4-s1", "source": "h4", "target": "s1", "bw_mbps": 10, "delay": "2ms"},\n'
    "]\n"
    "\n"
    "\n"
    "def _get_utilization() -> dict:\n"
    "    try:\n"
    "        from influxdb_client import InfluxDBClient\n"
    "        client = InfluxDBClient(\n"
    '            url=os.getenv("INFLUXDB_URL", "http://localhost:8086"),\n'
    '            token=os.getenv("INFLUXDB_TOKEN", ""),\n'
    '            org=os.getenv("INFLUXDB_ORG", "myorg"),\n'
    "        )\n"
    '        bucket = os.getenv("INFLUXDB_BUCKET", "metrics")\n'
    '        org    = os.getenv("INFLUXDB_ORG", "myorg")\n'
    "        query = (\n"
    "            f'from(bucket: \"{bucket}\")'\n"
    '            " |> range(start: -30s)"\n'
    '            " |> filter(fn: (r) => r._measurement == \\"network_traffic\\")"\n'
    '            " |> filter(fn: (r) => r._field == \\"packet_length\\")"\n'
    '            " |> group(columns: [\\"src_ip\\"])"\n'
    '            " |> sum()"\n'
    "        )\n"
    "        tables = client.query_api().query(query, org=org)\n"
    "        totals = {}\n"
    "        for table in tables:\n"
    "            for record in table.records:\n"
    '                src = record.values.get("src_ip", "")\n'
    "                totals[src] = totals.get(src, 0) + (record.get_value() or 0)\n"
    "        client.close()\n"
    "        max_val = max(totals.values(), default=1) or 1\n"
    "        util = {}\n"
    "        for edge in STATIC_EDGES:\n"
    '            src_node = edge["source"]\n'
    '            src_ip   = next((n["ip"] for n in STATIC_NODES if n["id"] == src_node), "")\n'
    '            util[edge["id"]] = round(min(totals.get(src_ip, 0) / max_val, 1.0), 3)\n'
    "        return util\n"
    "    except Exception:\n"
    '        return {e["id"]: 0.0 for e in STATIC_EDGES}\n'
    "\n"
    "\n"
    '@router.get("")\n'
    "async def get_topology():\n"
    "    utilization = _get_utilization()\n"
    "    edges_with_util = []\n"
    "    for edge in STATIC_EDGES:\n"
    "        e = dict(edge)\n"
    '        e["utilization"] = utilization.get(edge["id"], 0.0)\n'
    "        edges_with_util.append(e)\n"
    '    return {"nodes": STATIC_NODES, "edges": edges_with_util}\n'
)

out = pathlib.Path("backend/app/api/topology.py")
out.write_text(content, encoding="utf-8")
print("topology.py written OK, size:", out.stat().st_size, "bytes")

import ast

ast.parse(content)
print("topology.py: valid Python")
