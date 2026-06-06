import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from capture.scapy_agent import packet_to_payload

from scapy.all import IP, TCP, UDP, ICMP


def test_tcp_packet_conversion():

    pkt = IP(src="192.168.1.1", dst="192.168.1.2") / TCP(sport=1234, dport=80)

    payload = packet_to_payload(pkt)

    assert payload["src_ip"] == "192.168.1.1"
    assert payload["dst_ip"] == "192.168.1.2"
    assert payload["src_port"] == 1234
    assert payload["dst_port"] == 80
    assert payload["protocol"] == "TCP"


def test_udp_packet_conversion():

    pkt = IP(src="10.0.0.1", dst="10.0.0.2") / UDP(sport=5000, dport=53)

    payload = packet_to_payload(pkt)

    assert payload["protocol"] == "UDP"
    assert payload["src_port"] == 5000
    assert payload["dst_port"] == 53


def test_icmp_packet_conversion():

    pkt = IP(src="8.8.8.8", dst="1.1.1.1") / ICMP()

    payload = packet_to_payload(pkt)

    assert payload["protocol"] == "ICMP"
    assert payload["src_port"] == 0
    assert payload["dst_port"] == 0


def test_non_ip_packet_returns_none():

    pkt = TCP(sport=1111, dport=2222)

    payload = packet_to_payload(pkt)

    assert payload is None


def test_packet_length_positive():

    pkt = IP(src="1.1.1.1", dst="2.2.2.2") / TCP(sport=1111, dport=80)

    payload = packet_to_payload(pkt)

    assert payload["packet_length"] > 0


def test_timestamp_exists():

    pkt = IP(src="1.1.1.1", dst="2.2.2.2") / TCP(sport=1111, dport=80)

    payload = packet_to_payload(pkt)

    assert "timestamp" in payload
    assert payload["timestamp"] is not None
