from fastapi import APIRouter, HTTPException, Request

from app.core.limiter import limiter
from pydantic import BaseModel, Field
from typing import Literal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from fastapi import Depends
from app.core.db import get_session
from app.models.prediction import Prediction
from app.core.security import verify_api_key

router = APIRouter(prefix="/predict", tags=["predictions"])


class CongestionFeatures(BaseModel):
    packet_rate: float = Field(..., gt=0, le=100000, description="Packets per second")
    avg_latency: float = Field(..., gt=0, le=10000, description="Average latency in ms")
    byte_rate: float = Field(..., gt=0, le=10_000_000, description="Bytes per second")
    flow_count: int = Field(..., gt=0, le=100000, description="Number of active flows")
    protocol_ratio: float = Field(..., ge=0.0, le=1.0, description="TCP ratio (0-1)")



class CongestionResponse(BaseModel):
    prediction: int
    probability: float
    label: Literal["CONGESTED", "NORMAL"]
    model: str = "xgboost-v1"


@router.post(
    "/congestion",
    response_model=CongestionResponse,
    dependencies=[Depends(verify_api_key)],
)
@limiter.limit("60/minute")
async def predict_congestion(request: Request, features: CongestionFeatures):
    try:
        from ml.congestion.predictor import get_predictor

        predictor = get_predictor()

        # Convert request payload to model feature format
        payload = features.model_dump()

        payload["tcp_ratio"] = payload.pop("protocol_ratio")

        result = predictor.predict_with_confidence(payload)

        return CongestionResponse(**result, model="xgboost-v1")

    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=f"Model not loaded: {str(e)}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@router.get("/predictions/latest")
@limiter.limit("100/minute")
async def get_latest_predictions(request: Request, db: AsyncSession = Depends(get_session)):
    result = await db.execute(
        select(Prediction).order_by(desc(Prediction.created_at)).limit(20)
    )
    rows = result.scalars().all()
    return [
        {
            "id": p.id,
            "model": p.model_name,
            "score": p.score,
            "is_alert": p.binary_output,
            "severity": p.severity,
            "timestamp": p.created_at.isoformat(),
        }
        for p in rows
    ]
