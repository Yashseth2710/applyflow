# Starts the ApplyFlow web app on http://localhost:3000
# Run from anywhere - it resolves paths relative to this script.

$ErrorActionPreference = "Stop"
$frontend = Join-Path $PSScriptRoot "frontend"

if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
    Write-Host "Dependencies not installed." -ForegroundColor Red
    Write-Host "Run:  npm --prefix frontend install" -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path (Join-Path $frontend ".env.local"))) {
    Write-Host "Missing frontend\.env.local - copying from the example." -ForegroundColor Yellow
    Copy-Item (Join-Path $frontend ".env.local.example") (Join-Path $frontend ".env.local")
}

$inUse = Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue
if ($inUse) {
    Write-Host "Port 3000 is already in use by PID $($inUse.OwningProcess)." -ForegroundColor Yellow
    Write-Host "Stop it with:  Stop-Process -Id $($inUse.OwningProcess)"
    exit 1
}

Write-Host "ApplyFlow web  ->  http://localhost:3000" -ForegroundColor Cyan
Write-Host "Backend must also be running (start-backend.ps1)." -ForegroundColor DarkGray
Write-Host "Ctrl+C to stop.`n" -ForegroundColor DarkGray

Set-Location $frontend
npm run dev
