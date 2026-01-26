# Testing - Testovací strategie

Kompletní přehled testovací strategie Smart Shield projektu. Tento dokument integruje obsah z `TESTS_OVERVIEW.md` a rozšiřuje ho o detailní technické informace.

## Strategie testování

### Unit testy (Backend)

**Framework**: pytest

**Lokalizace**: `backend/tests/`

**Přístup**: Testování služeb izolovaně s mock databází

**Spuštění**:
```bash
cd backend
pytest tests/
```

### Unit testy (Android)

**Framework**: JUnit + MockK + Robolectric

**Lokalizace**: `clients/android/app/src/test/`

**Přístup**: 
- MockK pro mockování závislostí
- Robolectric pro Context a Android framework

**Spuštění**:
```bash
cd clients/android
./gradlew test
```

### Instrumented testy

**Framework**: Android Test Framework (Espresso)

**Status**: Není v projektu, ale doporučeno pro budoucí rozšíření

**Použití**: Testování UI a integračních testů na reálném zařízení

## Kritické testy před releasem

### Backend testy

#### test_app_filter.py - Filtrování aplikací

**Testy**:
- `test_is_trackable()` - Systémové procesy vs běžné aplikace
- `test_get_friendly_name()` - Mapování názvů (msedge → Microsoft Edge)
- `test_get_category()` - Kategorizace (chrome → browsers)
- `test_get_icon_type()` - Typy ikon

**Kritičnost**: Vysoká - ovlivňuje zobrazení aplikací v UI

**Zdroj**: `backend/tests/test_app_filter.py`

#### test_pairing.py - Párování zařízení

**Testy**:
- `test_generate_pairing_token_with_db_session` - Generování tokenu s reálnou DB
- `test_generate_pairing_token` - Generování tokenu s mock DB
- `test_create_device_from_pairing_success` - Úspěšné vytvoření zařízení

**Kritičnost**: Kritická - párování je základní funkcionalita

**Zdroj**: `backend/tests/test_pairing.py`

#### test_rules_endpoint.py - API endpoint pro pravidla

**Testy**:
- `test_agent_fetch_rules_success` - Úspěšné načtení pravidel
- `test_agent_fetch_rules_invalid_api_key` - Neplatný API klíč (401)
- `test_agent_fetch_rules_calculates_daily_usage` - Výpočet denního použití

**Kritičnost**: Vysoká - pravidla jsou jádro systému

**Zdroj**: `backend/tests/test_rules_endpoint.py`

#### test_validation.py - Validace API požadavků

**Testy**:
- `test_api_malformed_json` - Chybný JSON (422)
- `test_api_missing_required_fields` - Chybějící povinná pole
- `test_api_invalid_data_types` - Neplatné datové typy

**Kritičnost**: Střední - zabraňuje chybným požadavkům

**Zdroj**: `backend/tests/test_validation.py`

#### test_usage_calculation.py - Výpočty použití

**Testy**:
- `test_interval_merging` - Slučování překrývajících se intervalů
- `test_interval_merging_complete_overlap` - Úplné překrytí intervalů

**Kritičnost**: Vysoká - ovlivňuje přesnost statistik

**Zdroj**: `backend/tests/test_usage_calculation.py`

#### test_stats_service.py - Statistiky

**Testy**:
- `test_calculate_day_usage_minutes` - Výpočet unikátních minut
- `test_get_app_day_duration` - Součet trvání aplikace za den
- `test_get_activity_boundaries` - Hranice aktivity (první/poslední čas)

**Kritičnost**: Střední - ovlivňuje dashboard data

**Zdroj**: `backend/tests/test_stats_service.py`

### Android testy

#### KeywordDetectorTest.kt - Detekce klíčových slov

**Testy**:
- `testBasicDetection` - Základní detekce klíčových slov
- `testCzechAccentsAndCase` - Diakritika a case-insensitive
- `testOverlappingKeywords` - Překrývající se klíčová slova
- `testEmptyInputs` - Prázdné vstupy

**Kritičnost**: Kritická - Smart Shield jádro

**Zdroj**: `clients/android/app/src/test/java/com/familyeye/agent/scanner/KeywordDetectorTest.kt`

#### BootReceiverTest.kt - Spouštění po bootu

**Testy**:
- `testRebootStartsService` - Spuštění služby po rebootu
- `testDirectBootStartsService` - Spuštění služby při Direct Boot
- `testUserPresentStartsService` - Spuštění služby při přítomnosti uživatele

**Kritičnost**: Kritická - zajišťuje, že služba běží po restartu

**Zdroj**: `clients/android/app/src/test/java/com/familyeye/agent/receiver/BootReceiverTest.kt`

#### UsageTrackerTest.kt - Sledování použití

**Testy**:
- `test lastCheckTime reset on large gap prevents phantom usage` - Reset při velkém časovém rozdílu
- `test lastCheckTime preserved on small gap` - Zachování času při malém rozdílu
- `test tracking skips own package` - Vlastní balíček není sledován
- `test screen off prevents tracking` - Vypnutá obrazovka blokuje tracking
- `test overlay active prevents tracking` - Aktivní overlay blokuje tracking
- `test time jump backwards resets lastCheckTime` - Reset při skoku času zpět
- `test getUsageToday combines local and remote` - Kombinace lokálního a vzdáleného použití
- `test getTotalUsageToday combines local and remote` - Kombinace celkového použití

**Kritičnost**: Vysoká - ovlivňuje přesnost statistik

**Zdroj**: `clients/android/app/src/test/java/com/familyeye/agent/tracker/UsageTrackerTest.kt`

#### EnforcementServiceTest.kt - Vynucování pravidel

**Testy**:
- `testOwnPackageIsWhitelisted` - Vlastní balíček je vždy whitelistován
- `testTamperingAttemptIsDetected` - Detekce pokusu o manipulaci
- `testDeviceLockBlocksAllApps` - Device lock blokuje všechny aplikace
- `testWhitelistedAppIsAllowed` - Whitelistované aplikace jsou povoleny
- `testBlockedAppIsBlocked` - Blokované aplikace jsou blokovány
- `testDeviceScheduleBlocksApp` - Device schedule blokuje aplikace
- `testAllowedAppReturnsAllow` - Povolené aplikace vrací Allow

**Kritičnost**: Kritická - jádro vynucování pravidel

**Zdroj**: `clients/android/app/src/test/java/com/familyeye/agent/enforcement/EnforcementServiceTest.kt`

#### PackageMatcherTest.kt - Porovnávání balíčků

**Testy**:
- `testExactPackageMatch` - Přesná shoda balíčku (case-insensitive)
- `testPartialPackageMatch` - Částečná shoda (substring)
- `testAppLabelMatchWithAccents` - Shoda s diakritikou (normalizace)
- `testIsLauncher` - Detekce launcherů
- `testNormalizationHelper` - Normalizační funkce

**Kritičnost**: Střední - ovlivňuje matching aplikací

**Zdroj**: `clients/android/app/src/test/java/com/familyeye/agent/utils/PackageMatcherTest.kt`

#### PolicyEnforcerTest.kt - Device Owner politiky

**Testy**:
- `testApplyBaselineRestrictionsHandlesSecurityException` - Zpracování SecurityException
- `testSetUninstallBlockedHandlesException` - Zpracování výjimek při blokování odinstalace

**Kritičnost**: Vysoká - Device Owner ochrana

**Zdroj**: `clients/android/app/src/test/java/com/familyeye/agent/device/PolicyEnforcerTest.kt`

#### RestartReceiverTest.kt - Restart služby

**Testy**:
- `testRestartActionStartsService` - Spuštění služby při restart akci
- `testDebounceMechanism` - Debounce mechanismus (zabraňuje opakovaným restartům)

**Kritičnost**: Střední - zajišťuje obnovení služby

**Zdroj**: `clients/android/app/src/test/java/com/familyeye/agent/receiver/RestartReceiverTest.kt`

### Frontend testy

#### DeviceOwnerSetup.test.jsx - Setup Device Owner

**Testy**:
- `renders initial preparation step` - Zobrazení počátečního kroku
- `navigates through steps` - Navigace mezi kroky
- `shows error if no device is selected` - Zobrazení chyby při nevybraném zařízení

**Kritičnost**: Střední - UI testy

**Zdroj**: `frontend/src/components/DeviceOwnerSetup.test.jsx`

## Test coverage

### Backend

**6 test souborů, ~15 testů**

- Párování zařízení
- Validace API
- Filtrování aplikací
- Pravidla a endpointy
- Výpočty použití
- Statistiky

### Android

**7 test souborů, ~31 testů**

- Sledování použití (8 testů)
- Vynucování pravidel (7 testů)
- Porovnávání balíčků (5 testů)
- Detekce klíčových slov (4 testy)
- Device Owner politiky (2 testy)
- Boot a restart receivery (5 testů)

### Frontend

**1 test soubor, 3 testy**

- Device Owner Setup komponenta

**Celkem**: ~49 testů pokrývajících klíčové funkce systému

## Před releasem checklist

- [ ] Všechny backend testy projdou (`pytest tests/`)
- [ ] Všechny Android testy projdou (`./gradlew test`)
- [ ] KeywordDetector testy projdou (kritické pro Smart Shield)
- [ ] BootReceiver testy projdou (kritické pro persistence)
- [ ] EnforcementService testy projdou (kritické pro blokování)
- [ ] Pairing testy projdou (kritické pro párování)
- [ ] App filter testy projdou (ovlivňuje UI)

## Spuštění testů

### Backend

```bash
cd backend
pytest tests/ -v
```

### Android

```bash
cd clients/android
./gradlew test
```

### Frontend

```bash
cd frontend
npm test
```

## Technické reference

- Backend testy: `backend/tests/`
- Android testy: `clients/android/app/src/test/`
- Frontend testy: `frontend/src/components/*.test.jsx`
- Test konfigurace: `backend/pytest.ini`, `frontend/vitest.config.js`
