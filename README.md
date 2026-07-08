# 🧠 AINIS — AI Network Intelligence System

**Real-time network monitoring, ML-powered congestion prediction, and anomaly detection — built as a full-stack, production-style engineering project.**

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi)
![React](https://img.shields.io/badge/React-Frontend-61DAFB?logo=react)
![PyTorch](https://img.shields.io/badge/PyTorch-LSTM-EE4C2C?logo=pytorch)
![XGBoost](https://img.shields.io/badge/XGBoost-Congestion%20Model-brightgreen)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)
![Redis](https://img.shields.io/badge/Redis-PubSub-DC382D?logo=redis)
![InfluxDB](https://img.shields.io/badge/InfluxDB-TimeSeries-22ADF6?logo=influxdb)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

---

## 🚀 What is AINIS?

AINIS is a **4-layer, event-driven network intelligence platform** that simulates a live network, streams traffic telemetry in real time, and uses two independent machine learning models to predict congestion and detect anomalies — all visualized on a live React dashboard.

Built end-to-end by a 4-person engineering team over a 4-week sprint, this project mirrors how a real infrastructure/observability team ships software: proper Git workflow, Dockerized services, tested code, structured logging, CI/CD, and a rehearsed demo.

> **Note on traffic simulation:** Mininet requires native Linux kernel networking, which wasn't reliably available across the whole team's machines (Windows/WSL). To keep the pipeline platform-independent and fully reproducible, we replaced Mininet with a **custom synthetic traffic generator** that produces realistic packet-level and flow-level data (variable packet rate, latency, byte rate, protocol mix, and injected congestion/anomaly scenarios). Every downstream component — Redis pub/sub, FastAPI, InfluxDB, PostgreSQL, the ML models, and the dashboard — consumes this mock data exactly as it would consume real captured traffic, so the architecture is a drop-in fit for real packet capture (Scapy/Mininet or a live NIC tap) later.

---

## ✨ Key Features

- 📡 **Real-time telemetry pipeline** — synthetic traffic generator → Redis pub/sub → FastAPI → InfluxDB/PostgreSQL, streamed to the browser over WebSocket in under 1 second
- 🧮 **XGBoost congestion predictor** — classifies network congestion from live feature windows with 87% F1 on the synthetic dataset
- 🧠 **PyTorch LSTM autoencoder** — flags anomalous traffic via reconstruction error, with a tuned, configurable severity threshold
- 📊 **Live dashboard** — packet counters, rolling traffic charts, protocol breakdown, congestion gauge, anomaly severity badges, and a force-directed topology graph
- ⚙️ **Rule-based traffic prioritization engine** — configurable routing rules simulate QoS-style prioritization on the mock topology
- 🩺 **Full observability** — structured JSON logging, Prometheus-format metrics, per-service health checks, and a live in-dashboard log viewer
- 🔒 **Hardened API** — API-key auth on write endpoints, rate limiting, strict Pydantic validation, and consistent structured error responses
- 🧪 **Tested & CI'd** — 40+ backend tests (pytest), 15+ frontend tests (vitest), GitHub Actions running lint + test on every PR
- 🐳 **One-command deploy** — Dockerized microservices with an Nginx reverse proxy and a production Compose file

---

## 🏗️ Architecture

AINIS follows a **4-layer event-driven architecture**:

| Layer | Responsibility |
|---|---|
| **1. Ingestion** | The synthetic traffic generator emits packet/flow events (src/dst, protocol, size, latency) on a configurable schedule, including scripted congestion and attack scenarios. Events are published to a Redis channel within milliseconds. |
| **2. Processing** | FastAPI consumes from Redis pub/sub, writes time-series metrics to InfluxDB (line protocol) and structured events to PostgreSQL via SQLAlchemy. A WebSocket connection manager fans out live updates to every connected dashboard client. |
| **3. Intelligence** | A background `asyncio` scheduler pulls a fresh feature window from InfluxDB every 5 seconds and runs it through both the XGBoost congestion classifier and the PyTorch LSTM anomaly detector. Predictions above threshold create alerts in PostgreSQL and publish to a Redis alerts channel. A rule engine applies configured routing priorities to the simulated topology. |
| **4. Presentation** | The React dashboard subscribes over WebSocket for live data and calls REST endpoints for historical/aggregate data. Recharts renders traffic and protocol charts; a force-directed graph renders live topology; alert panels surface anomalies in real time. |

```
Synthetic Traffic Generator
        │  (packet/flow events)
        ▼
     Redis Pub/Sub
        │
        ▼
      FastAPI  ──────► InfluxDB (time-series metrics)
        │        ──────► PostgreSQL (events, alerts, predictions)
        │
        ├──► XGBoost Congestion Predictor
        ├──► PyTorch LSTM Anomaly Detector
        │
        ▼
   WebSocket Broadcast
        │
        ▼
   React Dashboard (charts · topology · alerts · health)
```

---

## 🛠️ Tech Stack

**Backend:** FastAPI · Python 3.11 · SQLAlchemy · Alembic · Pydantic · `asyncio`
**ML:** XGBoost · PyTorch (LSTM autoencoder) · scikit-learn · joblib
**Data:** PostgreSQL (relational) · InfluxDB (time-series) · Redis (pub/sub + cache)
**Frontend:** React · Vite · TailwindCSS · Recharts · react-force-graph
**Infra:** Docker & Docker Compose · Nginx · GitHub Actions · Prometheus-format metrics · `structlog`
**Testing:** pytest · httpx · vitest · @testing-library/react · locust (load testing)

---

## 📁 Project Structure

```
ainis/
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI route handlers
│   │   ├── core/           # Config, DB connections, startup
│   │   ├── models/         # SQLAlchemy + Pydantic models
│   │   ├── services/       # Business logic (monitoring, alerting, rule engine)
│   │   └── websocket/      # WS connection manager
│   ├── ml/
│   │   ├── congestion/     # XGBoost model, training + eval scripts
│   │   ├── anomaly/        # PyTorch LSTM autoencoder
│   │   └── data/           # Synthetic traffic + dataset generators
│   ├── simulator/          # Mock traffic / topology generator (replaces Mininet)
│   ├── tests/
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/     # Dashboard, charts, topology, alerts
│   │   ├── pages/
│   │   ├── hooks/          # useWebSocket, useMetrics
│   │   └── services/       # API client
│   └── Dockerfile
├── infra/
│   ├── docker-compose.yml
│   ├── docker-compose.prod.yml
│   ├── nginx/
│   └── scripts/            # deploy.sh, demo-mode.sh, DB seed scripts
├── docs/
│   ├── architecture.md
│   ├── api-spec.md
│   ├── data-model.md
│   ├── ml-model-card.md
│   ├── observability.md
│   ├── security.md
│   └── runbook.md
└── .github/workflows/       # test, lint, build pipelines
```

---

## ⚡ Quick Start

```bash
# clone and enter the repo
git clone https://github.com/<your-org>/ainis.git
cd ainis

# spin up the full stack: Postgres, InfluxDB, Redis, FastAPI, React, Nginx
docker-compose up --build

# seed a compelling demo scenario in one command
./infra/scripts/demo-mode.sh
```

Then open:
- **Dashboard:** `http://localhost:5173`
- **API docs (Swagger):** `http://localhost:8000/docs`
- **Adminer (DB inspection):** `http://localhost:8080`

Full setup, environment variables, and troubleshooting live in [`docs/runbook.md`](docs/runbook.md).

---

## 🎥 Live Demo Flow

1. `./infra/scripts/demo-mode.sh` — boots services and seeds realistic mock traffic
2. Open the dashboard — watch the live packet counter and traffic charts update in real time
3. `curl -X POST /simulate/congestion` — congestion gauge spikes within ~10 seconds
4. `curl -X POST /simulate/attack` — anomaly alert appears instantly in the alert panel
5. Topology graph — the affected link turns red under load
6. Routing rule engine kicks in — traffic visibly normalizes as priority queues apply
7. Close by walking through the LSTM autoencoder or the Redis pub/sub pipeline in code

---

## 🤖 Machine Learning

| Model | Task | Approach | Result |
|---|---|---|---|
| **XGBoost Classifier** | Congestion prediction | Gridsearched `max_depth`, `learning_rate`, `n_estimators` on engineered flow features | **87% F1** on synthetic test set |
| **PyTorch LSTM Autoencoder** | Anomaly detection | Reconstruction-error scoring over sliding time-series windows, tunable severity threshold | Validated: normal traffic → low error, injected spikes → correctly flagged critical |

Full details, inputs/outputs, and known limitations: [`docs/ml-model-card.md`](docs/ml-model-card.md).

**Known limitation (and the honest answer to "what would you improve"):** both models are trained on synthetic, generator-produced traffic, so their performance on real-world distributions is unvalidated. The natural next step is online learning against captured production traffic, plus data-drift detection to catch distribution shift.

---

## 🔒 Reliability, Testing & Security

- Global structured error handling across the API, with retry-and-buffer logic on the traffic generator's publisher if FastAPI is briefly unreachable
- Per-service health checks (`/health/redis`, `/health/influx`, `/health/postgres`) surfaced live on the dashboard
- 40+ backend tests and 15+ frontend tests, running automatically in CI on every PR
- API-key authentication on write endpoints, rate limiting (100 req/min/IP), and strict input validation
- Structured JSON logging and a Prometheus-compatible `/metrics/prometheus` endpoint for observability

---

## 🗺️ Roadmap

- **Near-term:** swap the synthetic generator for real packet capture (Scapy) against a live interface or a Mininet/Linux VM
- **Mid-term:** move from Redis pub/sub to Kafka for higher-throughput event streaming; deploy on Kubernetes
- **Long-term:** reinforcement-learning-driven routing rules, multi-datacenter metric federation, SHAP-based explainability for congestion predictions

---

## 👥 Team

Built by **Rehan, Bhavya, Devansh, and Jehan** — a 4-week, end-to-end sprint covering infrastructure, backend, ML, frontend, and DevOps, with every member able to explain and demo every layer of the system.

---

## 📄 License

MIT — see [`LICENSE`](LICENSE) for details.