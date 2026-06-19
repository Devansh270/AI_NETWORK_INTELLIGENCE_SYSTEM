import asyncio
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
import redis.asyncio as aioredis

from app.api import alerts, metrics
from app.api.websocket_routes import router as ws_router
from app.api.predictions import router as predictions_router
from app.api.anomaly import router as anomaly_router
from app.api.routing import router as routing_router
from app.api.topology import router as topology_router
from app.core.db import engine, AsyncSessionLocal
from app.core.influx import get_influx_write_api, get_influx_client
from app.core.config import get_settings
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.exceptions import (
    http_exception_handler,
    validation_exception_handler,
    unhandled_exception_handler,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ainis.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AINIS API starting up...")
    settings = get_settings()

    redis_client = aioredis.from_url(
        f"redis://{settings.redis_host}:{settings.redis_port}",
        decode_responses=True,
    )
    app.state.redis = redis_client

    influx_available = False
    try:
        app.state.influx = get_influx_client()
        influx_available = True
        logger.info("InfluxDB client initialized.")
    except Exception as e:
        logger.warning(f"InfluxDB not available at startup: {e}")
        app.state.influx = None

    app.state.inference_task = None
    app.state.aggregation_task = None

    if influx_available:
        shared_state = {
            "influx_client": app.state.influx,
            "session_factory": AsyncSessionLocal,
            "redis_client": redis_client,
            "settings": settings,
        }

        from app.services.feature_aggregator import run_feature_aggregation_loop

        app.state.aggregation_task = asyncio.create_task(
            run_feature_aggregation_loop(shared_state)
        )
        logger.info("Feature aggregation loop started.")

        from app.services.inference_scheduler import run_inference_loop

        app.state.inference_task = asyncio.create_task(run_inference_loop(shared_state))
        logger.info("Inference scheduler started.")
    else:
        logger.warning("Background tasks NOT started - InfluxDB unavailable.")

    yield

    for task_name in ("inference_task", "aggregation_task"):
        task = getattr(app.state, task_name, None)
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            logger.info(f"{task_name} stopped.")

    try:
        await redis_client.aclose()
    except Exception:
        pass

    logger.info("AINIS API shut down.")


app = FastAPI(
    title="AINIS API",
    description="AI Network Intelligence System",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)
class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request.state.request_id = str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

app.add_middleware(RequestIDMiddleware)

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
app.include_router(topology_router)
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
