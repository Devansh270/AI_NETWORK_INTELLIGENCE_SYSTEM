import os
import threading
import time
from collections import deque
from datetime import datetime, timezone
import redis
import json

import httpx

from scapy.all import sniff, IP, TCP, UDP, ICMP, conf, get_if_list

# ─────────────────────────────────────────────────────────────
# FASTAPI ENDPOINT
# ─────────────────────────────────────────────────────────────
API_URL = os.getenv("AINIS_API_URL", "http://localhost:8000/metrics")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")

print(f"[agent] Using API_URL={API_URL} | REDIS_HOST={REDIS_HOST}", flush=True)

# ─────────────────────────────────────────────────────────────
# REDIS CLIENT
# ─────────────────────────────────────────────────────────────
try:
    redis_client = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)
    redis_client.ping()
    print("[agent] Redis connected", flush=True)
except Exception as e:
    redis_client = None
    print(f"[agent][warn] Redis unavailable: {e}", flush=True)

# ─────────────────────────────────────────────────────────────
# LONG-LIVED HTTP CLIENT (was being recreated per-packet before)
# ─────────────────────────────────────────────────────────────
http_client = httpx.Client(timeout=2.0)

# ─────────────────────────────────────────────────────────────
# RETRY BUFFER (NEW — Day 15 resilience requirement)
# ─────────────────────────────────────────────────────────────
MAX_BUFFER = 1000
RETRY_BACKOFF_SECONDS = [1, 2, 5]  # tried in order on a given flush attempt

buffer_lock = threading.Lock()
packet_buffer = deque(maxlen=MAX_BUFFER)

# ─────────────────────────────────────────────────────────────
# TELEMETRY STATS
# ─────────────────────────────────────────────────────────────
stats = {
    "sent": 0,
    "failed": 0,
    "buffered": 0,
    "dropped": 0,
}

# ─────────────────────────────────────────────────────────────
# SHOW AVAILABLE INTERFACES
# ─────────────────────────────────────────────────────────────
print("[agent] Available interfaces:")
print(get_if_list())


def choose_interface():
    configured_interface = os.getenv("AINIS_INTERFACE")
    if configured_interface:
        return configured_interface
    return conf.iface


INTERFACE = choose_interface()


# ─────────────────────────────────────────────────────────────
# LOG STATS EVERY 60 SECONDS
# ─────────────────────────────────────────────────────────────
def log_stats():
    while True:
        time.sleep(60)
        with buffer_lock:
            buffer_size = len(packet_buffer)
        print(
            f"[agent] 1m summary: "
            f"{stats['sent']} sent, "
            f"{stats['failed']} failed, "
            f"{stats['dropped']} dropped, "
            f"buffer={buffer_size}",
            flush=True,
        )
        stats["sent"] = 0
        stats["failed"] = 0
        stats["dropped"] = 0


threading.Thread(target=log_stats, daemon=True).start()


# ─────────────────────────────────────────────────────────────
# BACKGROUND BUFFER-FLUSH THREAD (NEW)
# Tries to drain the buffer every few seconds without blocking sniff()
# ─────────────────────────────────────────────────────────────
def flush_buffer_loop():
    while True:
        time.sleep(3)
        _flush_buffer()


def _post_once(payload: dict) -> bool:
    try:
        response = http_client.post(API_URL, json=payload)
        return response.status_code == 201
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


def _flush_buffer():
    with buffer_lock:
        if not packet_buffer:
            return
        snapshot_size = len(packet_buffer)

    sent_count = 0
    for _ in range(snapshot_size):
        with buffer_lock:
            if not packet_buffer:
                break
            payload = packet_buffer[0]

        if _post_once(payload):
            with buffer_lock:
                if packet_buffer and packet_buffer[0] is payload:
                    packet_buffer.popleft()
            sent_count += 1
        else:
            # still down — stop draining this round, retry next loop iteration
            break

    if sent_count:
        stats["sent"] += sent_count
        with buffer_lock:
            remaining = len(packet_buffer)
        print(
            f"[agent] flushed {sent_count} buffered packets, {remaining} remaining",
            flush=True,
        )


threading.Thread(target=flush_buffer_loop, daemon=True).start()


# ─────────────────────────────────────────────────────────────
# PACKET → JSON PAYLOAD
# ─────────────────────────────────────────────────────────────
def packet_to_payload(pkt):
    if IP not in pkt:
        return None

    if TCP in pkt:
        proto = "TCP"
        sport = pkt[TCP].sport
        dport = pkt[TCP].dport
    elif UDP in pkt:
        proto = "UDP"
        sport = pkt[UDP].sport
        dport = pkt[UDP].dport
    elif ICMP in pkt:
        proto = "ICMP"
        sport = 0
        dport = 0
    else:
        proto = "OTHER"
        sport = 0
        dport = 0

    return {
        "src_ip": pkt[IP].src,
        "dst_ip": pkt[IP].dst,
        "src_port": sport,
        "dst_port": dport,
        "protocol": proto,
        "packet_length": len(pkt),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ─────────────────────────────────────────────────────────────
# HANDLE PACKET
# ─────────────────────────────────────────────────────────────
def handle_packet(pkt):
    payload = packet_to_payload(pkt)
    if payload is None:
        return

    # If anything is already buffered, FastAPI is presumed down —
    # don't even try a live POST, just buffer in order. Avoids
    # reordering packets ahead of ones already waiting.
    with buffer_lock:
        should_try_live = len(packet_buffer) == 0

    sent_live = False
    if should_try_live:
        try:
            response = http_client.post(API_URL, json=payload)
            if response.status_code == 201:
                stats["sent"] += 1
                sent_live = True
            else:
                stats["failed"] += 1
                print(f"[agent][warn] API returned {response.status_code}", flush=True)
        except httpx.ConnectError:
            stats["failed"] += 1
            print("[agent][warn] FastAPI unreachable, buffering packet", flush=True)
        except httpx.TimeoutException:
            stats["failed"] += 1
            print("[agent][warn] FastAPI timeout, buffering packet", flush=True)

    if not sent_live:
        with buffer_lock:
            if len(packet_buffer) == MAX_BUFFER:
                stats["dropped"] += 1
            packet_buffer.append(payload)
            stats["buffered"] += 1

    # Publish to Redis pub/sub — independent of HTTP outcome, unchanged
    try:
        if redis_client:
            redis_client.publish("packets", json.dumps(payload))
    except Exception as e:
        print(f"[agent][warn] Redis publish failed: {e}", flush=True)


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("[agent] Starting packet capture...", flush=True)
    print(f"[agent] Posting to {API_URL}", flush=True)
    print(f"[agent] Capturing on interface: {INTERFACE}", flush=True)

    sniff(
        iface=INTERFACE,
        prn=handle_packet,
        store=False,
    )
