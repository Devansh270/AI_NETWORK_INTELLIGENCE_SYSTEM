import threading
import time
from datetime import datetime, timezone

import httpx

from scapy.all import sniff, IP, TCP, UDP, ICMP, get_if_list

# ─────────────────────────────────────────────────────────────
# FASTAPI ENDPOINT
# localhost for local testing
# fastapi for Docker container networking
# ─────────────────────────────────────────────────────────────
API_URL = "http://localhost:8000/metrics"

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

# CHANGE THIS TO YOUR ACTUAL INTERFACE
# Example:
# "Wi-Fi"
# "Ethernet"
INTERFACE = "Wi-Fi"


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
