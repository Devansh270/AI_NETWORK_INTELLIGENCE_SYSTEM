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

from app.api import alerts, metrics

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
    """Startup and shutdown hooks.

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
    description="AI Network Intelligence System — real-time packet "
                "monitoring, anomaly detection, and traffic optimization.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow the React dashboard (localhost:5173) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:3000",   # alternate React port
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Register routers from app/api/
# ---------------------------------------------------------------------------
app.include_router(alerts.router)   # exposes /alerts (Bhavya)
app.include_router(metrics.router)  # exposes /metrics (Devansh)


# ---------------------------------------------------------------------------
# Core endpoints
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    """Root endpoint — confirms the server is reachable."""
    return {
        "service": "ainis-api",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """Liveness probe. Returns 200 OK if the API process is alive."""
    return {"status": "ok", "service": "ainis-api"}
