from prometheus_client import Counter, Gauge

packets_captured_total = Counter(
    "packets_captured_total", "Total packets captured by Scapy agent"
)
predictions_made_total = Counter(
    "predictions_made_total", "Total ML predictions made", ["model_name"]
)
active_connections = Gauge("active_connections", "Current active WebSocket connections")
