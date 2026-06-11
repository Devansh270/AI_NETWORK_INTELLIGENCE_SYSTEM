# app/services/rule_engine.py
import redis
import json
import os
import logging
import sys
import requests

# capture/ is at backend/capture/, one level up from app/services/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "capture"))
from qos_manager import apply_qos_rule, clear_qos

logger = logging.getLogger(__name__)

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
API_BASE = os.getenv("API_BASE", "http://localhost:8000")
MONITORED_INTERFACES = os.getenv("MININET_INTERFACES", "s1-eth1,s1-eth2").split(",")


def fetch_active_rules():
    try:
        resp = requests.get(f"{API_BASE}/routing-rules/", timeout=5)
        return [r for r in resp.json() if r.get("is_active")]
    except Exception as e:
        logger.error(f"Failed to fetch rules: {e}")
        return []


def apply_all_rules():
    rules = fetch_active_rules()
    for iface in MONITORED_INTERFACES:
        clear_qos(iface.strip())
    for rule in rules:
        for iface in MONITORED_INTERFACES:
            apply_qos_rule(iface.strip(), rule)
    logger.info(f"Applied {len(rules)} rules to {len(MONITORED_INTERFACES)} interfaces")
    return rules


def run_rule_engine():
    r = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)
    pubsub = r.pubsub()
    pubsub.subscribe("routing_rules_updated")

    logger.info("Rule engine started, listening for rule changes...")

    apply_all_rules()

    for message in pubsub.listen():
        if message["type"] == "message":
            data = json.loads(message["data"])
            logger.info(f"Rule change detected: {data}")
            rules = apply_all_rules()
            logger.info(f"Rules re-applied: {len(rules)} active rules")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_rule_engine()