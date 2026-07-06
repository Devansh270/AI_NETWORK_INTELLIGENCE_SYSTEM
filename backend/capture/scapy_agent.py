import os
import threading
import time
from collections import deque
from datetime import datetime, timezone
import redis
import json

import httpx

from dotenv import load_dotenv
from pathlib import Path

from scapy.all import sniff, IP, TCP, UDP, ICMP, conf, get_if_list

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / "infra" / ".env")

# CONFIG
API_URL = os.getenv("AINIS_API_URL", "http://localhost:8000/metrics")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
API_KEY = os.getenv("AINIS_API_KEY", "")

MAX_BUFFER = 1000
RETRY_BACKOFF_SECONDS = [1, 2, 5]

# MODULE STATE
redis_client = None
http_client = None
buffer_lock = threading.Lock()
packet_buffer = deque(maxlen=MAX_BUFFER)
stats = {
    "sent": 0,
    "failed": 0,
    "buffered": 0,
    "dropped": 0,
}


def choose_interface():
    configured_interface = os.getenv("AINIS_INTERFACE")
    if configured_interface:
        return configured_interface
    return conf.iface


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


def _post_once(client: httpx.Client, payload: dict) -> bool:
    try:
        response = client.post(API_URL, json=payload)
        return response.status_code == 201
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


def _flush_buffer(client: httpx.Client):
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

        if _post_once(client, payload):
            with buffer_lock:
                if packet_buffer and packet_buffer[0] is payload:
                    packet_buffer.popleft()
            sent_count += 1
        else:
            break

    if sent_count:
        stats["sent"] += sent_count
        with buffer_lock:
            remaining = len(packet_buffer)
        print(
            f"[agent] flushed {sent_count} buffered packets, {remaining} remaining",
            flush=True,
        )


def flush_buffer_loop(client: httpx.Client):
    while True:
        time.sleep(3)
        _flush_buffer(client)


def handle_packet(pkt, http_client_=None, redis_client_=None):
    http_client_ = http_client_ if http_client_ is not None else http_client
    redis_client_ = redis_client_ if redis_client_ is not None else redis_client

    payload = packet_to_payload(pkt)
    if payload is None:
        return

    with buffer_lock:
        should_try_live = len(packet_buffer) == 0

    sent_live = False
    if should_try_live and http_client_ is not None:
        try:
            response = http_client_.post(API_URL, json=payload)
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

    try:
        if redis_client_:
            redis_client_.publish("packets", json.dumps(payload))
    except Exception as e:
        print(f"[agent][warn] Redis publish failed: {e}", flush=True)


def init_agent():
    global redis_client, http_client

    print(f"[agent] Using API_URL={API_URL} | REDIS_HOST={REDIS_HOST}", flush=True)

    try:
        redis_client = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)
        redis_client.ping()
        print("[agent] Redis connected", flush=True)
    except Exception as e:
        redis_client = None
        print(f"[agent][warn] Redis unavailable: {e}", flush=True)

    http_client = httpx.Client(timeout=2.0, headers={"X-API-Key": API_KEY})

    print("[agent] Available interfaces:")
    print(get_if_list())

    threading.Thread(target=log_stats, daemon=True).start()
    threading.Thread(target=flush_buffer_loop, args=(http_client,), daemon=True).start()

    return choose_interface()


if __name__ == "__main__":
    interface = init_agent()

    print("[agent] Starting packet capture...", flush=True)
    print(f"[agent] Posting to {API_URL}", flush=True)
    print(f"[agent] Capturing on interface: {interface}", flush=True)

    sniff(
        iface=interface,
        prn=handle_packet,
        store=False,
    )
