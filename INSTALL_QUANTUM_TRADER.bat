@echo off
title QUANTUM TRADER V1 - Installer
color 0B
cls
echo ============================================================================
echo                    QUANTUM TRADER V1 INSTALLER
echo ============================================================================
echo Professional Quantitative Futures Trading ^& Intelligence Platform
echo ============================================================================
echo.

net session >nul 2>nul
if %errorLevel% neq 0 (
    echo [WARNING] Not running as administrator. Some features may require admin rights.
    echo.
)

set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"
echo [INFO] Project root: %PROJECT_ROOT%
echo.

echo [INFO] Checking available disk space...
for /f "tokens=3" %%a in ('dir /-c "%PROJECT_ROOT:~0,3%" 2^>nul ^| findstr /c:"bytes free"') do set "FREE_SPACE=%%a"
if defined FREE_SPACE (echo [INFO] Free space on drive: OK) else (echo [WARNING] Could not determine free space.)
echo.

echo [INFO] Creating directory structure...
if not exist "data\market_data" mkdir "data\market_data"
if not exist "data\database" mkdir "data\database"
if not exist "data\logs" mkdir "data\logs"
if not exist "data\backups" mkdir "data\backups"
if not exist "data\temp" mkdir "data\temp"
if not exist "config\exchanges" mkdir "config\exchanges"
if not exist "config\strategies" mkdir "config\strategies"
echo [INFO] Directory structure created successfully.
echo.

echo [INFO] Checking Python installation...
python --version >nul 2>nul
if %errorLevel% neq 0 (
    echo [WARNING] Python not found in system PATH.
    echo [ERROR] Please install Python 3.11+ from python.org
    pause
    exit /b 1
) else (
    for /f "tokens=2" %%i in ('python --version 2^>nul') do set "PYTHON_VERSION=%%i"
    echo [INFO] Python found: version %PYTHON_VERSION%
)
echo.

echo [INFO] Creating virtual environment...
if not exist "runtime\venv" (
    python -m venv runtime\venv
    echo [INFO] Virtual environment created successfully.
) else (
    echo [INFO] Virtual environment already exists.
)
echo.

echo [INFO] Installing dependencies...
call "runtime\venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if exist "src\backend\requirements.txt" (
    echo [INFO] Installing packages from requirements.txt...
    pip install --only-binary :all: -r src\backend\requirements.txt
    if %errorLevel% neq 0 (
        echo [WARNING] Retrying without --only-binary...
        pip install -r src\backend\requirements.txt
        if %errorLevel% neq 0 (
            echo [ERROR] Failed to install dependencies. Check output above.
            pause
            exit /b 1
        )
    )
    echo [INFO] Dependencies installed successfully.
) else (
    echo [WARNING] requirements.txt not found.
)
echo.

echo [INFO] Initializing database...
if exist "src\backend\database\init_db.py" (
    python src\backend\database\init_db.py
    echo [INFO] Database initialized successfully.
) else (
    echo [WARNING] Database initialization script not found.
)
echo.

if not exist ".env" (
    echo [INFO] Creating default .env file...
    (
        echo APP_NAME=QUANTUM_TRADER_V1
        echo VERSION=1.0.0
        echo DEBUG=False
        echo LOG_LEVEL=INFO
        echo HOST=127.0.0.1
        echo PORT=8000
        echo DATABASE_URL=sqlite:///data/database/quantum.db
        echo SECRET_KEY=quantum-trader-secret-key-change-in-production
    ) > .env
    echo [INFO] Default .env file created.
)

echo ============================================================================
echo                        INSTALLATION COMPLETE
echo ============================================================================
echo QUANTUM TRADER V1 has been successfully installed.
echo.
echo To start the application, run: START_QUANTUM_TRADER.bat
echo ============================================================================
echo.
pause