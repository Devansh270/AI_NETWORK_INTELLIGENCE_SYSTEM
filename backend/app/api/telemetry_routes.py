# backend/app/api/telemetry_routes.py
from fastapi import APIRouter, Request

from app.core.limiter import limiter
from app.core.log_buffer import log_ring_buffer

router = APIRouter()


@router.get("/telemetry/logs")
@limiter.limit("60/minute")
async def get_recent_logs(request: Request):
    return list(log_ring_buffer)
