from fastapi import APIRouter, HTTPException, Depends
from app.core.security import verify_api_key
from pydantic import BaseModel, validator
from typing import List
import os

router = APIRouter(prefix="/predict", tags=["predictions"])

# Lazy-load the predictor once on first request (avoids slow startup)
_predictor = None


def get_predictor():
    global _predictor
    if _predictor is None:
        from ml.anomaly.predictor import AnomalyPredictor

        _predictor = AnomalyPredictor()
    return _predictor


class AnomalyRequest(BaseModel):
    window: List[List[float]]

    @validator("window")
    def validate_window(cls, v):
        if len(v) != 30:
            raise ValueError(f"window must contain exactly 30 timesteps, got {len(v)}")
        for row in v:
            if len(row) != 5:
                raise ValueError(f"each timestep must have 5 features, got {len(row)}")
        return v


class AnomalyResponse(BaseModel):
    anomaly_score: float
    reconstruction_error: float
    is_anomaly: bool
    severity: str


@router.post(
    "/anomaly", response_model=AnomalyResponse, dependencies=[Depends(verify_api_key)]
)
async def predict_anomaly(payload: AnomalyRequest):
    try:
        predictor = get_predictor()
        result = predictor.predict(payload.window)
        return result
    except FileNotFoundError:
        raise HTTPException(
            status_code=503, detail="Model checkpoint not found. Train the model first."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
