import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_root_returns_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_check_returns_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_check_has_service_field():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    data = response.json()
    assert "service" in data


@pytest.mark.skip(reason="async DB session conflict in test client - tracked for Day 8")
@pytest.mark.asyncio
async def test_get_alerts_returns_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/alerts")
    assert response.status_code == 200


@pytest.mark.skip(reason="async DB session conflict in test client - tracked for Day 8")
@pytest.mark.asyncio
async def test_get_alerts_returns_list():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/alerts")
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_404_for_nonexistent_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/does-not-exist")
    assert response.status_code == 404
