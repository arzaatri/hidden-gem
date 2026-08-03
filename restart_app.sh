#!/bin/bash
set -e

cd "$(dirname "$0")"

docker compose down
docker compose up -d

echo "Dagster:  http://localhost:3000"
echo "Web app:  http://localhost:8000"
echo "MinIO:    http://localhost:9001"
