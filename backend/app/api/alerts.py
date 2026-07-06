from fastapi import APIRouter, Depends, Query, Request
from app.core.limiter import limiter
from app.core.security import verify_api_key
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
from app.models.alert import Alert, SeverityEnum
from app.core.db import get_session

router = APIRouter(prefix="/alerts", tags=["alerts"])


# Pydantic schema — what the API accepts
class AlertCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    severity: SeverityEnum
    source_ip: str | None = Field(
        None, pattern=r"^(\d{1,3}\.){3}\d{1,3}$"
    )


# GET /alerts
@router.get("")
@limiter.limit("100/minute")
async def list_alerts(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(
        select(Alert).order_by(Alert.created_at.desc()).offset(skip).limit(limit)
    )
    alerts = result.scalars().all()
    return {"alerts": alerts, "skip": skip, "limit": limit}


# POST /alerts
@router.post("", status_code=201, dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
async def create_alert(
    request: Request,
    payload: AlertCreate,
    db: AsyncSession = Depends(get_session),
):
    alert = Alert(**payload.model_dump())
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert