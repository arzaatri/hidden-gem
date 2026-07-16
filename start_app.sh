#!/bin/bash
set -e

cd "$(dirname "$0")"

if [ ! -f .env ]; then
    echo "Missing .env — copy .env.example and fill in IGDB credentials." >&2
    exit 1
fi

docker compose up -d

echo "Dagster:  http://localhost:3000"
echo "Web app:  http://localhost:8000"
echo "MinIO:    http://localhost:9001"
