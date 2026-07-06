#!/bin/bash
set -e

docker compose -f infra/docker-compose.prod.yml up -d

sleep 5

sudo python3 backend/capture/mininet_sim.py --topo demo --hosts 4 &

sleep 3

curl -X POST http://localhost/api/routing-rules \
-H "Content-Type: application/json" \
-d '{"name":"prioritize-https","port":443,"weight":10}'

echo "demo stack live on http://localhost"