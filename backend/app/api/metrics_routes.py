from fastapi import APIRouter, Response
from app.core.metrics import generate_latest, CONTENT_TYPE_LATEST

router = APIRouter()


@router.get("/metrics/prometheus")
async def prometheus_metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
