# backend/app/api/telemetry_routes.py
from fastapi import APIRouter
from app.core.log_buffer import log_ring_buffer

router = APIRouter()

@router.get("/telemetry/logs")
async def get_recent_logs():
    return list(log_ring_buffer)