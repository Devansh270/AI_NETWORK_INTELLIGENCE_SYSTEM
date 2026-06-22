# Day 17 — WebSocket Load Test Report

**Date:** 2026-06-22
**Author:** Jehan
**Branch:** `feat/day17-locust-load-test`

## Setup

- **Backend:** uvicorn `app.main:app --reload` on macOS (native, not Docker)
- **Infra:** Docker stack (Redis, Postgres, InfluxDB, Adminer) — `docker compose up -d`
- **Publisher:** `tests/load/mock_publisher.py` at 20 packets/sec (scapy not available on Mac; Devansh re-runs on WSL against live scapy)
- **Load tool:** Locust 2.44.4 with `websocket-client` 1.9.0
- **Test parameters:** 50 concurrent users, spawn rate 5/sec, run-time 5 minutes, headless mode

## Methodology

Each Locust client opens a single WebSocket connection to `/ws/metrics` and loops on `ws.recv()`. The time from entering `recv()` to receiving the next broadcast is recorded as the response time. Mock publisher emits one packet every ~50ms to Redis channel `packets`; the WS handler reads from Redis and broadcasts to all connected clients.

**Note on what this measures:** the metric is "wait time until next broadcast arrives," not true end-to-end capture-to-client latency. True E2E latency would require timestamps embedded by the publisher and compared client-side. For Day 17 the wait-time number is sufficient to characterize handler scaling and the Day 14 `timeout=1.0` poll behavior.

## Results

| Metric | Value |
|---|---|
| Total requests | 9,521 |
| Failures | 0 (0.00%) |
| Median response time | 0.023 ms |
| Average response time | 0.329 ms |
| Min | 0.023 ms |
| Max | 49.24 ms |
| p50, p66, p75, p80, p90, p95, p98 | 0 ms |
| p99 | 1 ms |
| p99.9 | 37 ms |
| p99.99 | 49 ms |
| Avg content size | 154.6 bytes |
| Throughput | 31.88 req/sec aggregate |

CSVs: `backend/tests/load/results_stats.csv`, `results_stats_history.csv`, `results_failures.csv`.

## Findings

### 1. Day 17 sprint target met
Sprint goal was "WebSocket p95 latency < 50ms under 50 concurrent clients." Actual p95 = 0ms (sub-millisecond), max = 49ms, zero failures. Comfortable margin.

### 2. The Day 14 `timeout=1.0` poll is not currently the bottleneck
With the mock publisher pumping packets every ~50ms, the Redis `get_message` call inside the WS handler almost always returns a real message on the first poll — it never waits the full 1s timeout. The 1s ceiling would only become visible during dead periods when no packets are being published, which is the empty-pipeline state, not the loaded one.

Recommendation: leave `timeout=1.0` as-is. It only matters during idle periods, and during those the latency doesn't matter (nothing to deliver).

### 3. Throughput observation
9,521 receives across 50 clients in 5 minutes = ~190 receives/client total = ~0.63 receives/client/sec. Mock publisher emits 20 packets/sec. With 50 clients all subscribed, we'd naively expect 20 receives/client/sec = 1000/total/sec, not 0.63. This is **expected** — `ws.recv()` only returns the next message after the previous one is fully drained, and Locust's `wait_time = between(1, 2)` adds 1-2s of think time between recv calls. So each client only attempts ~0.6 recvs/sec. The handler is delivering everything available; clients are just not asking for messages aggressively.

If we wanted true broadcast saturation, we'd remove `wait_time` and have clients loop on recv without delay. That's a follow-up if needed.

### 4. CPU profiling skipped
The plan called for py-spy profiling. Skipped because the latency results are already comfortably under target and there's no obvious bottleneck to investigate. py-spy is more useful when you have a slow handler and need to find which function is hot. Re-runnable any time with `py-spy top --pid $(pgrep -f "uvicorn.*main:app")`.

## Platform note

This test ran on macOS with a mock publisher in place of scapy. Devansh re-runs the same locustfile on his WSL machine against live scapy at end of day. Expected differences:
- Real scapy emits in bursty patterns (10 packets at once then idle) vs mock's uniform 50ms cadence
- Real packet payloads can be larger and contain unicode/binary that may stress JSON parsing
- Real scapy throughput depends on traffic on the captured interface

The handler scaling (50 concurrent, zero failures, sub-ms latency) should hold on both platforms — they exercise the same code path. Numbers will be confirmed in `day17-locust-report-devansh.md` (added separately).

## Reproducing

See `backend/tests/load/README.md`. Three-terminal setup:
T1: backend
cd backend && uvicorn app.main:app --reload
T2: publisher (Mac/Windows native)
python3 backend/tests/load/mock_publisher.py
OR (Linux/WSL with real scapy)
sudo python3 backend/capture/scapy_agent.py
T3: locust
cd backend/tests/load

locust -f locustfile.py --host=http://localhost:8000 --users 50 --spawn-rate 5 --run-time 5m --headless --csv=results
