"""
app/api/health_routes.py - per-dependency health checks.

Each subroute pings one infrastructure dependency directly. The aggregate
endpoint rolls all three up into a single status payload the dashboard polls.
"""

import logging

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

import redis.asyncio as redis_async
from influxdb_client import InfluxDBClient
from sqlalchemy import text

from app.core.config import get_settings
from app.core.db import engine

router = APIRouter(prefix="/health", tags=["health"])
logger = logging.getLogger("ainis.health")


async def _check_redis() -> dict:
    settings = get_settings()
    try:
        r = redis_async.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            socket_connect_timeout=2,
        )
        pong = await r.ping()
        await r.aclose()
        return {"service": "redis", "status": "ok" if pong else "degraded"}
    except Exception as e:
        logger.warning(f"redis health check failed: {e}")
        return {"service": "redis", "status": "down", "error": str(e)}


async def _check_influx() -> dict:
    settings = get_settings()
    try:
        client = InfluxDBClient(
            url=settings.influxdb_url,
            token=settings.influxdb_token,
            org=settings.influxdb_org,
        )
        ready = client.ping()
        client.close()
        return {"service": "influxdb", "status": "ok" if ready else "degraded"}
    except Exception as e:
        logger.warning(f"influxdb health check failed: {e}")
        return {"service": "influxdb", "status": "down", "error": str(e)}


async def _check_postgres() -> dict:
    """Use the shared SQLAlchemy engine so we hit the same DB the app uses."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"service": "postgres", "status": "ok"}
    except Exception as e:
        logger.warning(f"postgres health check failed: {e}")
        return {"service": "postgres", "status": "down", "error": str(e)}


def _status_to_http_code(svc_status: str) -> int:
    return (
        status.HTTP_200_OK
        if svc_status == "ok"
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )


@router.get("/redis")
async def health_redis():
    res = await _check_redis()
    return JSONResponse(status_code=_status_to_http_code(res["status"]), content=res)


@router.get("/influx")
async def health_influx():
    res = await _check_influx()
    return JSONResponse(status_code=_status_to_http_code(res["status"]), content=res)


@router.get("/postgres")
async def health_postgres():
    res = await _check_postgres()
    return JSONResponse(status_code=_status_to_http_code(res["status"]), content=res)


@router.get("")
async def health_aggregate():
    """Single endpoint the dashboard polls - rolls up all three checks."""
    redis_res = await _check_redis()
    influx_res = await _check_influx()
    postgres_res = await _check_postgres()

    services = {
        "redis": redis_res,
        "influxdb": influx_res,
        "postgres": postgres_res,
    }

    statuses = [s["status"] for s in services.values()]
    if all(s == "ok" for s in statuses):
        overall = "ok"
    elif any(s == "down" for s in statuses):
        overall = "degraded"
    else:
        overall = "degraded"

    http_code = status.HTTP_200_OK if overall == "ok" else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=http_code,
        content={"overall": overall, "services": services},
    )
