"""
AINIS FastAPI Application

Main entry point for the AINIS backend API. Wires together:
    - The FastAPI app instance with metadata
    - CORS middleware (so the React dashboard can call us)
    - Lifespan hooks for startup and shutdown
    - Routers from app/api/ (alerts, metrics)
    - Core endpoints: GET /health, GET /
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
import redis.asyncio as aioredis

from app.api import alerts, metrics
from app.api.websocket_routes import router as ws_router
from app.core.db import engine
from app.core.influx import get_influx_write_api
from app.core.config import get_settings
from app.api.predictions import router as predictions_router


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ainis.api")


# ---------------------------------------------------------------------------
# Lifespan: runs once at startup, once at shutdown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown hooks.

    DB engines and InfluxDB clients init lazily on first use,
    so we don't open connections here. Just log lifecycle events.
    """
    logger.info("AINIS API starting up...")
    yield
    logger.info("AINIS API shutting down...")


# ---------------------------------------------------------------------------
# FastAPI app instance
# ---------------------------------------------------------------------------
app = FastAPI(
    title="AINIS API",
    description=(
        "AI Network Intelligence System — real-time packet "
        "monitoring, anomaly detection, and traffic optimization."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS Middleware
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Register API Routers
# ---------------------------------------------------------------------------
app.include_router(alerts.router)   # /alerts (Bhavya)
app.include_router(metrics.router)  # /metrics (Devansh)
app.include_router(ws_router)       # /ws/metrics


# ---------------------------------------------------------------------------
# Root Endpoint
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    """Root endpoint — confirms the server is reachable."""
    return {
        "service": "ainis-api",
        "version": "0.1.0",
        "status": "running",
    }


# ---------------------------------------------------------------------------
# Health Check Endpoint
# ---------------------------------------------------------------------------
@app.get("/health")
async def health_check():
    """
    Health probe.

    Returns 200 OK if the API process is alive, plus the status
    of each dependent service (Postgres, InfluxDB, Redis).
    Individual service failures do NOT fail the endpoint —
    the dashboard uses this to show which services are down.
    """
    settings = get_settings()
    services = {}

    # ─── Postgres check ────────────────────────────────────────
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        services["postgres"] = "up"
    except Exception as e:
        logger.warning(f"Postgres health check failed: {e}")
        services["postgres"] = "down"

    # ─── InfluxDB check ────────────────────────────────────────
    try:
        client = get_influx_write_api()
        services["influxdb"] = "up" if client else "down"
    except Exception as e:
        logger.warning(f"InfluxDB health check failed: {e}")
        services["influxdb"] = "down"

    # ─── Redis check ───────────────────────────────────────────
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

app.include_router(predictions_router)