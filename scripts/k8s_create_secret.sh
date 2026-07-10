#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${1:-$ROOT/.env}"

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing $ENV_FILE — copy from .env.example first."
  exit 1
fi

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

kubectl create namespace aiinfra --dry-run=client -o yaml | kubectl apply -f -

kubectl -n aiinfra create secret generic aiinfra-secret \
  --from-literal=MODEL_API_KEY="${MODEL_API_KEY:-}" \
  --from-literal=MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:-root}" \
  --from-literal=MYSQL_PASSWORD="${MYSQL_PASSWORD:-aiinfra}" \
  --from-literal=REDIS_PASSWORD="${REDIS_PASSWORD:-}" \
  --from-literal=MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-minioadmin}" \
  --from-literal=ADMIN_TOKEN="${ADMIN_TOKEN:-change-me-admin-token}" \
  --from-literal=GRAFANA_ADMIN_PASSWORD="${GRAFANA_ADMIN_PASSWORD:-admin}" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "Secret aiinfra-secret applied."
