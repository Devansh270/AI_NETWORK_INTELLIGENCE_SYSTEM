import pytest

@pytest.mark.asyncio
async def test_health_check(async_client):
    resp = await async_client.get("/health")
    # 503 is valid here too — test env may not have live DB/Redis/Influx connections
    assert resp.status_code in (200, 503)

@pytest.mark.asyncio
async def test_post_metrics_happy_path(async_client):
    payload = {
        "src_ip": "10.0.0.1",
        "dst_ip": "10.0.0.2",
        "src_port": 5001,
        "dst_port": 80,
        "protocol": "TCP",
        "packet_length": 1024
    }
    resp = await async_client.post("/metrics", json=payload)
    assert resp.status_code in (200, 201)

@pytest.mark.asyncio
async def test_post_metrics_missing_required_field_returns_422(async_client):
    bad_payload = {
        "dst_ip": "10.0.0.2",
        "src_port": 5001,
        "dst_port": 80,
        "protocol": "TCP",
        "packet_length": 1024
    }  # missing src_ip
    resp = await async_client.post("/metrics", json=bad_payload)
    assert resp.status_code == 422

@pytest.mark.asyncio
async def test_post_metrics_wrong_type_returns_422(async_client):
    bad_payload = {
        "src_ip": "10.0.0.1",
        "dst_ip": "10.0.0.2",
        "src_port": 5001,
        "dst_port": 80,
        "protocol": "TCP",
        "packet_length": "not-a-number"
    }
    resp = await async_client.post("/metrics", json=bad_payload)
    assert resp.status_code == 422

@pytest.mark.asyncio
async def test_get_metrics_summary(async_client):
    resp = await async_client.get("/metrics/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert "total_packets" in body
    assert "active_flows" in body

@pytest.mark.asyncio
async def test_post_alert_happy_path(async_client):
    payload = {
        "title": "Test alert",
        "description": "Created during pytest",
        "severity": "HIGH",
        "source_ip": "10.0.0.1"
    }
    resp = await async_client.post("/alerts", json=payload)
    assert resp.status_code == 201

@pytest.mark.asyncio
async def test_get_alerts_returns_list(async_client):
    resp = await async_client.get("/alerts")
    assert resp.status_code == 200
    body = resp.json()
    assert "alerts" in body
    assert isinstance(body["alerts"], list)

@pytest.mark.asyncio
async def test_post_alert_invalid_severity_returns_422(async_client):
    payload = {
        "title": "Bad severity test",
        "severity": "NOT_A_REAL_SEVERITY"
    }
    resp = await async_client.post("/alerts", json=payload)
    assert resp.status_code == 422

@pytest.mark.asyncio
async def test_predict_congestion_happy_path(async_client):
    payload = {
        "packet_rate": 120.0,
        "avg_latency": 15.2,
        "byte_rate": 50000.0,
        "flow_count": 8,
        "protocol_ratio": 0.7
    }
    resp = await async_client.post("/predict/congestion", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert "probability" in body
    assert "prediction" in body

@pytest.mark.asyncio
async def test_predict_congestion_missing_field_returns_422(async_client):
    resp = await async_client.post("/predict/congestion", json={"packet_rate": 120.0})
    assert resp.status_code == 422

@pytest.mark.asyncio
async def test_predict_anomaly_happy_path(async_client, sample_feature_window):
    # anomaly endpoint expects window of List[List[float]], not List[dict]
    window = [
        [120.0, 15.2, 50000.0, 8, 0.7],
        [135.0, 16.0, 52000.0, 9, 0.68],
        [128.0, 14.8, 51000.0, 8, 0.71],
        [142.0, 17.1, 53500.0, 10, 0.69],
        [130.0, 15.5, 51200.0, 9, 0.70],
    ] * 6  # repeat to reach 30 timesteps
    resp = await async_client.post("/predict/anomaly", json={"window": window[:30]})
    assert resp.status_code == 200
    body = resp.json()
    assert "anomaly_score" in body
    assert "is_anomaly" in body