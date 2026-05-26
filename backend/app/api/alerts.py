from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.models.alert import Alert, SeverityEnum
from app.core.db import get_session

router = APIRouter(prefix="/alerts", tags=["alerts"])

# Pydantic schema — what the API accepts
class AlertCreate(BaseModel):
    title: str
    description: str | None = None
    severity: SeverityEnum
    source_ip: str | None = None

# GET /alerts
@router.get("")
async def list_alerts(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(
        select(Alert)
        .order_by(Alert.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    alerts = result.scalars().all()
    return {"alerts": alerts, "skip": skip, "limit": limit}

# POST /alerts
@router.post("", status_code=201)
async def create_alert(
    payload: AlertCreate,
    db: AsyncSession = Depends(get_session),
):
    alert = Alert(**payload.model_dump())
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert