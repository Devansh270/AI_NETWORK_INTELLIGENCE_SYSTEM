"""
AINIS FastAPI Application

Main entry point for the AINIS backend API. Wires together:
    - The FastAPI app instance with metadata
    - CORS middleware (so the React dashboard can call us)
    - Lifespan hooks for startup and shutdown
    - Routers from app/api/ (alerts, metrics)
    - Core endpoints: GET /health, GET /
    - WebSocket endpoint for real-time metrics streaming
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from app.api import alerts, metrics
from app.api.websocket_routes import router as ws_router

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

    Database engines and InfluxDB clients are initialized lazily on first use
    (see app/core/db.py and app/core/influx.py), so we don't open connections
    here. We just log lifecycle events.
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
        "http://localhost:5173",  # Vite frontend
        "http://localhost:3000",  # alternate React port
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Register API Routers
# ---------------------------------------------------------------------------
feat/endpoints
app.include_router(alerts.router)   # exposes /alerts (Bhavya)
app.include_router(metrics.router)  # exposes /metrics (Devansh)
app.include_router(ws_router)       # exposes /ws/metrics
app.include_router(alerts.router)
app.include_router(metrics.router)
develop


# ---------------------------------------------------------------------------
# Root Endpoint
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    """
    Root endpoint — confirms the server is reachable.
    """

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
feat/endpoints
    """Liveness probe. Returns 200 OK if the API process is alive."""
    return {"status": "ok", "service": "ainis-api"}

    """
    Liveness probe.
    Returns 200 OK if the API process is alive.
    """

    return {
        "status": "ok",
        "service": "ainis-api",
    }


# ---------------------------------------------------------------------------
# WebSocket Endpoint
# ---------------------------------------------------------------------------
@app.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket):
    """
    WebSocket endpoint for real-time metrics streaming.
    """

    # accept websocket connection
    await websocket.accept()

    logger.info("WebSocket client connected")

    try:
        while True:
            # temporary mock packet data
            packet_data = {
                "src_ip": "192.168.1.100",
                "dst_ip": "10.0.0.25",
                "protocol": "TCP",
                "packet_size": 512,
                "status": "live",
            }

            # send JSON data to frontend
            await websocket.send_json(packet_data)

            logger.info(f"Sent packet data: {packet_data}")

            # wait before next message
            await asyncio.sleep(2)

    except Exception as e:
        logger.error(f"WebSocket error: {e}")

    finally:
        logger.info("WebSocket client disconnected")
develop
