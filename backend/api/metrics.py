from fastapi import APIRouter, HTTPException
from app.models.metrics import NetworkMetric
from app.core.influx import get_influx_write_api

router = APIRouter(prefix="/metrics", tags=["metrics"])

@router.post("", status_code=201)
async def ingest_metric(metric: NetworkMetric):
    write_api = get_influx_write_api()
    point = (
        Point("network_traffic")
        .tag("protocol", metric.protocol)
        .tag("src_ip", metric.src_ip)
        .tag("dst_ip", metric.dst_ip)
        .field("packet_length", metric.packet_length)
        .field("src_port", metric.src_port)
        .field("dst_port", metric.dst_port)
        .time(metric.timestamp)
    )
    try:
        write_api.write(bucket="network", record=point)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "written"}