import json
import logging
from datetime import datetime, timezone
from scapy.all import sniff, IP, TCP, UDP, ICMP

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

logger = logging.getLogger(__name__)

INTERFACE = None


def extract_packet_data(pkt):

    if IP not in pkt:
        return None

    ip_layer = pkt[IP]

    proto = "OTHER"
    src_port = None
    dst_port = None

    if TCP in pkt:
        proto = "TCP"
        src_port = pkt[TCP].sport
        dst_port = pkt[TCP].dport

    elif UDP in pkt:
        proto = "UDP"
        src_port = pkt[UDP].sport
        dst_port = pkt[UDP].dport

    elif ICMP in pkt:
        proto = "ICMP"

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "src_ip": ip_layer.src,
        "dst_ip": ip_layer.dst,
        "src_port": src_port,
        "dst_port": dst_port,
        "protocol": proto,
        "packet_length": len(pkt),
        "ttl": ip_layer.ttl,
    }


def packet_callback(pkt):

    data = extract_packet_data(pkt)

    if data:
        print(json.dumps(data))


def main():

    logger.info("Starting packet capture...")
    sniff(
        iface=INTERFACE, prn=packet_callback, store=False, filter="ip and not port 22"
    )


if __name__ == "__main__":
    main()
