from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class RoutingRuleCreate(BaseModel):
    name: str
    protocol: str
    dst_port: Optional[int] = None
    priority: int
    bandwidth_limit_kbps: Optional[int] = None
    active: bool = True

class RoutingRuleResponse(RoutingRuleCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True