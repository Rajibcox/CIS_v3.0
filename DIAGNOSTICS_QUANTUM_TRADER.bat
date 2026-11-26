@echo off
:: ============================================================================
:: QUANTUM TRADER V1 - Diagnostics Script
:: ============================================================================

title QUANTUM TRADER V1 - Diagnostics
color 0E
cls

echo ============================================================================
echo                    QUANTUM TRADER V1 DIAGNOSTICS
echo ============================================================================
echo Professional Quantitative Futures Trading & Intelligence Platform
echo ============================================================================
echo.

set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

echo [1/6] Checking system environment...
echo OS Version:
ver
echo.

echo [2/6] Checking Python installation...
python --version
if %errorLevel% neq 0 (
    echo [ERROR] Python not found in PATH!
) else (
    echo [OK] Python is available.
)
echo.

echo [3/6] Checking virtual environment...
if exist "runtime\venv" (
    echo [OK] Virtual environment exists at runtime\venv.
) else (
    echo [WARNING] Virtual environment not found. Run INSTALL_QUANTUM_TRADER.bat.
)
echo.

echo [4/6] Checking database...
if exist "data\database\quantum.db" (
    echo [OK] SQLite database found.
) else if exist "data\database" (
    echo [INFO] Database directory exists.
) else (
    echo [WARNING] Database directory not found.
)
echo.

echo [5/6] Checking directory structure...
for %%d in (data\market_data data\database data\logs data\backups config src) do (
    if exist "%%d" (
        echo [OK] Directory %%d exists.
    ) else (
        echo [WARNING] Directory %%d missing.
    )
)
echo.

echo [6/6] Checking disk space...
dir /-c "%PROJECT_ROOT:~0,3%" 2>nul | findstr /c:"bytes free"
echo.

echo ============================================================================
echo                        DIAGNOSTICS COMPLETE
echo ============================================================================
echo.
pause