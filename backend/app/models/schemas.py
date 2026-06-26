from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional


class RoutingRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    protocol: str = Field(..., pattern=r"^(TCP|UDP|ICMP|tcp|udp|icmp)$")
    dst_port: Optional[int] = Field(None, ge=1, le=65535)
    priority: int = Field(..., ge=1, le=10)
    bandwidth_limit_kbps: Optional[int] = Field(None, ge=0, le=1000000)
    active: bool = True


class RoutingRuleResponse(RoutingRuleCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True