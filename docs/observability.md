# Observability Guide

How AINIS exposes its internal state for debugging, monitoring, and demos. Three layers: structured logs, Prometheus metrics, and a live log viewer.

## Quick reference

| Endpoint | Purpose |
|---|---|
| `GET /health` | Aggregate health (redis, influxdb, postgres) |
| `GET /health/{service}` | Per-dependency health check |
| `GET /metrics/prometheus` | Prometheus exposition format counters + gauges |
| `GET /telemetry/logs` | Last 100 structured log lines from the in-memory ring buffer |

---

## 1. Structured logging

All backend logs are emitted as JSON lines on stdout via `structlog`. Each log line is a single self-contained JSON object - no multi-line tracebacks or freeform text.

### Configuration

`backend/app/core/logging_config.py` sets up structlog with:
- ISO timestamps
- Log level injected automatically
- Stack info + exception info captured if present
- `ring_buffer_processor` (see section 3) keeps the last 100 events in memory
- `JSONRenderer` as the final step

Initialized once at module load:

```python
from app.core.logging_config import configure_logging
log = configure_logging()
```

### Standard event types

| `event` | When fired | Key fields |
|---|---|---|
| `app_startup` | Once on uvicorn boot | `service` |
| `http_request` | Every API request (via RequestLoggingMiddleware) | `method`, `path`, `status_code`, `duration_ms` |
| `prediction_made` | After each ML inference | `model_name`, `score`, `severity` |
| `alert_created` | When an anomaly/congestion alert is written | `alert_type`, `score`, `severity` |

### Example log line

```json
{
  "method": "GET",
  "path": "/health",
  "status_code": 200,
  "duration_ms": 124.87,
  "event": "http_request",
  "level": "info",
  "timestamp": "2026-06-24T17:19:58.753386Z"
}
```

### Why JSON

Single-line JSON is greppable, parseable by any log tool (jq, Datadog, ELK), and easy to filter. `grep "prediction_made" logs.txt | jq .` works without writing a custom parser.

---

## 2. Prometheus metrics

`backend/app/core/metrics.py` defines counters and gauges using `prometheus_client`. `/metrics/prometheus` exposes them in the standard exposition format any Prometheus scraper can consume.

### Available metrics

| Name | Type | Labels | Description |
|---|---|---|---|
| `packets_captured_total` | Counter | none | Total packets seen by scapy agent / mock publisher |
| `predictions_made_total` | Counter | `model_name` | ML predictions, separable per model |
| `active_connections` | Gauge | none | Current WebSocket clients connected to `/ws/metrics` |

### Where they get incremented

- **`packets_captured_total`** - `POST /metrics` ingestion path in `app/api/metrics.py`
- **`predictions_made_total{model_name="xgboost_congestion"}`** - in inference scheduler after congestion call
- **`predictions_made_total{model_name="lstm_anomaly"}`** - in inference scheduler after anomaly call
- **`active_connections`** - `inc()` on WS accept, `dec()` in finally block of `app/api/websocket_routes.py`

### Example output
HELP packets_captured_total Total packets captured by Scapy agent
TYPE packets_captured_total counter
packets_captured_total 1523.0
HELP predictions_made_total Total ML predictions made
TYPE predictions_made_total counter
predictions_made_total{model_name="lstm_anomaly"} 312.0

predictions_made_total{model_name="xgboost_congestion"} 312.0
HELP active_connections Current active WebSocket connections
TYPE active_connections gauge
active_connections 2.0

The endpoint also exposes built-in Python runtime gauges (GC stats, memory, Python version) automatically - useful for debugging memory leaks or runtime issues during long-running demos.

---

## 3. Live log viewer (ring buffer)

The plan was to avoid setting up an external log shipper (ELK, Loki, Datadog) for a college-scale project. Instead, structlog stores the last 100 events in an in-memory `deque` and exposes them over HTTP.

### How it works

`backend/app/core/log_buffer.py`:

```python
log_ring_buffer = deque(maxlen=100)

def ring_buffer_processor(logger, method_name, event_dict):
    log_ring_buffer.append(dict(event_dict))
    return event_dict
```

The `ring_buffer_processor` is registered in `configure_logging()` as a structlog processor. Every structured log line that flows through structlog gets appended to the deque before being JSON-rendered to stdout. Once the deque hits 100 entries, the oldest is silently dropped.

`backend/app/api/telemetry_routes.py` exposes the buffer:

```python
@router.get("/telemetry/logs")
async def get_recent_logs():
    return list(log_ring_buffer)
```

### Frontend integration

`frontend/src/components/TelemetryExport.jsx` polls `/telemetry/logs` every 2 seconds and renders the log lines as a terminal-style scrolling view. Useful for live demos where you want to show "look, every API call gets a log line."

### Limitations

- **In-memory only** - logs reset every uvicorn restart
- **Single-process** - if backend is later scaled with workers/replicas, each will have its own buffer
- **No filtering** - returns all 100 events on every call; client must filter

For production-scale work this would be replaced with a real log shipper. For the current scope it's enough.

---

## Debugging recipes

### "Did a request reach the API at all?"
curl http://localhost:8000/telemetry/logs | jq '.[] | select(.path == "/your/path")'

### "What's the latest LSTM anomaly score?"
curl http://localhost:8000/telemetry/logs | jq '.[] | select(.event == "prediction_made" and .model_name == "lstm_anomaly")'

### "How many WS clients are connected right now?"
curl -s http://localhost:8000/metrics/prometheus | grep active_connections

### "How many packets per minute is the ingestion path seeing?"
Take two readings 60s apart and subtract
curl -s http://localhost:8000/metrics/prometheus | grep "^packets_captured_total"

sleep 60

curl -s http://localhost:8000/metrics/prometheus | grep "^packets_captured_total"

---

## Verifying observability end-to-end

```bash
# 1. backend up
cd backend && uvicorn app.main:app --reload

# 2. trigger some requests
curl http://localhost:8000/health
curl http://localhost:8000/health/redis

# 3. check structured logs landed in the buffer
curl http://localhost:8000/telemetry/logs | python3 -m json.tool

# 4. check prometheus counters increment after a POST /metrics
curl -s http://localhost:8000/metrics/prometheus | grep packets_captured_total
curl -X POST http://localhost:8000/metrics -H "Content-Type: application/json" \
  -d '{"src_ip":"10.0.0.1","dst_ip":"10.0.0.2","src_port":1234,"dst_port":443,"protocol":"TCP","packet_length":1500,"timestamp":"2026-06-24T17:00:00Z"}'
curl -s http://localhost:8000/metrics/prometheus | grep packets_captured_total
```

---

## What this does NOT include

Honest limits so nobody expects more than is there:

- **No log search/aggregation** - no Elasticsearch, no Loki. Use grep on stdout or the ring buffer.
- **No metrics dashboards** - no Grafana, no Prometheus scraper configured. The endpoint exposes the data; viewing it is left to the user.
- **No alerting** - Prometheus would normally feed Alertmanager. We have the export side only.
- **No tracing** - no OpenTelemetry, no Jaeger. Logs include `duration_ms` per request but there's no cross-service trace correlation.

Each of these is reachable from the current state if someone wants to add it - the data shape is already correct (structured JSON, Prometheus format). The endpoints just need consumers.
