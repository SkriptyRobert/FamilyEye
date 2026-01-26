# Přehled testů v projektu FamilyEye

## Backend testy (Python/Pytest)

### `test_pairing.py` - Testování párování zařízení
- **`test_generate_pairing_token_with_db_session`**: Ověřuje generování pairing tokenu s reálnou databází
  - Kontroluje, že token má správného parent_id
  - Ověřuje, že token není použitý
  - Kontroluje expiraci tokenu
  - Ověřuje uložení do databáze
- **`test_generate_pairing_token`**: Test generování tokenu s mock databází
- **`test_create_device_from_pairing_success`**: Test úspěšného vytvoření zařízení z pairing tokenu
  - Ověřuje správné vytvoření zařízení
  - Kontroluje, že token je označen jako použitý
  - Ověřuje uložení do databáze

### `test_validation.py` - Validace API požadavků
- **`test_api_malformed_json`**: Test chybného JSON v požadavku (očekává 422)
- **`test_api_missing_required_fields`**: Test chybějících povinných polí (api_key, device_id)
- **`test_api_invalid_data_types`**: Test neplatných datových typů (např. duration jako string)

### `test_app_filter.py` - Filtrování aplikací
- **`test_is_trackable`**: Test, které aplikace jsou sledovatelné
  - Systémové procesy (idle, svchost, dwm) = False
  - Běžné aplikace (chrome, msedge, Minecraft) = True
- **`test_get_friendly_name`**: Test mapování názvů aplikací
  - msedge → "Microsoft Edge"
  - Neznámé aplikace vrací původní název
- **`test_get_category`**: Test kategorizace aplikací
  - Browsers (chrome, msedge) → "browsers"
  - Games (minecraft) → "games"
- **`test_get_icon_type`**: Test typů ikon pro aplikace

### `test_rules_endpoint.py` - API endpoint pro pravidla
- **`test_agent_fetch_rules_success`**: Test úspěšného načtení pravidel pro agenta
  - Ověřuje správnou strukturu odpovědi (rules, daily_usage, usage_by_app)
  - Kontroluje, že pravidla jsou vrácena
- **`test_agent_fetch_rules_invalid_api_key`**: Test neplatného API klíče (očekává 401)
- **`test_agent_fetch_rules_calculates_daily_usage`**: Test výpočtu denního použití
  - Ověřuje správný výpočet z více usage logů

### `test_usage_calculation.py` - Výpočty použití
- **`test_interval_merging`**: Test slučování překrývajících se časových intervalů
  - Ověřuje, že překrývající se intervaly se správně sloučí
  - Testuje přesný výpočet celkového času
- **`test_interval_merging_complete_overlap`**: Test úplného překrytí intervalů

### `test_stats_service.py` - Statistiky
- **`test_calculate_day_usage_minutes`**: Test výpočtu unikátních minut použití
  - Ověřuje, že se počítají unikátní minuty, ne celkový počet logů
- **`test_get_app_day_duration`**: Test součtu trvání aplikace za den
  - Ověřuje správný součet více logů pro stejnou aplikaci
- **`test_get_activity_boundaries`**: Test hranic aktivity (první a poslední čas)
  - Ověřuje správné vrácení prvního a posledního času aktivity

---

## Android testy (Kotlin/JUnit/MockK/Robolectric)

### `UsageTrackerTest.kt` - Sledování použití zařízení
- **`test lastCheckTime reset on large gap prevents phantom usage`**: Test resetu času při velkém časovém rozdílu (>60s)
  - Zabraňuje "phantom usage" po restartu aplikace
- **`test lastCheckTime preserved on small gap`**: Test zachování času při malém rozdílu (<60s)
- **`test tracking skips own package`**: Test, že vlastní balíček není sledován
- **`test screen off prevents tracking`**: Test, že při vypnuté obrazovce se nesleduje
- **`test overlay active prevents tracking`**: Test, že při aktivním overlay se nesleduje
- **`test time jump backwards resets lastCheckTime`**: Test resetu při skoku času zpět
- **`test getUsageToday combines local and remote`**: Test kombinace lokálního a vzdáleného použití
  - Vrací maximum z lokálního a vzdáleného
- **`test getTotalUsageToday combines local and remote`**: Test kombinace celkového použití

### `EnforcementServiceTest.kt` - Vynucování pravidel
- **`testOwnPackageIsWhitelisted`**: Test, že vlastní balíček je vždy whitelistován
- **`testTamperingAttemptIsDetected`**: Test detekce pokusu o manipulaci
- **`testDeviceLockBlocksAllApps`**: Test, že device lock blokuje všechny aplikace
- **`testWhitelistedAppIsAllowed`**: Test, že whitelistované aplikace jsou povoleny
- **`testBlockedAppIsBlocked`**: Test, že blokované aplikace jsou blokovány
- **`testDeviceScheduleBlocksApp`**: Test, že device schedule blokuje aplikace
- **`testAllowedAppReturnsAllow`**: Test, že povolené aplikace vrací Allow

### `PackageMatcherTest.kt` - Porovnávání balíčků
- **`testExactPackageMatch`**: Test přesné shody balíčku (case-insensitive)
- **`testPartialPackageMatch`**: Test částečné shody (substring)
- **`testAppLabelMatchWithAccents`**: Test shody s diakritikou (normalizace)
- **`testIsLauncher`**: Test detekce launcherů
- **`testNormalizationHelper`**: Test normalizační funkce

### `KeywordDetectorTest.kt` - Detekce klíčových slov
- **`testBasicDetection`**: Test základní detekce klíčových slov
- **`testCzechAccentsAndCase`**: Test detekce s českou diakritikou a velkými/malými písmeny
- **`testOverlappingKeywords`**: Test překrývajících se klíčových slov
- **`testEmptyInputs`**: Test prázdných vstupů

### `PolicyEnforcerTest.kt` - Vynucování Device Owner politik
- **`testApplyBaselineRestrictionsHandlesSecurityException`**: Test zpracování SecurityException při aplikaci restrikcí
- **`testSetUninstallBlockedHandlesException`**: Test zpracování výjimek při blokování odinstalace

### `BootReceiverTest.kt` - Spouštění po bootu
- **`testRebootStartsService`**: Test spuštění služby po rebootu
- **`testDirectBootStartsService`**: Test spuštění služby při Direct Boot
- **`testUserPresentStartsService`**: Test spuštění služby při přítomnosti uživatele

### `RestartReceiverTest.kt` - Restart služby
- **`testRestartActionStartsService`**: Test spuštění služby při restart akci
- **`testDebounceMechanism`**: Test debounce mechanismu (zabraňuje opakovaným restartům)

---

## Frontend testy (React/Vitest)

### `DeviceOwnerSetup.test.jsx` - Setup Device Owner
- **`renders initial preparation step`**: Test zobrazení počátečního kroku
- **`navigates through steps`**: Test navigace mezi kroky
- **`shows error if no device is selected`**: Test zobrazení chyby při nevybraném zařízení

---

## Shrnutí

**Backend**: 6 test souborů, ~15 testů
- Párování zařízení
- Validace API
- Filtrování aplikací
- Pravidla a endpointy
- Výpočty použití
- Statistiky

**Android**: 7 test souborů, ~31 testů
- Sledování použití (8 testů)
- Vynucování pravidel (7 testů)
- Porovnávání balíčků (5 testů)
- Detekce klíčových slov (4 testy)
- Device Owner politiky (2 testy)
- Boot a restart receivery (5 testů)

**Frontend**: 1 test soubor, 3 testy
- Device Owner Setup komponenta

**Celkem**: ~49 testů pokrývajících klíčové funkce systému
