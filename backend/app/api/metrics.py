from fastapi import APIRouter, HTTPException, Query, Depends
from influxdb_client import Point
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.metrics import NetworkMetric, MetricsSummary
from app.models.network_event import NetworkEvent
from app.services.metrics_service import get_metrics_summary
from app.core.db import get_session
from app.core.influx import (
    get_influx_bucket,
    get_influx_write_api,
    influx_is_configured,
)
from app.core.metrics import packets_captured_total

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.post("", status_code=201)
async def ingest_metric(
    metric: NetworkMetric,
    db: AsyncSession = Depends(get_session),
):
    packets_captured_total.inc()
    # 1. InfluxDB (time-series store)
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

    influx_status = "skipped"
    if influx_is_configured():
        write_api = get_influx_write_api()
        try:
            write_api.write(bucket=get_influx_bucket(), record=point)
            influx_status = "written"
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"InfluxDB write failed: {e}")

    # 2. PostgreSQL (structured event log)
    postgres_status = "skipped"
    try:
        event = NetworkEvent(
            src_ip=metric.src_ip,
            dst_ip=metric.dst_ip,
            src_port=metric.src_port,
            dst_port=metric.dst_port,
            protocol=metric.protocol,
            packet_length=metric.packet_length,
        )
        db.add(event)
        await db.commit()
        postgres_status = "written"
    except Exception as e:
        # Postgres failure should not fail the whole ingestion -
        # InfluxDB write already succeeded. Log and continue.
        await db.rollback()
        import logging

        logging.getLogger("ainis.metrics").warning(f"network_events insert failed: {e}")

    return {
        "status": "written",
        "influxdb": influx_status,
        "postgres": postgres_status,
    }


@router.get("/summary", response_model=MetricsSummary)
async def metrics_summary(window: int = Query(default=60, ge=5, le=3600)):
    """
    Returns aggregated network metrics for the last `window` seconds.
    Default window: 60 seconds.
    """
    data = await get_metrics_summary(window_seconds=window)
    return MetricsSummary(**data)
