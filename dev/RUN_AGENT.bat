@echo off
REM ============================================
REM  DEV: Run Agent (requires admin!)
REM ============================================
setlocal EnableDelayedExpansion

echo.
echo    ╔══════════════════════════════════════╗
echo    ║   DEV: Spoustim agenta               ║
echo    ╚══════════════════════════════════════╝
echo.

REM Check admin
net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ⚠️  POZOR: Spust jako Administrator!
    echo.
    pause
    exit /b 1
)

set "SCRIPT_DIR=%~dp0"
set "ROOT_DIR=%SCRIPT_DIR%.."
set "AGENT_DIR=%ROOT_DIR%\clients\windows"
cd /d "%AGENT_DIR%"

REM Check config
if not exist "config.json" (
    echo ❌ Config nenalezen! Nejprve spust PAIR_DEVICE.bat
    pause
    exit /b 1
)

REM Check venv
if not exist "venv\Scripts\python.exe" (
    echo [*] Vytvarim agent venv...
    python -m venv venv
    venv\Scripts\pip install -r requirements.txt
)

echo [*] Spoustim agenta (Ctrl+C pro zastaveni)...
echo.
venv\Scripts\python.exe run_agent.py

echo.
pause
