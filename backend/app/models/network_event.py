from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class NetworkEvent(Base):
    __tablename__ = "network_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    src_ip: Mapped[str] = mapped_column(String(45))
    dst_ip: Mapped[str] = mapped_column(String(45))
    src_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dst_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    protocol: Mapped[str] = mapped_column(String(10))
    packet_length: Mapped[int] = mapped_column(Integer)
    ttl: Mapped[int | None] = mapped_column(Integer, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)