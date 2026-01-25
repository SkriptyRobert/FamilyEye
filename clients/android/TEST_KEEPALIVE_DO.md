# Testovací návod: KeepAlive a FamilyEyeService v Device Owner módu

## Přehled testovacích scénářů

### 1. Příprava

```bash
# Ověření Device Owner statusu
adb shell dpm list-owners
# Mělo by obsahovat: com.familyeye.agent

# Ověření, že aplikace běží
adb shell dumpsys activity services | grep -A 5 FamilyEyeService
```

---

## Testovací scénáře

### Scénář 1: Zabití procesu pomocí `am kill`

**Cíl:** Otestovat START_STICKY automatický restart

```bash
# 1. Zabít proces
adb shell am kill com.familyeye.agent

# 2. Počkat 2-3 sekundy
sleep 3

# 3. Ověřit obnovu
adb shell dumpsys activity services | grep -A 5 FamilyEyeService
```

**Očekávaný výsledek:**
- Service se automaticky restartuje do 2-3 sekund (START_STICKY)
- V logcat: `FamilyEyeService started`

---

### Scénář 2: Simulace "Clear All" (onTaskRemoved)

**Cíl:** Otestovat RestartReceiver + AlarmManager

```bash
# 1. Simulace swipe away z recent apps
adb shell am start -a android.intent.action.MAIN -c android.intent.category.HOME
adb shell input keyevent KEYCODE_APP_SWITCH
adb shell input swipe 500 1000 500 100

# 2. Počkat 1-2 sekundy
sleep 2

# 3. Ověřit obnovu
adb shell dumpsys activity services | grep -A 5 FamilyEyeService
```

**Očekávaný výsledek:**
- `onTaskRemoved()` se zavolá
- AlarmManager naplánuje RestartReceiver za 500ms
- Service se restartuje do 1 sekundy
- V logcat: `RestartReceiver triggered from: task_removed`

---

### Scénář 3: Force Stop (pokud Device Owner není aktivní)

**Cíl:** Ověřit, že Device Owner blokuje Force Stop

```bash
# 1. Pokus o Force Stop přes Settings
adb shell am force-stop com.familyeye.agent

# 2. Ověřit, že service stále běží
adb shell dumpsys activity services | grep -A 5 FamilyEyeService
```

**Očekávaný výsledek (s Device Owner):**
- Force Stop by měl být skrytý v Settings (DISALLOW_APPS_CONTROL)
- Pokud se podaří spustit, service se restartuje (START_STICKY)

---

### Scénář 4: Zabití Accessibility Service

**Cíl:** Otestovat KeepAliveActivity recovery

```bash
# 1. Zastavit Accessibility Service
adb shell settings put secure enabled_accessibility_services ""

# 2. Počkat 1 sekundu
sleep 1

# 3. Ověřit, že AppDetectorService.onUnbind() spustil KeepAliveActivity
adb shell dumpsys activity activities | grep KeepAliveActivity
```

**Očekávaný výsledek:**
- `AppDetectorService.onUnbind()` se zavolá
- KeepAliveActivity se spustí
- Service se restartuje
- V logcat: `KeepAliveActivity: Recovery triggered from 'accessibility_unbind'`

---

### Scénář 5: Restart zařízení

**Cíl:** Otestovat BootReceiver

```bash
# 1. Restart zařízení
adb reboot

# 2. Počkat na boot (obvykle 30-60 sekund)
# 3. Připojit se znovu
adb wait-for-device
adb shell

# 4. Ověřit, že service běží
dumpsys activity services | grep -A 5 FamilyEyeService
```

**Očekávaný výsledek:**
- BootReceiver zachytí `BOOT_COMPLETED`
- Service se automaticky spustí
- V logcat: `BootReceiver triggered: android.intent.action.BOOT_COMPLETED`

---

### Scénář 6: ProcessGuardianWorker (backup mechanismus)

**Cíl:** Otestovat periodickou kontrolu každých 15 minut

```bash
# 1. Zabít service a počkat
adb shell am kill com.familyeye.agent
sleep 1

# 2. Manuálně spustit WorkManager task (simulace)
# POZNÁMKA: WorkManager má minimální interval 15 minut
# Pro testování můžete zkrátit interval v AgentConstants.GUARDIAN_WORKER_INTERVAL_MIN

# 3. Monitorovat logcat
adb logcat | grep ProcessGuardianWorker
```

**Očekávaný výsledek:**
- Každých 15 minut se spustí ProcessGuardianWorker
- Pokud service neběží, spustí se `triggerRecovery()`
- V logcat: `ProcessGuardianWorker: Agent unhealthy! Triggering recovery...`

---

## Monitoring v reálném čase

### Logcat s filtrem

```bash
# Základní monitoring
adb logcat | grep -E "FamilyEyeService|KeepAliveActivity|RestartReceiver|ProcessGuardianWorker|DeviceOwner"

# Detailní monitoring s Timber tagy
adb logcat | grep -E "FamilyEye|KeepAlive|Restart|Guardian|DeviceOwner"
```

### Klíčové log zprávy k hledání

**Úspěšná obnova:**
- `FamilyEyeService started`
- `RestartReceiver triggered from: task_removed`
- `KeepAliveActivity: Recovery triggered from '...'`
- `ProcessGuardianWorker: Agent healthy`

**Problémy:**
- `FamilyEyeService destroyed` (bez následného `started`)
- `Guardian: FamilyEyeService NOT running!`
- `Failed to restart FamilyEyeService`

---

## Rychlé ověřovací příkazy

```bash
# 1. Je Device Owner aktivní?
adb shell dpm list-owners | grep familyeye

# 2. Běží FamilyEyeService?
adb shell dumpsys activity services | grep FamilyEyeService

# 3. Je Accessibility Service bound?
adb shell dumpsys accessibility | grep AppDetectorService

# 4. Je WebSocket připojen?
adb logcat -d | grep "WebSocket.*connected" | tail -1

# 5. Kdy byl service naposledy restartován?
adb logcat -d | grep "FamilyEyeService started" | tail -1
```

---

## Automatizované testování

Použijte připravené skripty:

**Windows (PowerShell):**
```powershell
.\test_keepalive_do.ps1
```

**Linux/Mac:**
```bash
chmod +x test_keepalive_do.sh
./test_keepalive_do.sh
```

---

## Troubleshooting

### Service se neobnovuje po zabití

1. **Zkontrolujte Device Owner:**
   ```bash
   adb shell dpm list-owners
   ```

2. **Zkontrolujte AlarmManager oprávnění:**
   ```bash
   adb shell dumpsys alarm | grep RestartReceiver
   ```

3. **Zkontrolujte WorkManager:**
   ```bash
   adb shell dumpsys jobscheduler | grep ProcessGuardianWorker
   ```

### KeepAliveActivity se nespouští

1. **Zkontrolujte, že je aktivita v manifestu:**
   ```bash
   adb shell dumpsys package com.familyeye.agent | grep KeepAliveActivity
   ```

2. **Zkontrolujte logcat pro chyby:**
   ```bash
   adb logcat | grep -E "KeepAlive|Exception"
   ```

---

## Očekávané chování v Device Owner módu

✅ **Mělo by fungovat:**
- Automatický restart po zabití (START_STICKY)
- RestartReceiver po "Clear All" (500ms)
- BootReceiver po restartu zařízení
- ProcessGuardianWorker každých 15 minut
- KeepAliveActivity při unbind Accessibility Service

❌ **Mělo by být blokováno:**
- Force Stop tlačítko v Settings (DISALLOW_APPS_CONTROL)
- Odinstalace aplikace (setUninstallBlocked)
- Factory Reset (DISALLOW_FACTORY_RESET)
- Safe Mode (DISALLOW_SAFE_BOOT)

---

## Poznámky

1. **WorkManager interval:** Minimální interval je 15 minut. Pro testování můžete dočasně zkrátit `AgentConstants.GUARDIAN_WORKER_INTERVAL_MIN`.

2. **AlarmManager blokování:** Některé OEM (Xiaomi, Samsung) mohou blokovat AlarmManager. V takovém případě funguje pouze WorkManager backup.

3. **START_STICKY:** Funguje i bez Device Owner, ale Device Owner poskytuje další ochranu (blokace Force Stop).

4. **Accessibility Service:** Pokud je odpojen, KeepAliveActivity se spustí automaticky, ale může trvat několik sekund.
