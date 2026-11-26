# QUANTUM TRADER V1 - Verification Script
# Run this in PowerShell to verify the backend setup

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "QUANTUM TRADER V1 - Setup Verification" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan

# Navigate to project directory
$projectRoot = "N:\Trading\CIS_v3.0\QUANTUM_TRADER_V1"
Set-Location $projectRoot

Write-Host "`nProject root: $projectRoot" -ForegroundColor Yellow
Write-Host "Current directory: $(Get-Location)" -ForegroundColor Yellow

# Check if Python is available
Write-Host "`n=== Checking Python ===" -ForegroundColor Cyan
python --version
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python not found!" -ForegroundColor Red
    exit 1
}

# Check if virtual environment exists
Write-Host "`n=== Checking Virtual Environment ===" -ForegroundColor Cyan
if (Test-Path "runtime\venv") {
    Write-Host "✓ Virtual environment exists" -ForegroundColor Green
} else {
    Write-Host "⚠ Virtual environment not found, will create..." -ForegroundColor Yellow
}

# Install/verify dependencies
Write-Host "`n=== Installing Dependencies ===" -ForegroundColor Cyan
& "runtime\venv\Scripts\pip.exe" install --upgrade pip
& "runtime\venv\Scripts\pip.exe" install --only-binary :all: -r src\backend\requirements.txt

if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING: Install with --only-binary failed, trying without..." -ForegroundColor Yellow
    & "runtime\venv\Scripts\pip.exe" install -r src\backend\requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to install dependencies!" -ForegroundColor Red
        exit 1
    }
}

# Initialize database
Write-Host "`n=== Initializing Database ===" -ForegroundColor Cyan
& "runtime\venv\Scripts\python.exe" src\backend\database\init_db.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Database initialization failed!" -ForegroundColor Red
    exit 1
}

# Run verification script
Write-Host "`n=== Running Verification Tests ===" -ForegroundColor Cyan
& "runtime\venv\Scripts\python.exe" verify_setup.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Verification tests failed!" -ForegroundColor Red
    exit 1
}

Write-Host "`n✅ ALL CHECKS PASSED!" -ForegroundColor Green
Write-Host "You can now start the application with: .\START_QUANTUM_TRADER.bat" -ForegroundColor Green