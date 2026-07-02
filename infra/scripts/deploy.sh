#!/bin/bash
set -e
git pull origin main
docker compose -f infra/docker-compose.prod.yml build
cd backend && alembic upgrade head && cd ..
docker compose -f infra/docker-compose.prod.yml up -d --no-deps --build backend frontend
echo "deploy complete: $(date)"