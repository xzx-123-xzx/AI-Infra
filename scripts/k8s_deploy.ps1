$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "==> Building images..."
docker build -f services/gateway/Dockerfile -t aiinfra/gateway:latest .
docker build -f services/rag/Dockerfile -t aiinfra/rag:latest .
docker build -f web/console/Dockerfile -t aiinfra/console:latest .

if (Get-Command kind -ErrorAction SilentlyContinue) {
    Write-Host "==> Loading images into kind..."
    kind load docker-image aiinfra/gateway:latest
    kind load docker-image aiinfra/rag:latest
    kind load docker-image aiinfra/console:latest
}

Write-Host "==> Creating secret from .env..."
& "$PSScriptRoot\k8s_create_secret.ps1"

Write-Host "==> Applying manifests..."
kubectl apply -k deploy/k8s

Write-Host ""
Write-Host "Done. Access:"
Write-Host "  Console:    NodePort 30080"
Write-Host "  Grafana:    NodePort 30300"
Write-Host "  Prometheus: kubectl port-forward svc/prometheus 9090:9090 -n aiinfra"
