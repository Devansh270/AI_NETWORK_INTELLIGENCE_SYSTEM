from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal


class MetricsSummary(BaseModel):
    total_packets:   int
    total_bytes:     int
    active_flows:    int
    packets_per_sec: float
    bytes_per_sec:   float
    proto_breakdown: dict[str, int]  # {"TCP": 450, "UDP": 120, "ICMP": 30}


class NetworkMetric(BaseModel):
    src_ip: str = Field(
        ...,
        pattern=r"^(\d{1,3}\.){3}\d{1,3}$",
        examples=["192.168.1.10"]
    )
    dst_ip: str = Field(
        ...,
        pattern=r"^(\d{1,3}\.){3}\d{1,3}$",
        examples=["192.168.1.20"]
    )
    src_port: int = Field(..., ge=0, le=65535)
    dst_port: int = Field(..., ge=0, le=65535)
    protocol: Literal["TCP", "UDP", "ICMP", "OTHER"]
    packet_length: int = Field(..., gt=0, le=65535)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "src_ip": "10.0.0.1",
                "dst_ip": "10.0.0.2",
                "src_port": 5001,
                "dst_port": 80,
                "protocol": "TCP",
                "packet_length": 1024
            }
        }