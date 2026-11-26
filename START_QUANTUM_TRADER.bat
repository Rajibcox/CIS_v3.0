@echo off
:: ============================================================================
:: QUANTUM TRADER V1 - Startup Script
:: ============================================================================

title QUANTUM TRADER V1 - Running
color 0A
cls

echo ============================================================================
echo                    QUANTUM TRADER V1 LAUNCHER
echo ============================================================================
echo Professional Quantitative Futures Trading & Intelligence Platform
echo ============================================================================
echo.

:: Get current directory
set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

echo [INFO] Project root: %PROJECT_ROOT%
echo.

:: Check virtual environment
if not exist "runtime\venv" (
    echo [ERROR] Virtual environment not found. Please run INSTALL_QUANTUM_TRADER.bat first.
    pause
    exit /b 1
)

:: Activate virtual environment
echo [INFO] Activating virtual environment...
call "runtime\venv\Scripts\activate.bat"
echo.

:: Check database
if not exist "data\database\quantum.db" if not exist "data\database\quantum_trader" (
    echo [WARNING] Database not found. Initializing database...
    python src\backend\database\init_db.py
    echo.
)

:: Start the application
echo [INFO] Starting QUANTUM TRADER V1 backend server...
echo [INFO] Web Dashboard will be available at: http://localhost:8000
echo [INFO] Press Ctrl+C to stop the application.
echo.

python src\backend\main.py

echo.
echo [INFO] Application stopped.
pause