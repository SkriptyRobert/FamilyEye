@echo off
REM ============================================
REM  DEV: Stop All Services
REM ============================================

echo.
echo    ╔══════════════════════════════════════╗
echo    ║   DEV: Zastavuji sluzby              ║
echo    ╚══════════════════════════════════════╝
echo.

REM Kill by window title
taskkill /F /FI "WINDOWTITLE eq ParentalControl-Server" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq ParentalControl-Agent" >nul 2>&1

REM Kill by port
echo [*] Port 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
    echo     Zastaven PID %%a
)

echo [*] Port 3000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000 ^| findstr LISTENING 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
    echo     Zastaven PID %%a
)

echo.
echo    ✓ Hotovo
echo.
