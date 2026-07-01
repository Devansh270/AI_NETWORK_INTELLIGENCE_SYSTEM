"""
tests/load/locustfile.py

Day 17 WebSocket load test. Spawns N concurrent clients that each open a
WS connection to /ws/metrics and measure inter-message latency.

Note on measurement: ws.recv() blocks until the SERVER pushes the next
message. With Day 14's timeout=1.0 in the WS handler's Redis poll, this
test measures (a) how long until the next broadcast arrives, plus
(b) whether the server can sustain N concurrent connections.

True end-to-end latency (capture-to-client) would require timestamps in
the published payload - left as a follow-up for when scapy is the
publisher (mock_publisher already includes a timestamp field, but
backend doesn't currently forward it through the broadcast unchanged).

Usage (50 users, 5 min, headless):
    cd backend/tests/load
    locust -f locustfile.py --host=http://localhost:8000 \
        --users 50 --spawn-rate 5 --run-time 5m --headless \
        --csv=results

Prerequisites:
    1. uvicorn running (backend/)
    2. infra docker stack up (postgres, redis, influxdb)
    3. Either real scapy_agent.py OR mock_publisher.py publishing to redis
"""

import json
import os
import time

from locust import User, between, events, task

WS_BASE_URL = os.getenv("WS_BASE_URL", "ws://localhost:8000")


class WebSocketUser(User):
    wait_time = between(1, 2)
    abstract = False

    def on_start(self):
        import websocket

        try:
            self.ws = websocket.create_connection(
                f"{WS_BASE_URL}/ws/metrics",
                timeout=5,
            )
        except Exception as e:
            events.request.fire(
                request_type="WS",
                name="connect",
                response_time=0,
                response_length=0,
                exception=e,
            )
            self.ws = None

    @task
    def listen(self):
        if self.ws is None:
            return

        start = time.time()
        try:
            msg = self.ws.recv()
            elapsed_ms = (time.time() - start) * 1000

            events.request.fire(
                request_type="WS",
                name="recv ws/metrics",
                response_time=elapsed_ms,
                response_length=len(msg),
                exception=None,
            )

            # Light validation - the message must parse as JSON
            json.loads(msg)

        except Exception as e:
            events.request.fire(
                request_type="WS",
                name="recv ws/metrics",
                response_time=0,
                response_length=0,
                exception=e,
            )

    def on_stop(self):
        if self.ws is not None:
            try:
                self.ws.close()
            except Exception:
                pass