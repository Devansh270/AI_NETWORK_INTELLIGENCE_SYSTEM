-- Removes false-positive CRITICAL alerts generated before the
-- LSTM anomaly threshold was recalibrated (Day 20 fix).
-- Safe to re-run before any demo/seed if old alerts reappear.

DELETE FROM alerts
WHERE created_at BETWEEN '2026-06-14' AND '2026-06-26'
AND severity = 'CRITICAL';