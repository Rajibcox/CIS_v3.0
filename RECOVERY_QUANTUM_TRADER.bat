@echo off
:: ============================================================================
:: QUANTUM TRADER V1 - Recovery Script
:: ============================================================================

title QUANTUM TRADER V1 - Recovery
color 0C
cls

echo ============================================================================
echo                    QUANTUM TRADER V1 RECOVERY
echo ============================================================================
echo Professional Quantitative Futures Trading & Intelligence Platform
echo ============================================================================
echo.

echo [WARNING] This script will restore the database from the latest backup.
echo [WARNING] Current database will be overwritten.
set /p confirm="Are you sure? (y/n): "
if /i "%confirm%" neq "y" (
    echo [INFO] Recovery cancelled.
    pause
    exit /b 0
)

set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

echo [INFO] Searching for latest backup...
for /f "delims=" %%f in ('dir /b /o-d "data\backups\quantum_*.db"') do (
    set "LATEST_BACKUP=data\backups\%%f"
    goto :found
)

echo [ERROR] No backups found in data\backups\.
pause
exit /b 1

:found
echo [INFO] Found latest backup: %LATEST_BACKUP%
echo [INFO] Restoring database...
copy "%LATEST_BACKUP%" "data\database\quantum.db" >nul
echo [OK] Database restored successfully.

echo.
echo ============================================================================
echo                        RECOVERY COMPLETE
echo ============================================================================
echo.
pause