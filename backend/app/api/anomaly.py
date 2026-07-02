from fastapi import APIRouter, HTTPException, Depends, Request
from app.core.limiter import limiter
from app.core.security import verify_api_key
from pydantic import BaseModel, field_validator
from typing import List

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

    @field_validator("window")
    @classmethod
    def validate_window(cls, v):
        if len(v) != 30:
            raise ValueError(f"window must contain exactly 30 timesteps, got {len(v)}")
        for row in v:
            if len(row) != 5:
                raise ValueError(f"each timestep must have 5 features, got {len(row)}")
            for value in row:
                if not isinstance(value, (int, float)):
                    raise ValueError("all feature values must be numeric")
                if abs(value) > 1_000_000:
                    raise ValueError(
                        f"feature value {value} out of reasonable range (-1e6, 1e6)"
                    )
        return v


class AnomalyResponse(BaseModel):
    anomaly_score: float
    reconstruction_error: float
    is_anomaly: bool
    severity: str


@router.post(
    "/anomaly", response_model=AnomalyResponse, dependencies=[Depends(verify_api_key)]
)
@limiter.limit("60/minute")
async def predict_anomaly(request: Request, payload: AnomalyRequest):
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