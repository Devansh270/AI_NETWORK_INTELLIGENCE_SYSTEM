"""
AINIS FastAPI Application

Wires together FastAPI app, CORS, routers, lifespan startup/shutdown,
the background inference scheduler, and the /health endpoint.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
import redis.asyncio as aioredis

from app.api import alerts, metrics
from app.api.websocket_routes import router as ws_router
from app.api.predictions import router as predictions_router
from app.api.anomaly import router as anomaly_router
from app.core.db import engine, AsyncSessionLocal
from app.core.influx import get_influx_write_api, get_influx_client
from app.core.config import get_settings
from app.api.routing import router as routing_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ainis.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AINIS API starting up...")

    settings = get_settings()

    # Redis client (shared across app)
    redis_client = aioredis.from_url(
        f"redis://{settings.redis_host}:{settings.redis_port}",
        decode_responses=True,
    )
    app.state.redis = redis_client

    # InfluxDB client (for scheduler queries)
    influx_available = False
    try:
        app.state.influx = get_influx_client()
        influx_available = True
        logger.info("InfluxDB client initialized.")
    except Exception as e:
        logger.warning(f"InfluxDB not available at startup: {e}")
        app.state.influx = None

    # Start background inference scheduler
    if influx_available:
        from app.services.inference_scheduler import run_inference_loop
        app.state.inference_task = asyncio.create_task(
            run_inference_loop({
                "influx_client":   app.state.influx,
                "session_factory": AsyncSessionLocal,
                "redis_client":    redis_client,
                "settings":        settings,
            })
        )
        logger.info("Inference scheduler started.")
    else:
        app.state.inference_task = None
        logger.warning("Inference scheduler NOT started - InfluxDB unavailable.")

    yield

    # Shutdown
    if getattr(app.state, "inference_task", None) is not None:
        app.state.inference_task.cancel()
        try:
            await app.state.inference_task
        except asyncio.CancelledError:
            pass
        logger.info("Inference scheduler stopped.")

    try:
        await redis_client.aclose()
    except Exception:
        pass

    logger.info("AINIS API shut down.")


app = FastAPI(
    title="AINIS API",
    description="AI Network Intelligence System - real-time packet monitoring, anomaly detection, and traffic optimization.",
    version="0.1.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(alerts.router)
app.include_router(metrics.router)
app.include_router(ws_router)
app.include_router(predictions_router)
app.include_router(anomaly_router)
app.include_router(routing_router)

@app.get("/")
async def root():
    return {"service": "ainis-api", "version": "0.1.0", "status": "running"}


@app.get("/health")
async def health_check():
    settings = get_settings()
    services = {}

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        services["postgres"] = "up"
    except Exception as e:
        logger.warning(f"Postgres health check failed: {e}")
        services["postgres"] = "down"

    try:
        client = get_influx_write_api()
        services["influxdb"] = "up" if client else "down"
    except Exception as e:
        logger.warning(f"InfluxDB health check failed: {e}")
        services["influxdb"] = "down"

    try:
        r = aioredis.from_url(
            f"redis://{settings.redis_host}:{settings.redis_port}",
            socket_connect_timeout=2,
        )
        await r.ping()
        await r.aclose()
        services["redis"] = "up"
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        services["redis"] = "down"

    return {
        "status": "ok",
        "service": "ainis-api",
        "version": "0.1.0",
        "services": services,
    }
