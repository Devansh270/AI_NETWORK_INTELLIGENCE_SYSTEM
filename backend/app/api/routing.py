from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.limiter import limiter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import get_session
from app.models.routing_rule import RoutingRule
from app.models.schemas import RoutingRuleCreate, RoutingRuleResponse
from typing import List
import redis
import json
import os
from app.core.security import verify_api_key

router = APIRouter(prefix="/routing-rules", tags=["routing"])

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=6379,
    decode_responses=True,
)


@router.get("/", response_model=List[RoutingRuleResponse])
@limiter.limit("100/minute")
async def get_routing_rules(request: Request, db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(RoutingRule))
    return result.scalars().all()


@router.get("/{rule_id}", response_model=RoutingRuleResponse)
@limiter.limit("100/minute")
async def get_routing_rule(request: Request, rule_id: int, db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(RoutingRule).where(RoutingRule.id == rule_id))
    rule = result.scalar_one_or_none()

    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")

    return rule


@router.post(
    "/", response_model=RoutingRuleResponse, dependencies=[Depends(verify_api_key)]
)
@limiter.limit("30/minute")
async def create_routing_rule(
    request: Request,
    rule: RoutingRuleCreate,
    db: AsyncSession = Depends(get_session),
):
    db_rule = RoutingRule(**rule.model_dump())

    db.add(db_rule)
    await db.commit()
    await db.refresh(db_rule)

    redis_client.publish(
        "routing_rules_updated",
        json.dumps(
            {
                "action": "created",
                "rule_id": db_rule.id,
            }
        ),
    )

    return db_rule


@router.put(
    "/{rule_id}",
    response_model=RoutingRuleResponse,
    dependencies=[Depends(verify_api_key)],
)
@limiter.limit("30/minute")
async def update_routing_rule(
    request: Request,
    rule_id: int,
    rule: RoutingRuleCreate,
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(select(RoutingRule).where(RoutingRule.id == rule_id))
    db_rule = result.scalar_one_or_none()

    if db_rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")

    for key, value in rule.model_dump().items():
        setattr(db_rule, key, value)

    await db.commit()
    await db.refresh(db_rule)

    redis_client.publish(
        "routing_rules_updated",
        json.dumps(
            {
                "action": "updated",
                "rule_id": rule_id,
            }
        ),
    )

    return db_rule


@router.delete("/{rule_id}", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
async def delete_routing_rule(
    request: Request,
    rule_id: int,
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(select(RoutingRule).where(RoutingRule.id == rule_id))
    db_rule = result.scalar_one_or_none()

    if db_rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")

    await db.delete(db_rule)
    await db.commit()

    redis_client.publish(
        "routing_rules_updated",
        json.dumps(
            {
                "action": "deleted",
                "rule_id": rule_id,
            }
        ),
    )

    return {"deleted": rule_id}
