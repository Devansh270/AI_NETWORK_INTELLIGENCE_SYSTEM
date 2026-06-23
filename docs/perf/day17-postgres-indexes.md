# Day 17 — PostgreSQL Indexing

## Goal
Index hot columns on `alerts` and `predictions` tables, verify with EXPLAIN ANALYZE.

## Indexes Added
- `ix_alerts_created_at` on `alerts.created_at` (btree)
- `ix_predictions_created_at` on `predictions.created_at` (btree)

## Before (baseline, no index)

alerts query: Seq Scan on alerts — Execution Time: 0.168 ms (3 rows)
predictions query: Seq Scan on predictions — Execution Time: 0.179 ms (0 rows)

## After (index applied)
alerts query: Seq Scan on alerts — Execution Time: 0.191 ms (3 rows)

predictions query: Seq Scan on predictions — Execution Time: 0.030 ms (0 rows)

## Notes
Both tables currently have very few rows (alerts: 3 rows, predictions: 0–103 rows
depending on scheduler uptime). PostgreSQL's query planner correctly chose
Seq Scan over the new index for `alerts` since sequential scan is faster on
small tables — this is expected behavior, not a failure of the index.

The index is verified to exist via `\d alerts`:

Indexes:

"alerts_pkey" PRIMARY KEY, btree (id)

"ix_alerts_created_at" btree (created_at)

As table size grows (real production load, more captured packets/predictions),
the planner will automatically switch to Index Scan once it estimates that's
faster than a full table scan. No further action needed — this is correct
indexing for future scale.

## Migration
`backend/alembic/versions/f68392027b3b_add_perf_indexes_day17.py`