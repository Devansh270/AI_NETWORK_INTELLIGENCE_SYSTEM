from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Literal

router = APIRouter(prefix="/predict", tags=["predictions"])


class CongestionFeatures(BaseModel):
    packet_rate: float = Field(..., gt=0, description="Packets per second")
    avg_latency: float = Field(..., gt=0, description="Average latency in ms")
    byte_rate: float = Field(..., gt=0, description="Bytes per second")
    flow_count: int = Field(..., gt=0, description="Number of active flows")
    protocol_ratio: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="TCP ratio (0-1)"
    )


class CongestionResponse(BaseModel):
    prediction: int
    probability: float
    label: Literal["CONGESTED", "NORMAL"]
    model: str = "xgboost-v1"


@router.post("/congestion", response_model=CongestionResponse)
async def predict_congestion(features: CongestionFeatures):
    try:
        from ml.congestion.predictor import get_predictor

        predictor = get_predictor()

        # Convert request payload to model feature format
        payload = features.model_dump()

        payload["tcp_ratio"] = payload.pop("protocol_ratio")

        result = predictor.predict_with_confidence(payload)

        return CongestionResponse(
            **result,
            model="xgboost-v1"
        )

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Model not loaded: {str(e)}"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(e)}"
        )