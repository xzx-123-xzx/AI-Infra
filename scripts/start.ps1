$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$EnvFile = Join-Path $Root ".env"
$EnvExample = Join-Path $Root ".env.example"

if (-not (Test-Path $EnvFile)) {
    Copy-Item $EnvExample $EnvFile
    Write-Host "Created $EnvFile — please set MODEL_API_KEY before calling models."
}

$LogsDir = Join-Path $Root "logs"
$DataDir = Join-Path $Root "data"
if (-not (Test-Path $LogsDir)) { New-Item -ItemType Directory -Path $LogsDir | Out-Null }
if (-not (Test-Path $DataDir)) { New-Item -ItemType Directory -Path $DataDir | Out-Null }

Push-Location (Join-Path $Root "deploy\docker-compose")
try {
    docker compose up -d --build
    Write-Host "Gateway:   http://localhost:8080/health"
    Write-Host "RAG:       http://localhost:8081/health"
    Write-Host "Inference: http://localhost:8082/health"
    Write-Host "Agent:     http://localhost:8083/health"
    Write-Host "Console:   http://localhost:3000"
    Write-Host "Docs:    http://localhost:8080/docs (gateway) | http://localhost:8081/docs (rag)"
    Write-Host "Logs:    $LogsDir\app.log"
} finally {
    Pop-Location
}
