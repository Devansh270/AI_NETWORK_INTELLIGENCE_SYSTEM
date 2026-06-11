# AINIS — System Architecture

AINIS (AI Network Intelligence System) is a real-time network monitoring and intelligence platform. It captures live network traffic from a simulated Mininet environment, analyzes it using machine learning models to detect anomalies and predict congestion, and visualizes everything through a web dashboard. When a problem is detected, the system can automatically reroute traffic via an SDN controller.

This document describes the four layers of the system, the contracts between them, and the rationale behind the technology choices.

## High-level data flow

​```
Mininet → Scapy capture → Redis → Processing Worker → InfluxDB
                                                   ↓
                                              FastAPI + ML → PostgreSQL
                                                   ↓
                                              React Dashboard
​```

Every packet generated in Mininet flows through this pipeline. Raw packets enter on the left; structured intelligence (alerts, predictions, live metrics) exits on the right to the dashboard.

## The four layers

The system is structured as four layers, each with a single clear responsibility. Data flows downstream from Ingestion to Presentation; control signals (like routing changes) flow upstream from Intelligence back to the network.

### 1. Ingestion Layer

**Responsibility:** capture raw packets off the simulated network and push them into the pipeline as fast as possible. No analysis happens here.

**Components:**
- **Mininet** — creates the virtual network topology (routers, hosts, links) and generates real TCP/UDP packets between virtual hosts.
- **Scapy capture script** — a Python process that sniffs packets from Mininet's virtual interfaces, parses headers, and publishes each packet event to Redis.

**Why it's separate:** packet capture must be fast and lossless. Mixing analysis logic here would slow it down and risk dropping packets under load.

### 2. Processing Layer

**Responsibility:** turn raw packets into structured features the ML models can consume.

**Components:**
- **Processing worker** — a Python service that subscribes to the Redis packet stream, groups packets into 1-second time windows, and computes aggregate features per window (packets/sec, bytes/sec, unique source IPs, protocol distribution, average flow duration).
- **InfluxDB** — stores every time-windowed metric as a time-series point. Used by the dashboard for historical graphs.

**Why it's separate:** raw packets are too noisy for ML models. Aggregating into windows gives the models stable, comparable inputs and reduces the data volume by ~1000x.

### 3. Intelligence Layer

**Responsibility:** decide whether what's happening on the network is normal, anomalous, or about to become a problem. Take action when needed.

**Components:**
- **FastAPI service** — the central brain. Exposes REST endpoints for the frontend, hosts the ML models in-process, and manages a WebSocket connection for live updates.
- **ML models** — anomaly detection (Isolation Forest or autoencoder), congestion prediction (LSTM or simple regression on recent windows), and traffic classification (random forest on flow features).
- **PostgreSQL** — stores structured records: alerts, predictions, model versions, user-configured thresholds, and routing decisions.
- **(Future) Ryu SDN controller** — receives commands from FastAPI to actually change routing rules in Mininet when congestion or attacks are detected.

**Why it's separate:** this is the only layer that makes decisions. Keeping it isolated means we can swap models, retrain offline, or change thresholds without touching the rest of the system.

### 4. Presentation Layer

**Responsibility:** make everything visible and controllable to a human operator.

**Components:**
- **React dashboard** — single-page app with four routes: live dashboard, network topology, alerts feed, routing log.
- **WebSocket connection to FastAPI** — receives live events (new alerts, traffic spikes, routing changes) and updates the UI without polling.
- **REST calls to FastAPI** — used for historical data (graphs, alert history) and user actions (trigger simulation, configure threshold).

**Why it's separate:** the frontend should never talk directly to the database or the ML models. Every read and write goes through FastAPI, which means we have one place to enforce auth, validation, and rate limits later.

## Service contracts

Every boundary in the system is defined by a data contract — the exact shape of the message that crosses it. The four contracts below are the source of truth. If a service produces or consumes data that doesn't match one of these shapes, that's a bug.

### Contract 1 — Scapy capture → Redis

Published to Redis channel `packets.raw`. One message per captured packet.

​```json
{
  "timestamp": "2026-05-25T06:01:38.123Z",
  "src_ip": "10.0.0.1",
  "dst_ip": "10.0.0.5",
  "src_port": 54321,
  "dst_port": 80,
  "protocol": "TCP",
  "length": 1480,
  "flags": "SYN",
  "link": "R1-R2"
}
​```

**Notes:** `link` identifies which network edge the packet was captured on — needed later to know which link is congested. `flags` is TCP-specific and may be `null` for UDP.

### Contract 2 — Processing worker → InfluxDB

Written to InfluxDB measurement `traffic_window`. One point per link per 1-second window.

​```json
{
  "measurement": "traffic_window",
  "tags": {
    "link": "R1-R2"
  },
  "fields": {
    "packets_per_sec": 1240,
    "bytes_per_sec": 1830400,
    "unique_src_ips": 47,
    "tcp_ratio": 0.82,
    "udp_ratio": 0.15,
    "avg_packet_size": 1476
  },
  "time": "2026-05-25T06:01:39Z"
}
​```

**Notes:** tags are indexed (good for filtering by link); fields are the actual numeric metrics. Window size is fixed at 1 second for the MVP — can be made configurable later.

### Contract 3 — FastAPI → PostgreSQL (alerts table)

One row inserted per detected anomaly.

​```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-05-25T06:01:40Z",
  "type": "DDOS",
  "severity": "HIGH",
  "source_ip": "10.0.0.99",
  "target_ip": "10.0.0.5",
  "confidence": 0.94,
  "action_taken": "BLOCKED",
  "model_version": "anomaly_v1.2",
  "raw_features": { "packets_per_sec": 18420, "unique_src_ips": 1 }
}
​```

**Notes:** `type` is one of `DDOS`, `PORT_SCAN`, `CONGESTION`, `UNKNOWN_ANOMALY`. `severity` is `LOW | MEDIUM | HIGH | CRITICAL`. `raw_features` is the exact feature vector that triggered the alert — kept for debugging and model retraining.

### Contract 4 — FastAPI → React (WebSocket events)

Pushed over WebSocket connection at `/ws/live`. Multiple event types share one channel.

​```json
{
  "event": "alert.new",
  "payload": { /* alert object from Contract 3 */ }
}
​```

​```json
{
  "event": "metrics.update",
  "payload": {
    "link": "R1-R2",
    "packets_per_sec": 1240,
    "bytes_per_sec": 1830400,
    "timestamp": "2026-05-25T06:01:39Z"
  }
}
​```

​```json
{
  "event": "routing.changed",
  "payload": {
    "from_path": ["R1", "R2"],
    "to_path": ["R1", "R3", "R2"],
    "reason": "congestion_predicted",
    "timestamp": "2026-05-25T06:01:41Z"
  }
}
​```

**Notes:** every event has the same envelope (`event` + `payload`). New event types can be added without breaking the frontend — it just ignores events it doesn't recognize.

## Technology choices

Every technology in this stack was chosen for a specific reason. This section documents the rationale so future maintainers (and the team in interviews) can defend each choice.

### Why FastAPI for the backend

FastAPI is async-native, which matters because this service does three things concurrently: serving REST requests from the dashboard, running ML inference on incoming feature windows, and pushing live updates over WebSockets. A synchronous framework (Flask, Django) would either block on one of these or force us into a threadpool workaround.

Beyond async, FastAPI gives us automatic OpenAPI documentation — the frontend team can see the exact API contract at `/docs` without us writing it twice — and Pydantic validation at the boundary, which means malformed payloads are rejected before they reach our business logic.

The alternative we considered was Flask. Rejected because async support is bolted on rather than native, and WebSocket support requires an extra extension.

### Why InfluxDB and PostgreSQL together

These two databases serve fundamentally different access patterns, and forcing both into one store would have been a mistake either direction.

**Time-series data** (traffic metrics, packets-per-second, bandwidth) is high-write, append-only, queried by time ranges, and aggregated into rollups (last 5 min, last hour). InfluxDB is purpose-built for this — it compresses time-series points efficiently and has time-window queries as first-class operations. Storing this in Postgres would mean slow window queries and storage bloat.

**Relational data** (alerts, users, model versions, routing decisions) is lower-volume but needs foreign keys, joins, transactions, and arbitrary filtering. Postgres is the obvious fit. Storing this in InfluxDB would mean no joins, no referential integrity, and painful queries like "show me all CRITICAL alerts in the last week grouped by source IP."

The cost is operational complexity — two databases to back up and monitor — but the payoff in query performance and code clarity is worth it for this workload.

### Why Redis for the message bus

Redis pub/sub sits between the packet capture layer and the processing worker. It exists to decouple their rates: Scapy may capture packets in bursts of thousands per second, while the worker processes at a steady rate. Without a buffer in between, the worker would either drop packets or back-pressure the capture (which means losing them anyway).

Redis was chosen over alternatives like Kafka because the volume here is moderate (we don't need partitioned topics or weeks of retention), the latency requirement is tight (we want sub-second from capture to dashboard), and Redis is operationally trivial — one Docker container, no Zookeeper, no broker tuning. Kafka would be the right choice at 10x our scale; at this scale it's overkill.

Redis also doubles as the pub/sub layer for the WebSocket fan-out — when FastAPI generates an alert, it publishes to Redis, and any connected WebSocket can subscribe. This means the system scales horizontally later (multiple FastAPI instances) without re-architecting.

### Why React for the frontend

React was chosen primarily for component reusability across the four dashboard pages and the ecosystem of charting libraries (Recharts, Chart.js, D3) that integrate well with it. The dashboard has many small live-updating widgets — graphs, alert cards, topology nodes — and React's component model fits this naturally.

Vite (the build tool) was chosen over Create React App because CRA is deprecated and Vite's dev server is significantly faster on the kind of incremental edits we'll be making.

### Why Mininet for the simulated network

Mininet was chosen over physical hardware or cloud-based testbeds because it runs entirely on one laptop, uses real Linux network stacks (so packets are genuinely real, not simulated abstractions), and is the de facto standard for SDN research — which means our work is reproducible and the techniques transfer directly to real deployments. The constraint is scale: Mininet works well up to ~100 nodes; beyond that we'd need something like GNS3 or a real testbed.

## Scope and non-goals

This section documents what AINIS does **not** do, so the team and reviewers have a clear picture of the MVP boundary.

### In scope for the MVP

- Packet capture from a Mininet simulated network (up to ~10 nodes, ~5 links).
- Real-time feature extraction in 1-second windows.
- Anomaly detection trained on the CICIDS2017 dataset (DDoS, port scan, normal traffic).
- Congestion prediction on a short forecast horizon (next 30–60 seconds).
- Live dashboard with traffic graphs, topology view, alerts feed, and a simulation control panel.
- Scripted attack and congestion simulations triggered from the dashboard.

### Explicitly out of scope (for the MVP)

- **Deployment on real network hardware.** The system is designed to be portable to real networks, but the MVP runs only in Mininet on a single laptop.
- **Multi-user authentication.** The dashboard assumes a single trusted operator. No login, roles, or audit log.
- **Reinforcement learning for routing decisions.** Initial routing changes are rule-based (if link utilization > threshold, reroute). RL is a stretch goal for later.
- **Encrypted traffic inspection.** We analyze packet headers and flow features only. No deep packet inspection of payload, no TLS decryption.
- **Distributed deployment.** All services run on one host via Docker Compose. Horizontal scaling (multiple FastAPI instances, Redis cluster) is designed-for but not built.
- **Production-grade alerting.** Alerts appear on the dashboard. They are not sent to email, Slack, PagerDuty, or any external system.
- **Persistent model retraining.** Models are trained offline on CICIDS2017 and loaded at service start. There is no online learning loop.

### Known limitations of the chosen approach

- **Synthetic traffic ≠ real enterprise traffic.** CICIDS2017 is the closest publicly available substitute, but a model that performs well on it may show higher false-positive rates on real traffic. This is documented in the evaluation section of the final report.
- **Single-host bottleneck.** With everything running in Docker on one laptop, sustained traffic above ~10k packets/sec will degrade dashboard responsiveness. This is a deliberate trade-off for development simplicity.
- **Mininet abstraction gap.** Mininet's virtual switches behave correctly for L2/L3 but don't perfectly replicate physical switch buffer behavior under extreme load. Conclusions about congestion behavior under DDoS should be qualified accordingly.

## Glossary

- **AINIS** — AI Network Intelligence System, the project name.
- **SDN** — Software-Defined Networking. The paradigm where a software controller manages routing rules across network devices, rather than each device deciding independently.
- **Mininet** — A network emulator that creates virtual hosts, switches, and links on a single machine, using real Linux network namespaces.
- **Scapy** — A Python library for packet manipulation and capture.
- **Ryu** — A Python-based SDN controller framework, used to programmatically change routing rules.
- **CICIDS2017** — A labeled network intrusion detection dataset from the University of New Brunswick, used to train the anomaly detection model.
- **QoS** — Quality of Service. Prioritization of certain traffic types (e.g., video calls) over others (e.g., background sync).

---

*Document owner: Jehan. Last updated: Day 1 of Week 1. Architecture decisions are open for discussion in the kickoff meeting; once merged, changes require a PR with team review.*