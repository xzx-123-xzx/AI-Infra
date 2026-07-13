#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [ ! -f "$ROOT/.env" ]; then
  cp "$ROOT/.env.example" "$ROOT/.env"
  echo "Created $ROOT/.env — please set MODEL_API_KEY before calling models."
fi

mkdir -p "$ROOT/logs" "$ROOT/data"
cd "$ROOT/deploy/docker-compose"
docker compose up -d --build
echo "Gateway:   http://localhost:${GATEWAY_PORT:-8080}/health"
echo "RAG:       http://localhost:${RAG_PORT:-8081}/health"
echo "Inference: http://localhost:${INFERENCE_PORT:-8082}/health"
echo "Agent:     http://localhost:${AGENT_PORT:-8083}/health"
echo "Console:   http://localhost:${CONSOLE_PORT:-3000}"
echo "Docs:    http://localhost:${GATEWAY_PORT:-8080}/docs (gateway) | http://localhost:${RAG_PORT:-8081}/docs (rag)"
echo "Logs:    $ROOT/logs/app.log"
