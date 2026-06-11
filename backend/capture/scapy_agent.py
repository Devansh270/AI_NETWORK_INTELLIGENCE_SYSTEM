import os
import threading
import time
from datetime import datetime, timezone
import redis
import json

import httpx

from scapy.all import sniff, IP, TCP, UDP, ICMP, conf, get_if_list

# ─────────────────────────────────────────────────────────────
# FASTAPI ENDPOINT
# localhost for local testing
# fastapi for Docker container networking
# ─────────────────────────────────────────────────────────────
API_URL = os.getenv("AINIS_API_URL", "http://localhost:8000/metrics")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")

print(
    f"[agent] Using API_URL={API_URL} | REDIS_HOST={REDIS_HOST}",
    flush=True,
)

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
# TELEMETRY STATS
# ─────────────────────────────────────────────────────────────
stats = {
    "sent": 0,
    "failed": 0,
}

# ─────────────────────────────────────────────────────────────
# SHOW AVAILABLE INTERFACES
# ─────────────────────────────────────────────────────────────
print("[agent] Available interfaces:")
print(get_if_list())


def choose_interface():
    """Use Scapy's active route interface unless AINIS_INTERFACE is set."""
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

        print(
            f"[agent] 1m summary: "
            f"{stats['sent']} packets sent, "
            f"{stats['failed']} failed",
            flush=True,
        )

        stats["sent"] = 0
        stats["failed"] = 0


# Background telemetry thread
threading.Thread(
    target=log_stats,
    daemon=True,
).start()


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

    try:

        # timeout prevents packet capture freezing
        with httpx.Client(timeout=2.0) as client:

            response = client.post(
                API_URL,
                json=payload,
            )

            if response.status_code == 201:

                stats["sent"] += 1

            else:

                stats["failed"] += 1

                print(
                    f"[agent][warn] " f"API returned " f"{response.status_code}",
                    flush=True,
                )

    except httpx.ConnectError:

        stats["failed"] += 1

        print(
            "[agent][warn] " "FastAPI unreachable, " "skipping packet",
            flush=True,
        )

    except httpx.TimeoutException:

        stats["failed"] += 1

        print(
            "[agent][warn] " "FastAPI timeout, " "skipping packet",
            flush=True,
        )

    # Publish to Redis pub/sub
    try:
        if redis_client:
            redis_client.publish("packets", json.dumps(payload))
            print("[Redis] Published packet to channel: packets", flush=True)
    except Exception as e:
        print(f"[agent][warn] Redis publish failed: {e}", flush=True)


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":

    print(
        "[agent] Starting packet capture...",
        flush=True,
    )

    print(
        f"[agent] Posting to {API_URL}",
        flush=True,
    )

    print(
        f"[agent] Capturing on interface: {INTERFACE}",
        flush=True,
    )

    sniff(
        iface=INTERFACE,
        prn=handle_packet,
        store=False,
    )
