# Run WITHOUT Docker (Windows PowerShell). Creates a venv, installs deps, runs tests, starts the API on :4000.
# If script execution is blocked:  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
python -m venv .venv
& .\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
python -m pytest
if ($LASTEXITCODE -ne 0) { throw "Tests failed" }
uvicorn app.main:app --host 0.0.0.0 --port 4000
