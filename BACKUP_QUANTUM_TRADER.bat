@echo off
:: ============================================================================
:: QUANTUM TRADER V1 - Backup Script
:: ============================================================================

title QUANTUM TRADER V1 - Backup
color 0B
cls

echo ============================================================================
echo                    QUANTUM TRADER V1 BACKUP
echo ============================================================================
echo Professional Quantitative Futures Trading & Intelligence Platform
echo ============================================================================
echo.

set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c%%a%%b)
for /f "tokens=1-2 delims=: " %%a in ('time /t') do (set mytime=%%a%%b)
set "TIMESTAMP=%mydate%_%mytime%"

echo [INFO] Creating backup with timestamp: %TIMESTAMP%

if not exist "data\backups" mkdir "data\backups"

echo [INFO] Backing up database and configuration...
if exist "data\database\quantum.db" (
    copy "data\database\quantum.db" "data\backups\quantum_%TIMESTAMP%.db" >nul
    echo [OK] Database backed up successfully.
) else (
    echo [WARNING] SQLite database not found.
)

if exist ".env" (
    copy ".env" "data\backups\env_%TIMESTAMP%.bak" >nul
    echo [OK] Environment config backed up successfully.
)

echo.
echo ============================================================================
echo                        BACKUP COMPLETE
echo ============================================================================
echo Backup saved to data\backups\
echo ============================================================================
echo.
pause