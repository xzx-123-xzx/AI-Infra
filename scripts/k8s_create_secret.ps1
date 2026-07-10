$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$EnvFile = Join-Path $Root ".env"

if (-not (Test-Path $EnvFile)) {
    Write-Error "Missing $EnvFile — copy from .env.example first."
}

Get-Content $EnvFile | ForEach-Object {
    if ($_ -match '^\s*([^#=]+)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
    }
}

$grafanaPwd = if ($env:GRAFANA_ADMIN_PASSWORD) { $env:GRAFANA_ADMIN_PASSWORD } else { "admin" }

kubectl create namespace aiinfra --dry-run=client -o yaml | kubectl apply -f -

kubectl -n aiinfra create secret generic aiinfra-secret `
    --from-literal=MODEL_API_KEY="$($env:MODEL_API_KEY)" `
    --from-literal=MYSQL_ROOT_PASSWORD="$($env:MYSQL_ROOT_PASSWORD)" `
    --from-literal=MYSQL_PASSWORD="$($env:MYSQL_PASSWORD)" `
    --from-literal=REDIS_PASSWORD="$($env:REDIS_PASSWORD)" `
    --from-literal=MINIO_SECRET_KEY="$($env:MINIO_SECRET_KEY)" `
    --from-literal=ADMIN_TOKEN="$($env:ADMIN_TOKEN)" `
    --from-literal=GRAFANA_ADMIN_PASSWORD="$grafanaPwd" `
    --dry-run=client -o yaml | kubectl apply -f -

Write-Host "Secret aiinfra-secret applied."
