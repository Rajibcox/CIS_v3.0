@echo off
:: ============================================================================
:: QUANTUM TRADER V1 - Shutdown Script
:: ============================================================================

title QUANTUM TRADER V1 - Shutdown
color 0C
cls

echo ============================================================================
echo                    QUANTUM TRADER V1 SHUTDOWN
echo ============================================================================
echo Professional Quantitative Futures Trading & Intelligence Platform
echo ============================================================================
echo.

echo [INFO] Stopping QUANTUM TRADER V1 processes...

:: Kill python processes running quantum_trader
taskkill /f /im python.exe /fi "WINDOWTITLE eq QUANTUM TRADER V1 - Running*" >nul 2>&1
if %errorLevel% eq 0 (
    echo [INFO] Application stopped successfully.
) else (
    echo [INFO] No running application window found. Attempting general python cleanup...
    taskkill /f /im python.exe >nul 2>&1
    echo [INFO] Python processes terminated.
)

echo.
echo ============================================================================
echo                        SHUTDOWN COMPLETE
echo ============================================================================
echo.
pause