import json
import logging
from datetime import datetime, timezone
from scapy.all import sniff, IP, TCP, UDP, ICMP

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

logger = logging.getLogger(__name__)

# Mininet Open vSwitch interfaces
INTERFACE = ["s1-eth1", "s1-eth2", "s1-eth3", "s1-eth4"]


def extract_packet_data(pkt):
    """
    Extract key packet metadata.
    Returns None if packet has no IP layer.
    """

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
    """
    Called for every captured packet.
    """

    data = extract_packet_data(pkt)

    if data:
        print(json.dumps(data))


def main():

    logger.info(f"Starting packet capture on interfaces: {INTERFACE}")

    logger.info("Press Ctrl+C to stop")

    sniff(
        iface=INTERFACE, prn=packet_callback, store=False, filter="ip and not port 22"
    )


if __name__ == "__main__":
    main()
