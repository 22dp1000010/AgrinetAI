# Starts both AgriNet state nodes + the frontend dev server in separate windows.
# Prereqs (one-time):
#   cd backend; python -m venv .venv; .venv\Scripts\pip install -r requirements.txt
#   cd frontend; npm install
#   cp .env.example .env   (add GEMINI_API_KEY or keep DEMO_MODE=1)

$root = $PSScriptRoot
$py = Join-Path $root "backend\.venv\Scripts\python.exe"

if (-not (Test-Path $py)) {
    Write-Error "venv not found — run: cd backend; python -m venv .venv; .venv\Scripts\pip install -r requirements.txt"
    exit 1
}

Write-Host "Starting Telangana node on :8001 ..."
Start-Process pwsh -ArgumentList "-NoExit", "-Command",
    "`$env:STATE_ID='TS'; `$env:PORT='8001'; `$env:PEERS='http://localhost:8002'; Set-Location '$root\backend'; & '$py' -m uvicorn app.main:app --port 8001"

Write-Host "Starting Odisha node on :8002 ..."
Start-Process pwsh -ArgumentList "-NoExit", "-Command",
    "`$env:STATE_ID='OD'; `$env:PORT='8002'; `$env:PEERS='http://localhost:8001'; Set-Location '$root\backend'; & '$py' -m uvicorn app.main:app --port 8002"

Write-Host "Starting frontend dev server on :5173 ..."
Start-Process pwsh -ArgumentList "-NoExit", "-Command",
    "Set-Location '$root\frontend'; npm run dev"

Write-Host ""
Write-Host "AgriNet local stack starting:"
Write-Host "  Frontend:        http://localhost:5173"
Write-Host "  Telangana node:  http://localhost:8001/docs"
Write-Host "  Odisha node:     http://localhost:8002/docs"
Write-Host ""
Write-Host "Seed demo data (after nodes are up):"
Write-Host "  backend\.venv\Scripts\python backend\scripts\seed_demo_data.py"
