# Starts the ApplyFlow API on http://localhost:8000
# Run from anywhere - it resolves paths relative to this script.

$ErrorActionPreference = "Stop"
$backend = Join-Path $PSScriptRoot "backend"
$python = Join-Path $backend ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Host "Virtualenv missing at $python" -ForegroundColor Red
    Write-Host "Create it with:  python -m venv backend\.venv" -ForegroundColor Yellow
    Write-Host "Then:            backend\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt"
    exit 1
}

$inUse = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($inUse) {
    Write-Host "Port 8000 is already in use by PID $($inUse.OwningProcess)." -ForegroundColor Yellow
    Write-Host "Stop it with:  Stop-Process -Id $($inUse.OwningProcess)"
    exit 1
}

Write-Host "ApplyFlow API  ->  http://localhost:8000" -ForegroundColor Cyan
Write-Host "API docs       ->  http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "Ctrl+C to stop.`n" -ForegroundColor DarkGray

Set-Location $backend
& $python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
