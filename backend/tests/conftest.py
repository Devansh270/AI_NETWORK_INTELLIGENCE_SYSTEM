import pytest
import fakeredis.aioredis
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def fake_redis():
    """In-memory Redis for tests — no real Redis container needed."""
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.flushall()
    await client.close()


@pytest.fixture
async def async_client():
    """Async HTTP client for testing FastAPI endpoints without a running server."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    # Dispose of the engine's connection pool after each test
    from app.core.db import engine
    await engine.dispose()


@pytest.fixture
def sample_packet():
    return {
        "src_ip": "10.0.0.1",
        "dst_ip": "10.0.0.2",
        "protocol": "TCP",
        "port": 443,
        "length": 1500,
        "timestamp": "2026-06-20T10:00:00Z",
    }


@pytest.fixture
def sample_feature_window():
    """5-step window matching the LSTM's expected input shape."""
    return [
        {"packet_rate": 120.0, "avg_latency": 15.2, "byte_rate": 50000.0, "flow_count": 8, "protocol_ratio": 0.7},
        {"packet_rate": 135.0, "avg_latency": 16.0, "byte_rate": 52000.0, "flow_count": 9, "protocol_ratio": 0.68},
        {"packet_rate": 128.0, "avg_latency": 14.8, "byte_rate": 51000.0, "flow_count": 8, "protocol_ratio": 0.71},
        {"packet_rate": 142.0, "avg_latency": 17.1, "byte_rate": 53500.0, "flow_count": 10, "protocol_ratio": 0.69},
        {"packet_rate": 130.0, "avg_latency": 15.5, "byte_rate": 51200.0, "flow_count": 9, "protocol_ratio": 0.70},
    ]