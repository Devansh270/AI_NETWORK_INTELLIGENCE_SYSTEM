from fastapi import APIRouter, HTTPException, Query
from influxdb_client import Point

from app.models.metrics import NetworkMetric, MetricsSummary
from app.services.metrics_service import get_metrics_summary
from app.core.influx import (
    get_influx_bucket,
    get_influx_write_api,
    influx_is_configured,
)

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.post("", status_code=201)
async def ingest_metric(metric: NetworkMetric):
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

    if not influx_is_configured():
        return {
            "status": "accepted",
            "storage": "skipped",
            "reason": "influx_not_configured",
        }

    write_api = get_influx_write_api()
    try:
        write_api.write(bucket=get_influx_bucket(), record=point)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "written"}


@router.get("/summary", response_model=MetricsSummary)
async def metrics_summary(
    window: int = Query(default=60, ge=5, le=3600)
):
    """
    Returns aggregated network metrics for the last `window` seconds.
    Default window: 60 seconds.
    """
    data = await get_metrics_summary(window_seconds=window)
    return MetricsSummary(**data)