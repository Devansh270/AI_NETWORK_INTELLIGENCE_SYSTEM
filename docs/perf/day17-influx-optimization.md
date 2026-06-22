# Day 17 — InfluxDB Query Optimization

**Owner:** Rehan
**Branch:** `fix/day17-influx-perf`
**Sprint context:** Week 3, Day 17 — Performance Profiling & Optimization (hardening phase, no new features)

---

## Goal

Reduce InfluxDB query load and remove any event-loop-blocking calls ahead of Jehan's 50-client Locust WebSocket load test, per the Day 17 sprint goal: WebSocket p95 latency < 50ms under load.

---

## Findings & Fixes

### 1. Event-loop-blocking bug (highest impact)

**File:** `backend/app/services/inference_scheduler.py`

`_query_latest_summary` and `_query_window` called the synchronous `influxdb_client` query API (`influx_client.query_api().query(...)`) directly inside `async def` functions, with no `run_in_executor`. Since this scheduler runs every 5 seconds (`INFERENCE_INTERVAL = 5`), it was blocking the entire FastAPI event loop — including WebSocket broadcast handling — for the duration of both Influx queries, every single cycle.

This is relevant to today's Locust results specifically: any WS latency spike correlated with the 5s scheduler tick is explained by this, not by WebSocket/Redis pub-sub overhead itself.

**Fix:** wrapped both query calls in `loop.run_in_executor(None, ...)` so the blocking I/O runs off the event loop thread.

```python
loop = asyncio.get_event_loop()
tables = await loop.run_in_executor(
    None, lambda: influx_client.query_api().query(query=query, org=org)
)
```

### 2. Oversized range window

**File:** `backend/app/services/inference_scheduler.py` — `_query_window`

Previously queried `range(start: -5m)` every 5 seconds just to extract the most recent `SEQ_LEN = 30` rows via `limit()` after sorting — re-scanning a growing 5-minute window on every call.

Confirmed write cadence: `feature_aggregator.py`'s `AGGREGATION_INTERVAL = 5` — one row written roughly every 5 seconds. At that cadence, 30 rows requires ~150 seconds of history minimum.

**Fix:** tightened range to `-3m` (180s — 150s minimum + buffer for jitter/dropped writes). ~40% reduction in scanned range vs the original `-5m` (300s).

### 3. Redundant double-scan

**File:** `backend/app/services/metrics_service.py`

`total_q` (count) and `bytes_q` (sum) ran as two separate full scans over the identical filtered row set (`network_traffic` measurement, `packet_length` field, same time window).

**Fix:** combined into a single `reduce()` pass that accumulates both `count` and `sum` in one scan:

```flux
|> reduce(
    fn: (r, accumulator) => ({
        count: accumulator.count + 1,
        sum: accumulator.sum + r._value
    }),
    identity: {count: 0, sum: 0.0}
)
```

Net effect: 3 scans → 2 (combined scan + protocol breakdown scan). Did not fold the protocol breakdown query in as well — judged not worth the added complexity for one additional scan saved, given today's time budget.

---

## Deferred to Day 18

**`protocol` field → tag conversion**, `backend/app/api/metrics.py`

`metrics_service.py`'s `proto_q` groups by `protocol` (`group(columns: ["protocol"])`), but `protocol` is currently written as a `.field()`, not a `.tag()`, on the `Point("network_traffic")` write in `metrics.py`. Tags are indexed in InfluxDB; fields are not — so this group-by is currently a full scan rather than an index seek.

**Confirmed safe to convert:** the Pydantic model constrains `protocol: Literal["TCP", "UDP", "ICMP", "OTHER"]` — exactly 4 fixed values, no tag-cardinality risk.

**Confirmed no breakage risk found:** grep across the codebase for direct `r.protocol`-style filters returned no matches, so no other query depends on `protocol` being read as a field specifically.

**Why deferred:** the actual `Point("network_traffic")` write call in `metrics.py` wasn't reviewed in time during today's session — only the Pydantic model schema was confirmed. Didn't want to guess at the exact `.tag()`/`.field()` diff for the one write path the entire ingestion pipeline depends on. Picking this up as the first task Day 18.

---

## Verification

- `python -c "from app.services.inference_scheduler import _query_window, _query_latest_summary"` — imports clean
- `python -c "from app.services.metrics_service import get_metrics_summary"` — imports clean
- `GET /health` → `200 OK`, all services (`redis`, `influxdb`, `postgres`) report `ok`
- `GET /metrics/summary` → `200 OK`, returns valid response shape:
  ```json
  {"total_packets":0,"total_bytes":0,"active_flows":0,"packets_per_sec":0.0,"bytes_per_sec":0.0,"proto_breakdown":{}}
  ```
  Zero values are expected — no live Mininet/Scapy traffic was running at test time, not a code defect. Combined `reduce()` query executes and returns correctly-shaped output against an empty window.
- Scheduler logs confirmed still emitting `[scheduler] Congestion score=...` / anomaly equivalents every ~5s post-fix, with no new exceptions — event loop responsiveness preserved.

**Not yet measured:** real before/after latency numbers under live traffic volume. Recommend re-running with Mininet active before/after this branch merges, ideally as part of Jehan's combined post-merge Locust run, since that's when live traffic will actually be flowing.

---

## Commit

Branch: `fix/day17-influx-perf`
Commit: `fix: unblock event loop on influx queries, reduce scan range and double-scan`
PR: open against `develop`