@echo off
REM ============================================
REM  DEV: Pair Device (interactive)
REM ============================================
setlocal EnableDelayedExpansion

echo.
echo    ╔══════════════════════════════════════╗
echo    ║   DEV: Parovani zarizeni             ║
echo    ╚══════════════════════════════════════╝
echo.

set "SCRIPT_DIR=%~dp0"
set "ROOT_DIR=%SCRIPT_DIR%.."
set "AGENT_DIR=%ROOT_DIR%\clients\windows"
cd /d "%AGENT_DIR%"

REM Check venv
if not exist "venv\Scripts\python.exe" (
    echo [*] Vytvarim agent venv...
    python -m venv venv
    venv\Scripts\pip install -r requirements.txt
)

echo [*] Spoustim parovani...
echo.
venv\Scripts\python.exe pair_device.py

echo.
pause
