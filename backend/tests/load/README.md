# Load Testing — Day 17

WebSocket load test for `/ws/metrics`. Uses Locust to spawn N concurrent
clients that connect and listen for live packet broadcasts.

## Prerequisites

1. Backend running:
cd backend && uvicorn app.main:app --reload

2. Docker stack up:
cd infra && docker compose up -d

3. A packet publisher running. Pick one:
   - **Live scapy** (Linux/WSL only):
 sudo python3 backend/capture/scapy_agent.py
   - **Mock publisher** (cross-platform, for dev/test):
 python3 backend/tests/load/mock_publisher.py

## Running the test
cd backend/tests/load

locust -f locustfile.py --host=http://localhost:8000 
--users 50 --spawn-rate 5 --run-time 5m --headless 
--csv=results

Output files:
- `results_stats.csv` — request count, response time percentiles
- `results_failures.csv` — any exceptions during the run
- `results_stats_history.csv` — time-series of the metrics

## Interpreting numbers

- **`recv ws/metrics` p50/p95/p99** — wait time between server broadcasts.
  Lower-bounded by the WS handler's Redis poll timeout (1.0s as of Day 14).
- **Failure count** — connection drops, JSON parse errors, etc.

## Mock vs live data

Mock publisher emits uniform random packets at a fixed rate (default 20/sec).
This is enough to exercise the WS handler, Redis pub/sub, and connection
scaling — same bottlenecks as live scapy. What it does NOT test:
- Scapy parsing latency
- Burst patterns from real network traffic
- Variable payload sizes

Devansh re-runs the same locustfile against live scapy on WSL at end of
day. Results in `docs/perf/day17-locust-report.md`.
