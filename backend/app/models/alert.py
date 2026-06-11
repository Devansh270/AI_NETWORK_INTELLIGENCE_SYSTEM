from sqlalchemy import Column, String, Integer, DateTime, Enum
from app.models.base import Base
from datetime import datetime
import uuid, enum



class SeverityEnum(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class Alert(Base):
    __tablename__ = "alerts"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    description = Column(String(1000))
    severity = Column(Enum(SeverityEnum), nullable=False)
    source_ip = Column(String(45))
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved = Column(Integer, default=0)  # 0 = open, 1 = resolved