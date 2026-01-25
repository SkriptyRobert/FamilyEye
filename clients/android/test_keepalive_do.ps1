# Testovaci skript pro KeepAlive a FamilyEyeService v Device Owner modu
# Pouziti: .\test_keepalive_do.ps1

Write-Host "=== Test KeepAlive a FamilyEyeService v Device Owner modu ===" -ForegroundColor Cyan
Write-Host ""

# 1. Overeni Device Owner statusu
Write-Host "[1/6] Kontroluji Device Owner status..." -ForegroundColor Yellow
$adbPath = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"
if (!(Test-Path $adbPath)) {
    Write-Host "  VAROVANI: adb.exe nebyl nalezen na standardni ceste!" -ForegroundColor Red
    $adbPath = "adb" # Fallback to path
}

$doCheck = & $adbPath shell dumpsys device_policy
if ($doCheck -match "com.familyeye.agent") {
    Write-Host "  OK: Device Owner je aktivni" -ForegroundColor Green
}
else {
    Write-Host "  VAROVANI: Device Owner neni aktivni!" -ForegroundColor Red
    Write-Host "  Spustte: adb shell dpm set-device-owner com.familyeye.agent/.receiver.FamilyEyeDeviceAdmin" -ForegroundColor Yellow
    exit 1
}

# 2. Overeni ze service bezi
Write-Host ""
Write-Host "[2/6] Kontroluji FamilyEyeService..." -ForegroundColor Yellow
$serviceCheck = & $adbPath shell "dumpsys activity services | grep -A 5 FamilyEyeService"
if ($serviceCheck -match "FamilyEyeService") {
    Write-Host "  OK: FamilyEyeService bezi" -ForegroundColor Green
}
else {
    Write-Host "  VAROVANI: FamilyEyeService nebezi!" -ForegroundColor Red
}

# 3. Overeni Accessibility Service
Write-Host ""
Write-Host "[3/6] Kontroluji AppDetectorService (Accessibility)..." -ForegroundColor Yellow
$accCheck = & $adbPath shell "dumpsys accessibility | grep -A 3 AppDetectorService"
if ($accCheck -match "AppDetectorService") {
    Write-Host "  OK: Accessibility Service je aktivni" -ForegroundColor Green
}
else {
    Write-Host "  VAROVANI: Accessibility Service neni aktivni!" -ForegroundColor Red
}

# 4. Spusteni logcat monitoring (v pozadi)
Write-Host ""
Write-Host "[4/6] Spoustim logcat monitoring..." -ForegroundColor Yellow
Write-Host "  Filtruji: FamilyEyeService, KeepAliveActivity, RestartReceiver, ProcessGuardianWorker" -ForegroundColor Gray
$logcatJob = Start-Job -ScriptBlock {
    param($adb)
    & $adb logcat -c
    & $adb logcat | Select-String -Pattern "FamilyEyeService|KeepAliveActivity|RestartReceiver|ProcessGuardianWorker|DeviceOwner"
} -ArgumentList $adbPath

# 5. Test 1: Zabiti procesu pomoci am kill
Write-Host ""
Write-Host "[5/6] TEST 1: Zabijam proces pomoci 'am kill'..." -ForegroundColor Cyan
Write-Host "  Cekam 2 sekundy..." -ForegroundColor Gray
Start-Sleep -Seconds 2

$packageName = "com.familyeye.agent"
& $adbPath shell am kill $packageName
Write-Host "  Proces zabit. Cekam 3 sekundy na obnovu..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# Overeni obnovy
$serviceCheck2 = & $adbPath shell "dumpsys activity services | grep -A 5 FamilyEyeService"
if ($serviceCheck2 -match "FamilyEyeService") {
    Write-Host "  OK: Service se obnovil!" -ForegroundColor Green
}
else {
    Write-Host "  CHYBA: Service se neobnovil!" -ForegroundColor Red
}

# 6. Test 2: Simulace "Clear All" (onTaskRemoved)
Write-Host ""
Write-Host "[6/6] TEST 2: Simulace 'Clear All' (onTaskRemoved)..." -ForegroundColor Cyan
Write-Host "  Cekam 2 sekundy..." -ForegroundColor Gray
Start-Sleep -Seconds 2

# Simulace swipe away z recent apps
& $adbPath shell am start -a android.intent.action.MAIN -c android.intent.category.HOME
Start-Sleep -Seconds 1
& $adbPath shell input keyevent KEYCODE_APP_SWITCH
Start-Sleep -Seconds 1
& $adbPath shell input swipe 500 1000 500 100  # Swipe up to clear (může se lišit podle zařízení)

Write-Host "  'Clear All' simulovano. Cekam 3 sekundy na obnovu..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# Overeni obnovy
$serviceCheck3 = & $adbPath shell "dumpsys activity services | grep -A 5 FamilyEyeService"
if ($serviceCheck3 -match "FamilyEyeService") {
    Write-Host "  OK: Service se obnovil po Clear All!" -ForegroundColor Green
}
else {
    Write-Host "  VAROVANI: Service se mozna neobnovil (cekame na AlarmManager/WorkManager)..." -ForegroundColor Yellow
    Write-Host "  ProcessGuardianWorker kontroluje kazdych 15 minut" -ForegroundColor Gray
}

# 7. Zobrazeni logcat (poslednich 50 radku)
Write-Host ""
Write-Host "=== Logcat (posledni relevantni zaznamy) ===" -ForegroundColor Cyan
Stop-Job $logcatJob
Remove-Job $logcatJob
& $adbPath logcat -d | Select-String -Pattern "FamilyEyeService|KeepAliveActivity|RestartReceiver|ProcessGuardianWorker|DeviceOwner" | Select-Object -Last 50

Write-Host ""
Write-Host "=== Test dokoncen ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Pro kontinuální monitoring logcat spustte:" -ForegroundColor Yellow
Write-Host "  adb logcat | Select-String -Pattern 'FamilyEyeService|KeepAliveActivity|RestartReceiver|ProcessGuardianWorker'" -ForegroundColor White
