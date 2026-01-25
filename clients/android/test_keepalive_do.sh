#!/bin/bash
# Testovaci skript pro KeepAlive a FamilyEyeService v Device Owner modu
# Pouziti: ./test_keepalive_do.sh

echo "=== Test KeepAlive a FamilyEyeService v Device Owner modu ==="
echo ""

# 1. Overeni Device Owner statusu
echo "[1/6] Kontroluji Device Owner status..."
DO_CHECK=$(adb shell dpm list-owners)
if echo "$DO_CHECK" | grep -q "com.familyeye.agent"; then
    echo "  OK: Device Owner je aktivni"
else
    echo "  VAROVANI: Device Owner neni aktivni!"
    echo "  Spustte: adb shell dpm set-device-owner com.familyeye.agent/.receiver.FamilyEyeDeviceAdmin"
    exit 1
fi

# 2. Overeni ze service bezi
echo ""
echo "[2/6] Kontroluji FamilyEyeService..."
SERVICE_CHECK=$(adb shell "dumpsys activity services | grep -A 5 FamilyEyeService")
if echo "$SERVICE_CHECK" | grep -q "FamilyEyeService"; then
    echo "  OK: FamilyEyeService bezi"
else
    echo "  VAROVANI: FamilyEyeService nebezi!"
fi

# 3. Overeni Accessibility Service
echo ""
echo "[3/6] Kontroluji AppDetectorService (Accessibility)..."
ACC_CHECK=$(adb shell "dumpsys accessibility | grep -A 3 AppDetectorService")
if echo "$ACC_CHECK" | grep -q "AppDetectorService"; then
    echo "  OK: Accessibility Service je aktivni"
else
    echo "  VAROVANI: Accessibility Service neni aktivni!"
fi

# 4. Spusteni logcat monitoring (v pozadi)
echo ""
echo "[4/6] Spoustim logcat monitoring..."
echo "  Filtruji: FamilyEyeService, KeepAliveActivity, RestartReceiver, ProcessGuardianWorker"
adb logcat -c
adb logcat | grep -E "FamilyEyeService|KeepAliveActivity|RestartReceiver|ProcessGuardianWorker|DeviceOwner" &
LOGCAT_PID=$!

# 5. Test 1: Zabiti procesu pomoci am kill
echo ""
echo "[5/6] TEST 1: Zabijam proces pomoci 'am kill'..."
echo "  Cekam 2 sekundy..."
sleep 2

PACKAGE_NAME="com.familyeye.agent"
adb shell am kill "$PACKAGE_NAME"
echo "  Proces zabit. Cekam 3 sekundy na obnovu..."
sleep 3

# Overeni obnovy
SERVICE_CHECK2=$(adb shell "dumpsys activity services | grep -A 5 FamilyEyeService")
if echo "$SERVICE_CHECK2" | grep -q "FamilyEyeService"; then
    echo "  OK: Service se obnovil!"
else
    echo "  CHYBA: Service se neobnovil!"
fi

# 6. Test 2: Simulace "Clear All" (onTaskRemoved)
echo ""
echo "[6/6] TEST 2: Simulace 'Clear All' (onTaskRemoved)..."
echo "  Cekam 2 sekundy..."
sleep 2

# Simulace swipe away z recent apps
adb shell am start -a android.intent.action.MAIN -c android.intent.category.HOME
sleep 1
adb shell input keyevent KEYCODE_APP_SWITCH
sleep 1
adb shell input swipe 500 1000 500 100  # Swipe up to clear

echo "  'Clear All' simulovano. Cekam 3 sekundy na obnovu..."
sleep 3

# Overeni obnovy
SERVICE_CHECK3=$(adb shell "dumpsys activity services | grep -A 5 FamilyEyeService")
if echo "$SERVICE_CHECK3" | grep -q "FamilyEyeService"; then
    echo "  OK: Service se obnovil po Clear All!"
else
    echo "  VAROVANI: Service se mozna neobnovil (cekame na AlarmManager/WorkManager)..."
    echo "  ProcessGuardianWorker kontroluje kazdych 15 minut"
fi

# 7. Zobrazeni logcat (poslednich 50 radku)
echo ""
echo "=== Logcat (posledni relevantni zaznamy) ==="
kill $LOGCAT_PID 2>/dev/null
adb logcat -d | grep -E "FamilyEyeService|KeepAliveActivity|RestartReceiver|ProcessGuardianWorker|DeviceOwner" | tail -50

echo ""
echo "=== Test dokoncen ==="
echo ""
echo "Pro kontinuální monitoring logcat spustte:"
echo "  adb logcat | grep -E 'FamilyEyeService|KeepAliveActivity|RestartReceiver|ProcessGuardianWorker'"
