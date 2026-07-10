$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$ConsoleDir = Join-Path $Root "web\console"

if (-not (Test-Path (Join-Path $ConsoleDir "node_modules"))) {
    Push-Location $ConsoleDir
    try {
        npm install
    } finally {
        Pop-Location
    }
}

Push-Location $ConsoleDir
try {
    npm run dev
} finally {
    Pop-Location
}
