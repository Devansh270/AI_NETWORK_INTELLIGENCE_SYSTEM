import json
import pytest
from scapy.all import IP, TCP, UDP, ICMP, Ether

from capture.scapy_agent import (
    packet_to_payload,
    handle_packet,
    _post_once,
    _flush_buffer,
)
import capture.scapy_agent as agent_module


# ---------- packet_to_payload (pure function) ----------


def test_packet_to_payload_extracts_tcp_fields():
    pkt = IP(src="10.0.0.1", dst="10.0.0.2") / TCP(sport=443, dport=5000)
    payload = packet_to_payload(pkt)

    assert payload["src_ip"] == "10.0.0.1"
    assert payload["dst_ip"] == "10.0.0.2"
    assert payload["protocol"] == "TCP"
    assert payload["src_port"] == 443
    assert payload["dst_port"] == 5000
    assert "timestamp" in payload


def test_packet_to_payload_extracts_udp_fields():
    pkt = IP(src="10.0.0.5", dst="10.0.0.9") / UDP(sport=53, dport=5000)
    payload = packet_to_payload(pkt)
    assert payload["protocol"] == "UDP"
    assert payload["src_port"] == 53


def test_packet_to_payload_extracts_icmp_fields():
    pkt = IP(src="10.0.0.5", dst="10.0.0.9") / ICMP()
    payload = packet_to_payload(pkt)
    assert payload["protocol"] == "ICMP"
    assert payload["src_port"] == 0
    assert payload["dst_port"] == 0


def test_packet_to_payload_non_ip_returns_none():
    pkt = Ether()  # no IP layer at all
    payload = packet_to_payload(pkt)
    assert payload is None


def test_packet_to_payload_length_matches_packet_size():
    pkt = IP(src="10.0.0.1", dst="10.0.0.2") / TCP(sport=443, dport=5000)
    payload = packet_to_payload(pkt)
    assert payload["packet_length"] == len(pkt)


# ---------- handle_packet: HTTP live-send path ----------


class FakeHttpResponse:
    def __init__(self, status_code):
        self.status_code = status_code


class FakeHttpClient:
    """Stands in for httpx.Client — records calls, returns a canned response."""

    def __init__(self, status_code=201, raise_exc=None):
        self.status_code = status_code
        self.raise_exc = raise_exc
        self.calls = []

    def post(self, url, json=None):
        self.calls.append((url, json))
        if self.raise_exc:
            raise self.raise_exc
        return FakeHttpResponse(self.status_code)


class FakeRedisClient:
    def __init__(self):
        self.published = []

    def publish(self, channel, message):
        self.published.append((channel, message))


@pytest.fixture(autouse=True)
def clean_buffer():
    """The packet_buffer is a module-level deque — clear it before/after every test
    so tests don't bleed into each other."""
    agent_module.packet_buffer.clear()
    agent_module.stats.update({"sent": 0, "failed": 0, "buffered": 0, "dropped": 0})
    yield
    agent_module.packet_buffer.clear()


def test_handle_packet_sends_live_when_http_succeeds():
    pkt = IP(src="10.0.0.1", dst="10.0.0.2") / TCP(sport=443, dport=5000)
    fake_http = FakeHttpClient(status_code=201)
    fake_redis = FakeRedisClient()

    handle_packet(pkt, http_client_=fake_http, redis_client_=fake_redis)

    assert len(fake_http.calls) == 1
    assert len(agent_module.packet_buffer) == 0  # sent live, never buffered
    assert agent_module.stats["sent"] == 1


def test_handle_packet_buffers_when_http_unreachable():
    import httpx

    pkt = IP(src="10.0.0.1", dst="10.0.0.2") / TCP(sport=443, dport=5000)
    fake_http = FakeHttpClient(raise_exc=httpx.ConnectError("refused"))
    fake_redis = FakeRedisClient()

    handle_packet(pkt, http_client_=fake_http, redis_client_=fake_redis)

    assert len(agent_module.packet_buffer) == 1
    assert agent_module.stats["failed"] == 1
    assert agent_module.stats["buffered"] == 1


def test_handle_packet_skips_live_send_when_buffer_nonempty():
    """Once anything is buffered, new packets should go straight to the buffer
    (preserve ordering) instead of racing ahead via a live POST."""
    pkt = IP(src="10.0.0.1", dst="10.0.0.2") / TCP(sport=443, dport=5000)
    fake_http = FakeHttpClient(status_code=201)
    fake_redis = FakeRedisClient()

    agent_module.packet_buffer.append({"already": "queued"})

    handle_packet(pkt, http_client_=fake_http, redis_client_=fake_redis)

    assert len(fake_http.calls) == 0  # never attempted — buffer wasn't empty
    assert len(agent_module.packet_buffer) == 2


def test_handle_packet_drops_when_buffer_full():
    pkt = IP(src="10.0.0.1", dst="10.0.0.2") / TCP(sport=443, dport=5000)
    fake_http = FakeHttpClient(status_code=500)  # never succeeds -> always buffers
    fake_redis = FakeRedisClient()

    for _ in range(agent_module.MAX_BUFFER):
        agent_module.packet_buffer.append({"filler": True})

    handle_packet(pkt, http_client_=fake_http, redis_client_=fake_redis)

    assert agent_module.stats["dropped"] == 1


def test_handle_packet_publishes_to_redis_regardless_of_http_outcome():
    import httpx

    pkt = IP(src="10.0.0.1", dst="10.0.0.2") / TCP(sport=443, dport=5000)
    fake_http = FakeHttpClient(raise_exc=httpx.ConnectError("refused"))
    fake_redis = FakeRedisClient()

    handle_packet(pkt, http_client_=fake_http, redis_client_=fake_redis)

    assert len(fake_redis.published) == 1
    channel, message = fake_redis.published[0]
    assert channel == "packets"
    payload = json.loads(message)
    assert payload["src_ip"] == "10.0.0.1"


def test_handle_packet_non_ip_packet_is_ignored():
    pkt = Ether()
    fake_http = FakeHttpClient(status_code=201)
    fake_redis = FakeRedisClient()

    handle_packet(pkt, http_client_=fake_http, redis_client_=fake_redis)

    assert len(fake_http.calls) == 0
    assert len(fake_redis.published) == 0
    assert len(agent_module.packet_buffer) == 0


# ---------- buffer flush logic ----------


def test_post_once_returns_true_on_201():
    fake_http = FakeHttpClient(status_code=201)
    assert _post_once(fake_http, {"x": 1}) is True


def test_post_once_returns_false_on_non_201():
    fake_http = FakeHttpClient(status_code=500)
    assert _post_once(fake_http, {"x": 1}) is False


def test_post_once_returns_false_on_connect_error():
    import httpx

    fake_http = FakeHttpClient(raise_exc=httpx.ConnectError("refused"))
    assert _post_once(fake_http, {"x": 1}) is False


def test_flush_buffer_drains_when_http_recovers():
    fake_http = FakeHttpClient(status_code=201)
    agent_module.packet_buffer.extend([{"n": 1}, {"n": 2}, {"n": 3}])

    _flush_buffer(fake_http)

    assert len(agent_module.packet_buffer) == 0
    assert len(fake_http.calls) == 3


def test_flush_buffer_stops_at_first_failure_preserving_order():
    """If packet 2 fails, packet 3 should NOT be sent ahead of it —
    matches the agent's stated ordering guarantee."""
    call_results = [201, 500, 201]  # second call fails

    class FlakyHttpClient:
        def __init__(self):
            self.calls = []

        def post(self, url, json=None):
            self.calls.append(json)
            code = call_results[len(self.calls) - 1]
            return FakeHttpResponse(code)

    flaky = FlakyHttpClient()
    agent_module.packet_buffer.extend([{"n": 1}, {"n": 2}, {"n": 3}])

    _flush_buffer(flaky)

    # only packet 1 should have been popped; 2 and 3 remain, in order
    assert list(agent_module.packet_buffer) == [{"n": 2}, {"n": 3}]
    assert len(flaky.calls) == 2  # tried 1 (success), tried 2 (fail), stopped
