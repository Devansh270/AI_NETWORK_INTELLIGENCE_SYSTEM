"""
tests/load/mock_publisher.py

Simulates scapy_agent by publishing fake packet events to Redis on the
"packets" channel. Used for platform-independent load testing on machines
that can't run live scapy (Mac, Windows native).

Devansh validates the same locust suite against live scapy on WSL at end of
day - this script exists so anyone on any platform can reproduce the test.

Usage:
    python3 backend/tests/load/mock_publisher.py
    # Publishes 20 messages/sec by default. Ctrl+C to stop.

Env vars:
    MOCK_RATE_PER_SEC  (default 20)  - target publish rate
    REDIS_HOST         (default localhost)
    REDIS_PORT         (default 6379)
"""

import json
import os
import random
import signal
import sys
import time

import redis


RATE = int(os.getenv("MOCK_RATE_PER_SEC", "20"))
HOST = os.getenv("REDIS_HOST", "localhost")
PORT = int(os.getenv("REDIS_PORT", "6379"))

INTERVAL = 1.0 / RATE


def make_packet() -> dict:
    return {
        "src_ip": f"10.0.0.{random.randint(1, 50)}",
        "dst_ip": f"10.0.0.{random.randint(1, 50)}",
        "src_port": random.randint(1024, 65000),
        "dst_port": random.choice([22, 53, 80, 123, 443, 8080]),
        "protocol": random.choices(["TCP", "UDP", "ICMP"], weights=[7, 2, 1])[0],
        "packet_length": random.randint(64, 1500),
        "timestamp": time.time(),
    }


def main():
    r = redis.Redis(host=HOST, port=PORT, decode_responses=True)
    r.ping()  # fail fast if redis unreachable
    print(f"[mock] connected to redis://{HOST}:{PORT}")
    print(f"[mock] publishing {RATE} packets/sec on channel 'packets'")
    print("[mock] Ctrl+C to stop")

    sent = 0
    start = time.time()

    def report(_signum=None, _frame=None):
        elapsed = time.time() - start
        rate = sent / elapsed if elapsed > 0 else 0
        print(f"\n[mock] sent {sent} packets over {elapsed:.1f}s = {rate:.1f}/sec")
        sys.exit(0)

    signal.signal(signal.SIGINT, report)

    while True:
        pkt = make_packet()
        r.publish("packets", json.dumps(pkt))
        sent += 1
        if sent % 100 == 0:
            print(f"[mock] sent {sent} packets")
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
