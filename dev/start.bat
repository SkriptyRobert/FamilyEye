@echo off
setlocal enabledelayedexpansion

:: Prejdi do korenoveho adresare projektu
cd /d "%~dp0"
cd ..

:: Detekce IP adresy (robustni verze)
set LOCAL_IP=127.0.0.1
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4 Address" /c:"IP Address"') do (
    set "temp_ip=%%a"
    set "temp_ip=!temp_ip: =!"
    if "!temp_ip:~0,7!"=="192.168" set LOCAL_IP=!temp_ip!
    if "!temp_ip:~0,3!"=="10." set LOCAL_IP=!temp_ip!
    if "!temp_ip:~0,7!"=="172.16." set LOCAL_IP=!temp_ip!
)

:: Cisteni portu
echo [*] Cisteni portu 8000 a 5173...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5173 ^| findstr LISTENING') do taskkill /f /pid %%a >nul 2>&1

:: Detekce Pythonu ve venv
set "PYTHON_PATH=python"
if exist "backend\venv\Scripts\python.exe" (
    set "PYTHON_PATH=backend\venv\Scripts\python.exe"
)

echo.
echo    ┌──────────────────────────────────────┐
echo    │   FamilyEye: Full Dev Environment    │
echo    │   Detected IP: %LOCAL_IP%           │
echo    └──────────────────────────────────────┘
echo.

:: Spust BACKEND (na pozadi)
echo [*] Spoustim Backend...
start "FamilyEye Backend" /b cmd /c "cd backend && ..\!PYTHON_PATH! run_https.py"

:: Spust FRONTEND (na pozadi)
echo [*] Spoustim Frontend...
start "FamilyEye Frontend" /b cmd /c "cd frontend && npm run dev -- --host %LOCAL_IP% --port 5173"

echo.
echo    ------------------------------------------
echo    HOTOVO: Vse bezi v tomto okne.
echo    ------------------------------------------
echo    📍 Dashboard UI: http://%LOCAL_IP%:5173
echo    📍 Backend API:  https://localhost:8000
echo    ------------------------------------------
echo.

:: Nechame okno otevrene pro logy (stisknuti klavesy neukonci procesy, ty se musi pres dev\STOP.bat)
echo Sleduji logy (Ctrl+C pro ukonceni zobrazeni, procesy ukonci dev\STOP.bat)...
pause > nul

endlocal
