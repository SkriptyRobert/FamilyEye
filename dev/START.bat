@echo off
REM ============================================
REM  DEV: Quick Start Server (HTTPS port 8000)
REM ============================================
setlocal EnableDelayedExpansion

echo.
echo    ╔══════════════════════════════════════╗
echo    ║   DEV: Parental Control Server       ║
echo    ║   🔒 HTTPS Enabled                   ║
echo    ╚══════════════════════════════════════╝
echo.

set "SCRIPT_DIR=%~dp0"
set "ROOT_DIR=%SCRIPT_DIR%.."
cd /d "%ROOT_DIR%"

REM Stop existing
echo [*] Zastavuji existujici procesy na portu 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
)

REM Check venv
if not exist "backend\venv\Scripts\python.exe" (
    echo [*] Vytvarim backend venv...
    cd backend
    python -m venv venv
    venv\Scripts\pip install -r requirements.txt
    venv\Scripts\pip install cryptography qrcode pillow
    cd ..
)

REM Check frontend build
if not exist "frontend\dist\index.html" (
    echo [*] Building frontend...
    cd frontend
    call npm install
    call npm run build
    cd ..
)

REM Start HTTPS server
echo [*] Spoustim HTTPS server...
cd backend
start "ParentalControl-Server" /MIN cmd /c "venv\Scripts\python.exe run_https.py"
cd ..

timeout /t 3 /nobreak >nul

REM Get local IP (skip Docker/WSL IPs like 172.x.x.x)
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    set "LOCAL_IP=%%a"
    set "LOCAL_IP=!LOCAL_IP: =!"
    REM Skip Docker/WSL IPs (172.16-31.x.x) and prefer 192.168.x.x or 10.x.x.x
    echo !LOCAL_IP! | findstr /r "^172\.[0-9][0-9]\." >nul
    if errorlevel 1 (
        REM Not a Docker/WSL IP, use it
        goto :found_ip
    )
)
REM Fallback: try to find 192.168.x.x or 10.x.x.x
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    set "LOCAL_IP=%%a"
    set "LOCAL_IP=!LOCAL_IP: =!"
    echo !LOCAL_IP! | findstr /r "^192\.168\." >nul
    if not errorlevel 1 goto :found_ip
    echo !LOCAL_IP! | findstr /r "^10\." >nul
    if not errorlevel 1 goto :found_ip
)
REM If still not found, use first non-172 IP
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    set "LOCAL_IP=%%a"
    set "LOCAL_IP=!LOCAL_IP: =!"
    echo !LOCAL_IP! | findstr /r "^172\." >nul
    if errorlevel 1 goto :found_ip
)
REM Last resort: use localhost
set "LOCAL_IP=127.0.0.1"
:found_ip

echo.
echo    ════════════════════════════════════════
echo    Dashboard: https://localhost:8000
echo    Network:   https://%LOCAL_IP%:8000
echo    API Docs:  https://localhost:8000/docs
echo    ════════════════════════════════════════
echo.
echo    📱 QR kod pro mobil: https://%LOCAL_IP%:8000/api/trust/qr.png
echo.
echo    Pro zastaveni: dev\STOP.bat
echo.
start https://%LOCAL_IP%:8000
