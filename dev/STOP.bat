@echo off
echo [*] Zastavuji FamilyEye vyvojove prostredi...

:: Zastaveni Python serveru
taskkill /f /im python.exe /t > nul 2>&1

:: Zastaveni Node procesů
taskkill /f /im node.exe /t > nul 2>&1

echo [OK] Procesy byly zastaveny.
timeout /t 3
