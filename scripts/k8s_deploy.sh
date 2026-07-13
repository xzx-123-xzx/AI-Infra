#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Building images..."
docker build -f services/gateway/Dockerfile -t aiinfra/gateway:latest .
docker build -f services/rag/Dockerfile -t aiinfra/rag:latest .
docker build -f services/inference/Dockerfile -t aiinfra/inference:latest .
docker build -f services/agent/Dockerfile -t aiinfra/agent:latest .
docker build -f web/console/Dockerfile -t aiinfra/console:latest .

if command -v kind >/dev/null 2>&1; then
  echo "==> Loading images into kind..."
  kind load docker-image aiinfra/gateway:latest
  kind load docker-image aiinfra/rag:latest
  kind load docker-image aiinfra/inference:latest
  kind load docker-image aiinfra/agent:latest
  kind load docker-image aiinfra/console:latest
fi

echo "==> Creating secret from .env..."
bash scripts/k8s_create_secret.sh

echo "==> Applying manifests..."
kubectl apply -k deploy/k8s

echo ""
echo "Done. Access:"
echo "  Console:  NodePort 30080 (or kubectl port-forward svc/console 3000:80 -n aiinfra)"
echo "  Grafana:  NodePort 30300 (admin / see GRAFANA_ADMIN_PASSWORD in .env)"
echo "  Prometheus: kubectl port-forward svc/prometheus 9090:9090 -n aiinfra"
