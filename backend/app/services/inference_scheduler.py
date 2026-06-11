"""
services/inference_scheduler.py

Background asyncio task. Runs every 5 seconds.
Pulls latest data from InfluxDB, runs both ML models,
writes results to PostgreSQL, publishes to Redis,
creates alerts if thresholds are crossed.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from app.services.auto_rule_manager import evaluate_rules

logger = logging.getLogger("ainis.scheduler")

INFERENCE_INTERVAL = 5
CONGESTION_ALERT_THRESH = 0.70
ANOMALY_ALERT_THRESH = 0.50

# These must match what scapy writes to InfluxDB
SEQ_LEN = 30
FEATURES = ["packet_rate", "avg_latency", "byte_rate", "flow_count", "tcp_ratio"]


async def _query_latest_summary(influx_client, bucket: str, org: str) -> dict | None:
    """Single most-recent metric row for XGBoost."""
    try:
        query = f"""
        from(bucket: \"{bucket}\")
          |> range(start: -30s)
          |> filter(fn: (r) => r._measurement == \"network_metrics\")
          |> last()
          |> pivot(rowKey: [\"_time\"], columnKey: [\"_field\"], valueColumn: \"_value\")
        """
        tables = influx_client.query_api().query(query=query, org=org)
        for table in tables:
            for record in table.records:
                return {f: float(record.values.get(f, 0.0)) for f in FEATURES}
        return None
    except Exception as e:
        logger.warning(f"[scheduler] InfluxDB summary query failed: {e}")
        return None


async def _query_window(
    influx_client, bucket: str, org: str
) -> list[list[float]] | None:
    """SEQ_LEN rows for LSTM. Pads with first row if fewer points exist."""
    try:
        query = f"""
        from(bucket: \"{bucket}\")
          |> range(start: -5m)
          |> filter(fn: (r) => r._measurement == \"network_metrics\")
          |> pivot(rowKey: [\"_time\"], columnKey: [\"_field\"], valueColumn: \"_value\")
          |> sort(columns: [\"_time\"], desc: false)
          |> limit(n: {SEQ_LEN})
        """
        tables = influx_client.query_api().query(query=query, org=org)
        rows = []
        for table in tables:
            for record in table.records:
                row = [float(record.values.get(f, 0.0)) for f in FEATURES]
                rows.append(row)

        if len(rows) == 0:
            return None

        while len(rows) < SEQ_LEN:
            rows.insert(0, rows[0])

        return rows[-SEQ_LEN:]
    except Exception as e:
        logger.warning(f"[scheduler] InfluxDB window query failed: {e}")
        return None


async def _save_prediction(
    session_factory, model_name, score, binary_output, severity, raw_features
):
    """Write one prediction row to PostgreSQL."""
    from app.models.prediction import Prediction

    async with session_factory() as session:
        pred = Prediction(
            model_name=model_name,
            score=score,
            binary_output=binary_output,
            severity=severity,
            raw_features=raw_features,
        )
        session.add(pred)
        await session.commit()


async def _create_alert(session_factory, redis_client, severity: str, message: str):
    """Write alert to PostgreSQL and publish to Redis alerts channel."""
    from app.models.alert import Alert, SeverityEnum

    severity_map = {
        "warning": SeverityEnum.MEDIUM,
        "critical": SeverityEnum.CRITICAL,
        "CONGESTED": SeverityEnum.HIGH,
    }
    db_severity = severity_map.get(severity, SeverityEnum.MEDIUM)

    try:
        async with session_factory() as session:
            alert = Alert(
                title=message[:255],
                description=message,
                severity=db_severity,
            )
            session.add(alert)
            await session.commit()

        await redis_client.publish(
            "alerts",
            json.dumps(
                {
                    "severity": severity,
                    "message": message,
                    "ts": datetime.now(timezone.utc).isoformat(),
                }
            ),
        )
        logger.info(f"[scheduler] Alert created: {message}")
    except Exception as e:
        logger.error(f"[scheduler] Alert creation failed: {e}")


async def run_inference_loop(app_state: dict):
    logger.info("[scheduler] Inference loop starting.")

    influx_client = app_state["influx_client"]
    session_factory = app_state["session_factory"]
    redis_client = app_state["redis_client"]
    settings = app_state["settings"]

    bucket = (
        settings.influxdb_bucket if hasattr(settings, "influxdb_bucket") else "metrics"
    )
    org = settings.influxdb_org if hasattr(settings, "influxdb_org") else "myorg"

    congestion_predictor = None
    anomaly_predictor = None
    latest_congestion_score = 0.0
    latest_anomaly_score = 0.0

    while True:
        try:
            await asyncio.sleep(INFERENCE_INTERVAL)

            if congestion_predictor is None:
                try:
                    from ml.congestion.predictor import get_predictor

                    congestion_predictor = get_predictor()
                    logger.info("[scheduler] Congestion predictor loaded.")
                except Exception as e:
                    logger.warning(f"[scheduler] Congestion predictor not ready: {e}")

            if anomaly_predictor is None:
                try:
                    from ml.anomaly.predictor import AnomalyPredictor

                    anomaly_predictor = AnomalyPredictor()
                    logger.info("[scheduler] Anomaly predictor loaded.")
                except Exception as e:
                    logger.warning(f"[scheduler] Anomaly predictor not ready: {e}")

            # XGBoost congestion
            if congestion_predictor is not None:
                summary = await _query_latest_summary(influx_client, bucket, org)
                if summary:
                    try:
                        result = congestion_predictor.predict_with_confidence(summary)
                        score = result["probability"]
                        latest_congestion_score = score
                        is_congested = result["prediction"] == 1

                        await _save_prediction(
                            session_factory,
                            model_name="xgboost-congestion",
                            score=score,
                            binary_output=is_congested,
                            severity="CONGESTED" if is_congested else "NORMAL",
                            raw_features=json.dumps(summary),
                        )

                        await redis_client.publish(
                            "predictions",
                            json.dumps(
                                {
                                    "model": "xgboost-congestion",
                                    "score": round(score, 4),
                                    "is_alert": score > CONGESTION_ALERT_THRESH,
                                    "ts": datetime.now(timezone.utc).isoformat(),
                                }
                            ),
                        )

                        if score > CONGESTION_ALERT_THRESH:
                            await _create_alert(
                                session_factory,
                                redis_client,
                                severity="CONGESTED",
                                message=f"High congestion probability: {score:.1%}",
                            )

                        logger.info(f"[scheduler] Congestion score={score:.4f}")
                    except Exception as e:
                        logger.error(f"[scheduler] Congestion inference failed: {e}")

            # LSTM anomaly
            if anomaly_predictor is not None:
                window = await _query_window(influx_client, bucket, org)
                if window:
                    try:
                        result = anomaly_predictor.predict(window)
                        score = result["anomaly_score"]
                        latest_anomaly_score = score
                        is_anomaly = result["is_anomaly"]
                        severity = result["severity"]

                        await _save_prediction(
                            session_factory,
                            model_name="lstm-anomaly",
                            score=score,
                            binary_output=is_anomaly,
                            severity=severity,
                            raw_features=json.dumps(window[-1]),
                        )

                        await redis_client.publish(
                            "predictions",
                            json.dumps(
                                {
                                    "model": "lstm-anomaly",
                                    "score": round(score, 4),
                                    "severity": severity,
                                    "is_alert": is_anomaly,
                                    "ts": datetime.now(timezone.utc).isoformat(),
                                }
                            ),
                        )

                        if is_anomaly:
                            await _create_alert(
                                session_factory,
                                redis_client,
                                severity=severity,
                                message=f"Anomaly detected - score {score:.3f}, severity {severity}",
                            )

                        logger.info(
                            f"[scheduler] Anomaly score={score:.4f} severity={severity}"
                        )
                    except Exception as e:
                        logger.error(f"[scheduler] Anomaly inference failed: {e}")

        except asyncio.CancelledError:
            logger.info("[scheduler] Inference loop cancelled.")
            break
        except Exception as e:
            logger.error(f"[scheduler] Unexpected error: {e}")
            await asyncio.sleep(INFERENCE_INTERVAL)
