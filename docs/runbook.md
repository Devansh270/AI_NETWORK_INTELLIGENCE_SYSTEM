## REHAN:
## 1. Prerequisites & First-Time Setup

### Required tools

| Tool | Version | Download |
|---|---|---|
| Python | 3.11+ | https://python.org/downloads |
| Node | 20+ | https://nodejs.org |
| Docker Desktop | 24+ | https://docker.com/products/docker-desktop |
| Git | any | https://git-scm.com |

Verify after install:

```bash
python3 --version
node --version
npm --version
docker --version
git --version
```

### Clone

```bash
git clone https://github.com/YOUR_ORG/ainis.git
cd ainis
git checkout develop
```

### Create backend/.env

```bash
cp backend/.env.example backend/.env
```

Paste this into `backend/.env`:

```
POSTGRES_URL=postgresql+asyncpg://ainis:ainis@localhost:5432/ainis
INFLUX_URL=http://localhost:8086
INFLUX_TOKEN=ainis-super-secret-auth-token
INFLUX_ORG=ainis
INFLUX_BUCKET=metrics
REDIS_HOST=localhost
REDIS_PORT=6379
API_KEY=dev-api-key-change-in-prod
```

### Create frontend/.env

```bash
cp frontend/.env.example frontend/.env
```

Paste this into `frontend/.env`:

```
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws/metrics
```

### Start Docker services

```bash
cd infra
docker compose up -d
docker ps
```

Expected — all 4 containers show **Up**:

```
infra-postgres-1    Up
infra-influxdb-1    Up
infra-redis-1       Up
infra-adminer-1     Up
```

### Install Python dependencies

```bash
cd backend
pip install -r requirements.txt
```

### Run database migrations

```bash
cd backend
alembic upgrade head
```

Expected:

```
INFO  [alembic.runtime.migration] Running upgrade  -> a1b2c3d4e5f6, initial schema
```

Verify tables:

```bash
docker exec -it infra-postgres-1 psql -U ainis -d ainis -c "\dt"
```

Expected:

```
 public | alerts         | table | ainis
 public | anomalies      | table | ainis
 public | network_events | table | ainis
 public | routing_rules  | table | ainis
```

### Install frontend dependencies

```bash
cd frontend
npm install
```

### Start all services — open 4 separate terminals

**Terminal 1 — FastAPI**

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 — React**

```bash
cd frontend
npm run dev
```

**Terminal 3 — Scapy (needs sudo)**

```bash
cd backend
sudo python capture/scapy_agent.py
```

**Terminal 4 — Traffic**

```bash
ping -c 500 8.8.8.8
```

### Verify

```bash
curl -s http://localhost:8000/health | python3 -m json.tool
```

Expected:

```json
{
    "status": "healthy",
    "services": {
        "postgres": "up",
        "influxdb": "up",
        "redis": "up"
    }
}
```

Open `http://localhost:5173` — PacketCounter must increment.

### Full reset (nuclear)

```bash
cd ainis
docker compose -f infra/docker-compose.yml down -v
rm -rf frontend/node_modules frontend/.vite
find . -name '__pycache__' -exec rm -rf {} + 2>/dev/null
find . -name '*.pyc' -delete
```

Then repeat from **Start Docker services** above.

---
## JEHAN:
## 2. FastAPI Troubleshooting

### Start the server

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Health check — run this first whenever anything is broken

```bash
curl -s http://localhost:8000/health | python3 -m json.tool
```

Expected:

```json
{
    "status": "healthy",
    "services": {
        "postgres": "up",
        "influxdb": "up",
        "redis": "up"
    }
}
```

### List all registered routes

```bash
curl -s http://localhost:8000/openapi.json | python3 -c "
import json, sys
doc = json.load(sys.stdin)
for path, methods in doc['paths'].items():
    for method in methods:
        print(f'{method.upper():6} {path}')
"
```

### Test endpoints

```bash
curl -s http://localhost:8000/health

curl -s http://localhost:8000/metrics/summary | python3 -m json.tool

curl -s http://localhost:8000/alerts | python3 -m json.tool

curl -s -X POST http://localhost:8000/alerts \
  -H "Content-Type: application/json" \
  -d '{"severity":"warning","message":"test alert","source":"manual"}' \
  | python3 -m json.tool

curl -s -X POST http://localhost:8000/metrics \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp":"2024-01-01T00:00:00Z",
    "src_ip":"192.168.1.1",
    "dst_ip":"8.8.8.8",
    "src_port":54321,
    "dst_port":443,
    "protocol":"TCP",
    "length":64,
    "ttl":64
  }' | python3 -m json.tool
```

### Fix: ImportError — No module named app

```bash
# Wrong — do not run from wrong dir
uvicorn app.main:app --reload

# Correct
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Fix: postgres shows "down" in /health

```bash
docker ps | grep postgres
cd infra && docker compose up -d postgres
sleep 5
curl -s http://localhost:8000/health | python3 -m json.tool
```

If container is running but still shows down — token or URL mismatch:

```bash
cat backend/.env | grep POSTGRES_URL
docker exec -it infra-postgres-1 psql -U ainis -d ainis -c "SELECT 1;"
```

### Fix: influxdb shows "down" in /health

```bash
cat backend/.env | grep INFLUX
cat infra/docker-compose.yml | grep INFLUX
curl -s -o /dev/null -w "%{http_code}" http://localhost:8086/ping
# Expected: 204
```

INFLUX_TOKEN in `.env` must exactly match `DOCKER_INFLUXDB_INIT_ADMIN_TOKEN` in `docker-compose.yml`.

### Fix: redis shows "down" in /health

```bash
docker exec infra-redis-1 redis-cli ping
# Expected: PONG

cat backend/.env | grep REDIS
# Must be: REDIS_HOST=localhost REDIS_PORT=6379
```

### Fix: CORS error in browser

Confirm `backend/app/main.py` contains:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Fix: WebSocket not connecting

```bash
npm install -g wscat
wscat -c ws://localhost:8000/ws/metrics
# Must stay connected — ping messages appear every 30s
```

### Environment variables FastAPI requires

```
POSTGRES_URL     postgresql+asyncpg://ainis:ainis@localhost:5432/ainis
INFLUX_URL       http://localhost:8086
INFLUX_TOKEN     ainis-super-secret-auth-token
INFLUX_ORG       ainis
INFLUX_BUCKET    metrics
REDIS_HOST       localhost
REDIS_PORT       6379
API_KEY          dev-api-key-change-in-prod
```

---
## BHAVYA:
## 3. Database Operations

### PostgreSQL — Adminer web UI

Open `http://localhost:8080`

```
System:   PostgreSQL
Server:   postgres
Username: ainis
Password: ainis
Database: ainis
```

### PostgreSQL — psql command line

```bash
docker exec -it infra-postgres-1 psql -U ainis -d ainis
```

```sql
\dt

\d alerts
\d network_events

SELECT COUNT(*) FROM alerts;
SELECT COUNT(*) FROM network_events;
SELECT COUNT(*) FROM anomalies;
SELECT COUNT(*) FROM routing_rules;

SELECT id, severity, message, created_at
FROM alerts
ORDER BY created_at DESC
LIMIT 10;

SELECT src_ip, dst_ip, protocol, length, created_at
FROM network_events
ORDER BY created_at DESC
LIMIT 10;

SELECT protocol, COUNT(*) AS count
FROM network_events
GROUP BY protocol
ORDER BY count DESC;

\q
```

### Alembic migrations

```bash
cd backend

alembic upgrade head

alembic current

alembic history

alembic downgrade -1

alembic downgrade base
```

### Reset PostgreSQL — deletes all data

```bash
cd infra
docker compose stop postgres
docker compose rm -f postgres
docker volume ls
docker volume rm infra_postgres_data

docker compose up -d postgres
sleep 10

cd ../backend
alembic upgrade head

docker exec -it infra-postgres-1 psql -U ainis -d ainis -c "\dt"
```

### Fix: alembic — "relation already exists"

```bash
alembic stamp head
```

### Fix: alembic — "Multiple head revisions"

```bash
alembic heads
alembic merge heads
alembic upgrade head
```

### Fix: asyncpg ConnectionRefusedError

```bash
docker ps | grep postgres
cat backend/.env | grep POSTGRES_URL
cd infra && docker compose up -d postgres
```

### InfluxDB — web UI

Open `http://localhost:8086`

```
Username: admin
Password: adminpassword
```

### InfluxDB — run verification script

```bash
python infra/check_influx.py
```

Expected (empty):

```
InfluxDB: connected
Total packet records (last 24h): 0
Bucket is empty — no packets captured yet
```

Expected (after Scapy runs):

```
InfluxDB: connected
Total packet records (last 24h): 3847
Latest 5 records (last 1 hour):
  [2024-01-01 12:34:56+00:00] length=64  tags={'protocol': 'TCP', ...}
```

### InfluxDB — query from terminal

```bash
docker exec -it infra-influxdb-1 influx query \
  --org ainis \
  --token ainis-super-secret-auth-token \
  'from(bucket:"metrics") |> range(start:-1h) |> filter(fn:(r) => r._measurement == "packets") |> count()'

docker exec -it infra-influxdb-1 influx query \
  --org ainis \
  --token ainis-super-secret-auth-token \
  'from(bucket:"metrics") |> range(start:-1h) |> sort(columns:["_time"],desc:true) |> limit(n:5)'
```

### InfluxDB — clear bucket

```bash
docker exec -it infra-influxdb-1 influx bucket delete \
  --name metrics \
  --org ainis \
  --token ainis-super-secret-auth-token

docker exec -it infra-influxdb-1 influx bucket create \
  --name metrics \
  --org ainis \
  --retention 168h \
  --token ainis-super-secret-auth-token

python infra/check_influx.py
```

### Fix: InfluxDB 401 Unauthorized

Get token from UI: `Data > API Tokens > Copy`
Update `INFLUX_TOKEN` in `backend/.env`

### Fix: InfluxDB 404 bucket not found

```bash
docker exec -it infra-influxdb-1 influx bucket create \
  --name metrics \
  --org ainis \
  --retention 168h \
  --token ainis-super-secret-auth-token
```

### Fix: InfluxDB ping fails

```bash
cd infra && docker compose up -d influxdb
sleep 5
curl -s -o /dev/null -w "%{http_code}" http://localhost:8086/ping
# Expected: 204
```

### Redis — CLI

```bash
docker exec -it infra-redis-1 redis-cli
```

```bash
PING

PUBSUB CHANNELS

SUBSCRIBE packets

DBSIZE

KEYS *

FLUSHALL

EXIT
```

### Redis — watch live packets

```bash
docker exec -it infra-redis-1 redis-cli SUBSCRIBE packets
```

Run `ping -c 10 8.8.8.8` in another terminal.
JSON packet objects must appear within 5 seconds.

### Fix: Redis connection refused

```bash
cd infra && docker compose up -d redis
sleep 3
docker exec infra-redis-1 redis-cli ping
# Expected: PONG
```

---
## DEVANSH:
## 4. Frontend Troubleshooting

### Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Expected:

```
  VITE v5.x.x  ready in 312 ms
  ➜  Local:   http://localhost:5173/
```

### frontend/.env template

```
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws/metrics
```

Verify env vars are loaded in browser DevTools console:

```javascript
import.meta.env.VITE_API_URL
// Expected: "http://localhost:8000"
```

### Fix: npm not found

Install Node 20+ from https://nodejs.org — close and reopen terminal after install.

### Fix: Cannot find module recharts (or any package)

```bash
cd frontend
npm install
```

### Fix: blank page

Open DevTools (F12) > Console. Then check:

```bash
curl -s http://localhost:8000/health
# If this fails — start FastAPI first (Terminal 1)
cat frontend/.env | grep VITE_API_URL
# Must be: VITE_API_URL=http://localhost:8000
```

### Fix: CORS error in browser

Error text: `Access to fetch at 'http://localhost:8000' has been blocked by CORS policy`

Confirm `backend/app/main.py` contains:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Fix: WebSocket shows "disconnected"

```bash
curl -s http://localhost:8000/health
# Must return healthy — if not, fix backend first

npm install -g wscat
wscat -c ws://localhost:8000/ws/metrics
# Must stay connected and show {"type":"ping"} every 30s

cat frontend/.env | grep WS
# Must be: VITE_WS_URL=ws://localhost:8000/ws/metrics
# NOT https:// — must be ws://
```

After fixing `.env`:

```bash
# Ctrl+C to stop, then:
npm run dev
```

### Fix: PacketCounter not incrementing

```bash
# Step 1 — is Scapy capturing?
# Terminal 3 must show: [scapy_agent] Captured X packets

# Step 2 — is Redis getting packets?
docker exec -it infra-redis-1 redis-cli SUBSCRIBE packets
ping -c 10 8.8.8.8
# Packet JSON must appear in Redis within 5 seconds

# Step 3 — is WebSocket connected?
# DevTools > Network > WS tab
# Must show active connection to ws://localhost:8000/ws/metrics

# Step 4 — any JS errors?
# DevTools > Console — look for red errors
```

### Fix: ProtocolBreakdown pie chart empty

Generate varied traffic:

```bash
ping -c 50 8.8.8.8 &
curl -s https://example.com > /dev/null &
curl -s https://httpbin.org/get > /dev/null &
nslookup google.com 8.8.8.8 &
```

Wait 15 seconds. Chart needs at least 2 protocol types to render.

### Fix: MetricsPanel line chart flat

```bash
ping -c 500 8.8.8.8
```

Line chart requires 5+ data points. Wait 15 seconds after ping starts.

### Fix: Vite stale module errors

```bash
rm -rf frontend/.vite
npm run dev
```

### Fix: Wrong Node version

```bash
node --version
# Must be v20.x.x — if not, install from nodejs.org
```

### React codebase quick reference

```
frontend/src/
├── hooks/
│   └── useWebSocket.js       opens WS, returns live data as state
├── components/
│   ├── PacketCounter.jsx     total packet count from WS
│   ├── ProtocolBreakdown.jsx Recharts PieChart — TCP/UDP/ICMP
│   ├── MetricsPanel.jsx      Recharts LineChart — packets/sec over time
│   ├── TopologyGraph.jsx     force-directed network graph
│   └── AlertsPanel.jsx       real-time anomaly alerts
├── pages/
│   ├── Dashboard.jsx         main page — all panels assembled here
│   ├── Topology.jsx          full-screen topology view
│   └── Alerts.jsx            full alert history
└── services/
    └── api.js                HTTP client — wraps fetch() for REST calls
```

Data flow:

```
ws://localhost:8000/ws/metrics
  → useWebSocket.js  (connection + state)
    → Dashboard.jsx  (distributes to children)
      → PacketCounter    (receives total count)
      → ProtocolBreakdown (receives {TCP:n, UDP:n, ICMP:n})
      → MetricsPanel     (receives [{time, pps}, ...])
```

Guard for ping messages in useWebSocket.js:

```javascript
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'ping') return;   // ignore keepalives
  // handle real data below
};
```

---

## 5. Verification Checklist

Run every command. All must pass before calling the system working.

### Infrastructure

```bash
docker ps | grep -E "postgres|influx|redis|adminer"
# Expected: 4 lines, all "Up"

docker exec -it infra-postgres-1 psql -U ainis -d ainis -c "SELECT 1;"
# Expected: 1

docker exec infra-redis-1 redis-cli ping
# Expected: PONG

curl -s -o /dev/null -w "%{http_code}" http://localhost:8086/ping
# Expected: 204
```

### Backend

```bash
curl -s http://localhost:8000/health | python3 -m json.tool
# Expected: all services "up"

curl -s http://localhost:8000/metrics/summary | python3 -m json.tool
# Expected: {"total_packets":..., "status":"ok"}

curl -s http://localhost:8000/alerts | python3 -m json.tool
# Expected: {"alerts":[], "total":0}  or real data

wscat -c ws://localhost:8000/ws/metrics
# Expected: connects, {"type":"ping"} appears, stays open
```

### Packet capture

```bash
docker exec -it infra-redis-1 redis-cli SUBSCRIBE packets
# Run ping -c 10 8.8.8.8 — JSON packets must appear

python infra/check_influx.py
# After 1 min of Scapy: total_packets non-zero
```

### Frontend — open http://localhost:5173

- [ ] Page loads, no blank screen
- [ ] No red errors in DevTools Console
- [ ] PacketCounter increments while ping runs
- [ ] ProtocolBreakdown pie shows slices
- [ ] MetricsPanel line chart rising
- [ ] Sidebar navigation works

### 5-minute stability test

```bash
ping -c 1000 8.8.8.8
# leave all terminals open for 5 minutes
# at the end:
python infra/check_influx.py
# packet count must be 500+

curl -s http://localhost:8000/health | python3 -m json.tool
# all services still "up"
```

---

## 6. Environment Variable Reference

### backend/.env

```
POSTGRES_URL=postgresql+asyncpg://ainis:ainis@localhost:5432/ainis
INFLUX_URL=http://localhost:8086
INFLUX_TOKEN=ainis-super-secret-auth-token
INFLUX_ORG=ainis
INFLUX_BUCKET=metrics
REDIS_HOST=localhost
REDIS_PORT=6379
API_KEY=dev-api-key-change-in-prod
```

In Docker Compose use service names instead of localhost:

```
POSTGRES_URL=postgresql+asyncpg://ainis:ainis@postgres:5432/ainis
INFLUX_URL=http://influxdb:8086
REDIS_HOST=redis
```

### frontend/.env

```
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws/metrics
```

### Scapy environment overrides (optional)

```bash
API_URL=http://localhost:8000       # FastAPI URL
REDIS_HOST=localhost                # Redis host
REDIS_PORT=6379                     # Redis port
REDIS_CHANNEL=packets               # pub/sub channel
CAPTURE_INTERFACE=eth0              # specific interface (omit = all)
CAPTURE_FILTER=ip                   # BPF filter string
```

Example — target specific interface:

```bash
CAPTURE_INTERFACE=eth0 sudo python backend/capture/scapy_agent.py
```
