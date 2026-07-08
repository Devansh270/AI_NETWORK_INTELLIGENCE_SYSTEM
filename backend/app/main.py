import asyncio
import logging
import uuid
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as aioredis

from app.api import alerts, metrics
from app.api.websocket_routes import router as ws_router
from app.api.predictions import router as predictions_router
from app.api.anomaly import router as anomaly_router
from app.api.routing import router as routing_router
from app.api.topology import router as topology_router
from app.api.health_routes import router as health_router
from app.core.db import AsyncSessionLocal
from app.core.influx import get_influx_client
from app.core.config import get_settings
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.exceptions import (
    http_exception_handler,
    validation_exception_handler,
    unhandled_exception_handler,
)
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.api.metrics_routes import router as metrics_router
from app.api.telemetry_routes import router as telemetry_router
from app.api.simulate_routes import router as simulate_router
from app.core.limiter import limiter
from app.core.logging_config import configure_logging

log = configure_logging()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ainis.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("app_startup", service="ainis-backend")
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

# Rate limiting - slowapi limiter attached to app state.
# See app/core/limiter.py for tier conventions and exclusions.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
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


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.time()
        response = await call_next(request)
        duration_ms = round((time.time() - start) * 1000, 2)
        log.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response


app.add_middleware(RequestLoggingMiddleware)

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
app.include_router(health_router)
app.include_router(simulate_router)
app.include_router(metrics_router)
app.include_router(telemetry_router)


@app.get("/")
async def root():
    return {"service": "ainis-api", "version": "0.1.0", "status": "running"}
