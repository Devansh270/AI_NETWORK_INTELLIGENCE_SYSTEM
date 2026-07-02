from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.models import Alert, AlertSeverity, RoutingRule, NetworkEvent
DATABASE_URL = "postgresql://dev:devpass@localhost:5432/appdb"
engine = create_engine(DATABASE_URL)

with Session(engine) as session:
    session.add(Alert(
        severity=AlertSeverity.HIGH,
        message="High packet rate detected on eth0",
        source_ip="10.0.0.1",
        dst_ip="10.0.0.2",
        protocol="TCP"
    ))
    session.add(RoutingRule(
        name="Prioritize HTTPS traffic",
        protocol="TCP",
        dst_port=443,
        priority=1,
        bandwidth_limit_kbps=None
    ))
    session.add(NetworkEvent(
        src_ip="10.0.0.1", dst_ip="10.0.0.2",
        src_port=54321, dst_port=80,
        protocol="TCP", packet_length=1500, ttl=64
    ))
    session.commit()
    print("Seed data inserted successfully")