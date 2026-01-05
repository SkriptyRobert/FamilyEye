@echo off
REM ============================================
REM  DEV: Stop Agent
REM ============================================

echo.
echo    Zastavuji agenta...
echo.

taskkill /F /FI "WINDOWTITLE eq ParentalControl-Agent" >nul 2>&1

REM Kill python processes running agent
wmic process where "name='python.exe'" get processid,commandline 2>nul | findstr "run_agent" >nul
if %ERRORLEVEL% EQU 0 (
    for /f "tokens=2" %%a in ('wmic process where "commandline like '%%run_agent%%'" get processid /value ^| findstr "="') do (
        set PID=%%a
        taskkill /F /PID !PID! >nul 2>&1
    )
)

echo    ✓ Agent zastaven
echo.
