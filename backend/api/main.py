"""
AINIS FastAPI Application

This is the main entry point for the AINIS backend API. It defines:
    - The FastAPI app instance with metadata
    - CORS configuration (so the React dashboard can call us)
    - Lifespan hooks (database connections on startup, cleanup on shutdown)
    - Core endpoints: GET /health, GET /

Other team members add their endpoints to this file:
    - Devansh:  POST /metrics  (network packet ingestion)
    - Bhavya:   GET/POST /alerts  (alert CRUD)
    - Rehan:    posts to /metrics from scapy_agent.py
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
    """Application startup and shutdown hooks.

    On startup: log that we're ready. (DB connection pools, Redis client,
    and InfluxDB client will be initialized here by teammates as they add
    their features.)

    On shutdown: log that we're stopping. (Close any open connections.)
    """
    logger.info("AINIS API starting up...")
    # TODO: initialize DB engine, Redis client, InfluxDB client here
    yield
    logger.info("AINIS API shutting down...")
    # TODO: close DB engine, Redis client, InfluxDB client here


# ---------------------------------------------------------------------------
# FastAPI app
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
# Core endpoints (owned by Jehan)
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
    """Liveness probe. Returns 200 OK if the API process is alive.

    Note: this only checks the API itself. Dependency health checks
    (Postgres, InfluxDB, Redis) will be added later as separate endpoints.
    """
    return {"status": "ok", "service": "ainis-api"}


# ---------------------------------------------------------------------------
# Devansh's slice — Metric ingestion (POST /metrics)
# Keeping Rehan's initial stub; Devansh will extend this to write to InfluxDB.
# ---------------------------------------------------------------------------
class Metric(BaseModel):
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: str
    packet_length: int
    timestamp: str


@app.post("/metrics", status_code=201)
async def ingest_metric(metric: Metric):
    """Receive one captured packet metric.

    Current behavior: logs the payload. Devansh will wire this up to
    write to InfluxDB via MetricsClient.
    """
    logger.info(f"Received metric: {metric.model_dump()}")
    return {"message": "metric received"}


# ---------------------------------------------------------------------------
# Bhavya's slice — Alert CRUD endpoints will be added here
# ---------------------------------------------------------------------------
# (Bhavya will add GET /alerts and POST /alerts below this line)
