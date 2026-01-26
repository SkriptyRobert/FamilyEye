# Windows Agent dokumentace

## Přehled

Agent běží na Windows zařízení a monitoruje použití, vynucuje pravidla a odesílá statistiky na backend.

## Struktura

```
clients/windows/agent/
├── main.py              # Hlavní agent, orchestrace
├── config.py            # Konfigurace
├── monitor/             # Monitorování aplikací
│   ├── core.py
│   ├── process_tracking.py
│   └── ...
├── enforcer/            # Vynucování pravidel
│   ├── core.py
│   ├── app_blocking.py
│   └── ...
├── reporter.py          # Odesílání statistik
├── network_control.py   # Kontrola sítě
├── notifications.py     # Windows notifikace
├── boot_protection.py   # Ochrana při startu
└── logger.py            # Logging
```

## Instalace

### Manuální

```bash
cd clients/windows
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m agent.main
```

### Párování

Párování se provádí přes frontend dashboard nebo přímo přes API endpoint `/api/devices/pairing/pair`.

Pro manuální párování použijte:
- Frontend: Otevřete dashboard a použijte QR kód nebo manuální token
- API: POST request na `/api/devices/pairing/pair` s pairing tokenem, device_name, device_type, mac_address a device_id

Párování vytvoří zařízení v databázi a vrátí `device_id` a `api_key`, které se uloží do `config.json`.

## Konfigurace

**Soubor**: `clients/windows/config.json`

**Struktura**:
```json
{
  "backend_url": "https://192.168.1.100:8000",
  "device_id": "uuid-device-id",
  "api_key": "uuid-api-key",
  "polling_interval": 30,
  "reporting_interval": 300,
  "ssl_verify": false
}
```

**Proměnné prostředí**:
- `BACKEND_URL` - URL backendu
- `DEVICE_ID` - ID zařízení
- `API_KEY` - API klíč
- `AGENT_POLLING_INTERVAL` - Interval kontroly (sekundy)
- `AGENT_REPORTING_INTERVAL` - Interval reportování (sekundy)
- `AGENT_SSL_VERIFY` - Ověřování SSL certifikátů

## Moduly

### Main (`main.py`)

**Třída**: `ParentalControlAgent`

**Funkce**:
- Orchestrace všech modulů
- Spuštění/zastavení agenta
- Validace přihlašovacích údajů
- Thread management

**Thready**:
- `monitor_thread` - Monitorování aplikací
- `enforcer_thread` - Vynucování pravidel
- `reporter_thread` - Odesílání statistik

**Lifecycle**:
1. `start()` - Validace, spuštění threadů
2. `run()` - Hlavní smyčka
3. `stop()` - Zastavení všech threadů

### Monitor (`monitor/`)

**Hlavní modul**: `monitor/core.py`

**Třída**: `AppMonitor`

**Funkce**:
- Detekce spuštěných aplikací
- Sledování aktivních oken
- Měření času použití
- Konsolidace helper procesů

**Strategie detekce**:
1. **Viditelná okna** - Procesy s viditelnými okny
2. **CLI nástroje** - Cmd, PowerShell, Python, atd.
3. **Filtrování** - Ignorování systémových procesů
4. **Konsolidace** - Helper procesy → hlavní aplikace

**Ignorované procesy**:
- Systémové procesy (svchost, winlogon, atd.)
- Background služby
- Systémové UI (explorer, taskmgr, atd.)

**Helper mapping**:
- `steamwebhelper` → `steam`
- `discordptb` → `discord`
- `chrome_crashpad` → `chrome`
- atd.

### Enforcer (`enforcer/`)

**Hlavní modul**: `enforcer/core.py`

**Třída**: `RuleEnforcer`

**Funkce**:
- Načítání pravidel z backendu
- Vynucování blokování aplikací
- Kontrola časových limitů
- Kontrola denních limitů
- Kontrola časových oken
- Zamknutí zařízení
- Blokování sítě

**Typy pravidel**:
- `app_block` - Okamžité ukončení aplikace
- `time_limit` - Kontrola denního limitu pro aplikaci
- `daily_limit` - Kontrola celkového denního limitu
- `schedule` - Kontrola časového okna
- `lock_device` - Zamknutí zařízení
- `network_block` - Blokování internetu

**Vynucování**:
- **Blokování aplikací**: `taskkill` nebo `psutil.kill()`
- **Časové limity**: Kontrola použití vs. limit
- **Denní limit**: Kontrola celkového použití
- **Zamknutí**: `LockWorkStation()` nebo `WTSDisconnectSession()`
- **Blokování sítě**: Windows Firewall rules

**Notifikace**:
- Varování při 70% limitu
- Upozornění při překročení limitu
- Upozornění při blokování aplikace

### Reporter (`reporter.py`)

**Třída**: `UsageReporter`

**Funkce**:
- Shromažďování statistik z monitoru
- Odesílání reportů na backend
- Resetování denních statistik
- Error handling a retry

**Reportování**:
- Interval: 60 sekund (konfigurovatelné)
- Formát: JSON s usage_logs
- Endpoint: `POST /api/reports/agent/report`

**Data**:
- `app_name` - Název aplikace
- `duration` - Délka použití (sekundy)
- `timestamp` - Časová značka

### Network Control (`network_control.py`)

**Třída**: `NetworkController`

**Funkce**:
- Blokování webových stránek (hosts file)
- Blokování všech odchozích připojení
- Whitelist pro backend komunikaci
- Detekce VPN/proxy

**Metody**:
- `block_website()` - Blokování domény
- `unblock_website()` - Odblokování domény
- `block_all_outbound()` - Blokování všeho kromě whitelistu
- `unblock_all_outbound()` - Odstranění blokování
- `detect_vpn()` - Detekce VPN
- `detect_proxy()` - Detekce proxy

### Notifications (`notifications.py`)

**Třída**: `NotificationManager`

**Funkce**:
- Windows toast notifikace
- Popup okna
- Zvukové upozornění (případně)

**Typy notifikací**:
- `show_limit_warning()` - Varování před limitem
- `show_limit_exceeded()` - Limit překročen
- `show_daily_limit_warning()` - Varování denního limitu
- `show_daily_limit_exceeded()` - Denní limit překročen
- `show_app_blocked()` - Aplikace zablokována
- `show_outside_schedule()` - Mimo časové okno

### Boot Protection (`boot_protection.py`)

**Třída**: `BootProtection`

**Funkce**:
- Ochrana před odinstalací
- Automatické spuštění při bootu
- Kontrola integrity agenta

**Metody**:
- `start()` - Spuštění monitoru
- `stop()` - Zastavení monitoru
- `check_integrity()` - Kontrola integrity

## Lifecycle

### Start

1. Načtení konfigurace
2. Validace přihlašovacích údajů
3. Spuštění threadů:
   - Monitor (každých 5s)
   - Enforcer (každých 2s)
   - Reporter (každých 60s)
4. Spuštění boot protection

### Běh

- **Monitor**: Sleduje aplikace, aktualizuje statistiky
- **Enforcer**: Kontroluje pravidla, vynucuje akce
- **Reporter**: Odesílá statistiky na backend

### Stop

1. Zastavení všech threadů
2. Odeslání finálního reportu (případně)
3. Zastavení boot protection

## Komunikace s backendem

### Fetch Rules

**Endpoint**: `POST /api/rules/agent/fetch`

**Request**:
```json
{
  "device_id": "uuid",
  "api_key": "uuid"
}
```

**Response**:
```json
{
  "rules": [...],
  "daily_usage": 3600,
  "usage_by_app": {
    "chrome": 1800,
    "steam": 1800
  }
}
```

### Report Usage

**Endpoint**: `POST /api/reports/agent/report`

**Request**:
```json
{
  "device_id": "uuid",
  "api_key": "uuid",
  "usage_logs": [
    {
      "app_name": "chrome",
      "duration": 60,
      "timestamp": "2024-01-01T12:00:00Z"
    }
  ],
  "running_processes": ["chrome", "steam"]
}
```

### Critical Event

**Endpoint**: `POST /api/reports/agent/critical-event`

**Request**:
```json
{
  "device_id": "uuid",
  "api_key": "uuid",
  "event_type": "limit_exceeded",
  "app_name": "steam",
  "used_seconds": 3600,
  "limit_seconds": 1800
}
```

## Error handling

### Network errors

- Retry s exponenciálním backoffem
- Offline režim (pravidla fungují i bez sítě)
- Logování chyb

### Authentication errors

- 401 → Zastavení agenta
- Požadavek na re-párování

### Process errors

- Ignorování přístupových chyb
- Logování chyb
- Pokračování v běhu

## Logging

**Soubor**: `agent.log`

**Úrovně**:
- INFO - Obecné informace
- WARNING - Varování
- ERROR - Chyby
- DEBUG - Ladění (pouze v dev módu)

**Formát**: Strukturované logy s kontextem

## Rozšíření

### Přidání nového typu pravidla

1. Přidat logiku do `enforcer/core.py`
2. Přidat do `_update_blocked_apps()` v `enforcer/app_blocking.py`
3. Přidat do `update()` smyčky v `enforcer/core.py`
4. Aktualizovat backend API

### Přidání nové detekce

1. Přidat do `monitor/core.py` nebo `monitor/process_tracking.py`
2. Aktualizovat `update()` metodu
3. Přidat do helper mapping (pokud potřeba)

### Přidání nové notifikace

1. Přidat metodu do `notifications.py`
2. Zavolat z `enforcer.py`
3. Přidat styling (případně)

## Produkční nasazení

Viz [DEPLOYMENT.md](./DEPLOYMENT.md) pro detailní návod na instalaci jako Windows služby.

---

# Android Agent dokumentace

## Přehled

Android agent běží na Android zařízeních a poskytuje nejvyšší úroveň ochrany pomocí Device Owner módu. Monitoruje použití, vynucuje pravidla, odesílá statistiky a poskytuje Smart Shield detekci škodlivého obsahu.

## Struktura

```
clients/android/app/src/main/java/com/familyeye/agent/
├── service/
│   ├── FamilyEyeService.kt          # Hlavní foreground služba
│   ├── AppDetectorService.kt        # Accessibility Service pro detekci aplikací
│   ├── EnforcementService.kt       # Centralizované vynucování pravidel
│   ├── RuleEnforcer.kt              # Logika vynucování pravidel
│   ├── UsageTracker.kt              # Sledování použití aplikací
│   ├── Reporter.kt                  # Odesílání statistik
│   ├── WatchdogService.kt           # Watchdog v separátním procesu
│   ├── ResurrectionJobService.kt   # JobScheduler persistence
│   ├── ProcessGuardianWorker.kt    # WorkManager persistence
│   ├── AlarmWatchdog.kt             # AlarmManager heartbeat
│   └── BlockOverlayManager.kt      # UI overlay pro blokování
├── scanner/
│   ├── ContentScanner.kt           # Smart Shield skenování obsahu
│   ├── KeywordDetector.kt          # Aho-Corasick detekce klíčových slov
│   └── KeywordManager.kt           # Správa klíčových slov
├── device/
│   ├── DeviceOwnerPolicyEnforcer.kt # Device Owner ochrana
│   └── DeviceRestrictions.kt        # Restrikce a konstanty
├── enforcement/
│   ├── Blocker.kt                   # Blokování aplikací
│   ├── SelfProtectionHandler.kt     # Anti-tampering detekce
│   └── WhitelistManager.kt          # Whitelist systémových aplikací
├── receiver/
│   ├── BootReceiver.kt             # Boot receiver
│   ├── RestartReceiver.kt            # Restart receiver
│   └── FamilyEyeDeviceAdmin.kt       # Device Admin receiver
├── data/
│   ├── api/
│   │   ├── FamilyEyeApi.kt          # REST API klient
│   │   └── WebSocketClient.kt       # WebSocket klient
│   ├── local/
│   │   ├── AgentDatabase.kt         # Room databáze
│   │   ├── RuleDao.kt               # Pravidla DAO
│   │   └── UsageLogDao.kt           # Usage logs DAO
│   └── repository/
│       ├── AgentConfigRepository.kt  # Konfigurace
│       ├── RuleRepository.kt        # Pravidla repository
│       └── UsageRepository.kt       # Usage repository
└── ui/
    ├── MainActivity.kt               # Hlavní aktivita
    ├── KeepAliveActivity.kt          # Keep-alive aktivita
    └── screens/
        ├── PairingScreen.kt          # Párování
        ├── SetupWizardScreen.kt     # Setup wizard
        └── ChildDashboardScreen.kt  # Dětský dashboard
```

## Instalace

### Požadavky

- Android 7.0+ (pro Direct Boot)
- Device Owner oprávnění (nastaveno přes WebADB nebo ADB)
- Accessibility Service oprávnění
- Notification oprávnění

### Párování

1. **Otevřete dashboard** na počítači
2. **Vytvořte pairing token** v sekci Devices
3. **Spusťte aplikaci** na Android zařízení
4. **Zadejte pairing token** nebo naskenujte QR kód
5. **Aplikace se automaticky spáruje** a stáhne konfiguraci

### Device Owner nastavení

Device Owner musí být nastaven **před prvním spuštěním aplikace** nebo po factory resetu.

**Metoda 1: WebADB (doporučeno)**
1. Otevřete dashboard
2. Přejděte na Device Owner Setup
3. Připojte zařízení přes USB
4. Klikněte na "Set Device Owner"
5. Postupujte podle instrukcí

**Metoda 2: ADB**
```bash
adb shell dpm set-device-owner com.familyeye.agent/.receiver.FamilyEyeDeviceAdmin
```

## Konfigurace

**Soubor**: Lokální Room databáze (`AgentDatabase`)

**Struktura**:
- `backend_url` - URL backendu
- `device_id` - UUID zařízení
- `api_key` - API klíč pro autentizaci
- `paired` - Stav párování

**Proměnné prostředí**: Nejsou podporovány (používá lokální databázi)

## Moduly

### FamilyEyeService (`service/FamilyEyeService.kt`)

**Třída**: `FamilyEyeService : Service`

**Funkce**:
- Foreground service (běží na popředí)
- Orchestrace všech modulů
- Spuštění persistence vrstev
- Device Owner restrikce
- Screen state monitoring

**Lifecycle**:
1. `onCreate()` - Inicializace všech modulů
2. `onStartCommand()` - Spuštění služby
3. `onDestroy()` - Zastavení služby

**Persistence vrstvy**:
- WatchdogService (separate process)
- ResurrectionJobService (JobScheduler)
- ProcessGuardianWorker (WorkManager)
- AlarmWatchdog (AlarmManager)
- KeepAliveActivity (Activity-based)

### AppDetectorService (`service/AppDetectorService.kt`)

**Třída**: `AppDetectorService : AccessibilityService`

**Funkce**:
- Detekce změn foreground aplikace
- Smart Shield detekce obsahu
- Screenshot capture při detekci
- Spouštění blokování aplikací

**Event handling**:
- `onAccessibilityEvent()` - Zpracování accessibility eventů
- `handleSmartShieldDetection()` - Zpracování Smart Shield detekce
- `handleAppChange()` - Zpracování změny aplikace

### EnforcementService (`enforcement/EnforcementService.kt`)

**Třída**: `EnforcementService`

**Funkce**:
- Centralizované vynucování pravidel
- Priorita vynucování:
  1. Self-protection (tampering)
  2. Device Lock (nejvyšší priorita)
  3. Whitelist check
  4. App blocking rules
  5. Device schedules
  6. App schedules
  7. Device daily limit
  8. App time limits

**Metody**:
- `evaluateEnforcement()` - Vyhodnocení, zda aplikace má být blokována
- `shouldBlockApp()` - Kontrola blokování

### RuleEnforcer (`service/RuleEnforcer.kt`)

**Třída**: `RuleEnforcer`

**Funkce**:
- Načítání pravidel z backendu
- Kontrola časových limitů
- Kontrola denních limitů
- Kontrola časových oken
- Kontrola blokování aplikací

**Typy pravidel**:
- `app_block` - Blokování aplikace
- `time_limit` - Časový limit pro aplikaci
- `daily_limit` - Denní limit pro celé zařízení
- `schedule` - Časové okno
- `lock_device` - Zamknutí zařízení
- `network_block` - Blokování sítě

### ContentScanner (`scanner/ContentScanner.kt`)

**Třída**: `ContentScanner`

**Funkce**:
- Skenování obsahu aplikací pomocí Accessibility API
- Extrakce textu z UI elementů
- Detekce klíčových slov pomocí Aho-Corasick algoritmu
- Rate limiting (2 sekundy mezi skenováním)

**Metody**:
- `processScreen()` - Zpracování aktuální obrazovky
- `extractText()` - Extrakce textu z UI (DFS traversal)
- `normalize()` - Normalizace textu (odstranění diakritiky)

### KeywordDetector (`scanner/KeywordDetector.kt`)

**Třída**: `KeywordDetector`

**Funkce**:
- Aho-Corasick algoritmus pro efektivní detekci více klíčových slov
- Trie struktura s failure links
- Case-insensitive matching
- Normalizace textu

**Metody**:
- `findAny()` - Najde první shodu v textu
- `findAll()` - Najde všechny shody v textu

### DeviceOwnerPolicyEnforcer (`device/DeviceOwnerPolicyEnforcer.kt`)

**Třída**: `DeviceOwnerPolicyEnforcer`

**Funkce**:
- Device Owner ochrana
- Blokování odinstalace
- Aplikace baseline restrikcí
- Ochrana Settings aplikací
- Kiosk mode

**Metody**:
- `setUninstallBlocked()` - Blokování odinstalace
- `applyBaselineRestrictions()` - Aplikace restrikcí
- `applySettingsProtection()` - Ochrana Settings
- `deactivateAllProtections()` - Deaktivace ochrany

### Reporter (`service/Reporter.kt`)

**Třída**: `Reporter`

**Funkce**:
- Shromažďování statistik z UsageTracker
- Odesílání reportů na backend
- WebSocket komunikace
- Error handling a retry

**Reportování**:
- Interval: 60 sekund (konfigurovatelné)
- Formát: JSON s usage_logs
- Endpoint: `POST /api/reports/agent/report`

## Lifecycle

### Start

1. BootReceiver zachytí `ACTION_BOOT_COMPLETED` nebo `ACTION_LOCKED_BOOT_COMPLETED`
2. FamilyEyeService.start() se spustí
3. onCreate() inicializuje všechny moduly:
   - Device Owner restrikce
   - WatchdogService
   - ResurrectionJobService
   - ProcessGuardianWorker
   - AlarmWatchdog
   - Monitoring tasks
4. Foreground notification se zobrazí

### Běh

- **AppDetectorService**: Sleduje změny aplikací
- **ContentScanner**: Skenuje obsah pro Smart Shield
- **EnforcementService**: Kontroluje a vynucuje pravidla
- **UsageTracker**: Sleduje použití aplikací
- **Reporter**: Odesílá statistiky na backend

### Stop

1. Zastavení všech modulů
2. Zastavení persistence vrstev
3. Odeslání finálního reportu (případně)

## Komunikace s backendem

### Fetch Rules

**Endpoint**: `POST /api/rules/agent/fetch`

**Request**:
```json
{
  "device_id": "uuid",
  "api_key": "uuid"
}
```

**Response**:
```json
{
  "rules": [...],
  "daily_usage": 3600,
  "usage_by_app": {
    "com.chrome.browser": 1800,
    "com.steam": 1800
  }
}
```

### Report Usage

**Endpoint**: `POST /api/reports/agent/report`

**Request**:
```json
{
  "device_id": "uuid",
  "api_key": "uuid",
  "usage_logs": [
    {
      "app_name": "com.chrome.browser",
      "duration": 60,
      "timestamp": "2024-01-01T12:00:00Z"
    }
  ],
  "running_processes": ["com.chrome.browser", "com.steam"]
}
```

### Smart Shield Alert

**Endpoint**: `POST /api/shield/alert`

**Request**:
```json
{
  "device_id": "uuid",
  "api_key": "uuid",
  "keyword_id": 1,
  "keyword": "drogy",
  "category": "drugs",
  "severity": "high",
  "package_name": "com.chrome.browser",
  "screenshot_url": "https://.../screenshot.jpg",
  "context_text": "Kde koupit drogy..."
}
```

### Fetch Keywords

**Endpoint**: `POST /api/shield/agent/keywords`

**Request**:
```json
{
  "device_id": "uuid",
  "api_key": "uuid"
}
```

**Response**:
```json
[
  {
    "id": 1,
    "keyword": "drogy",
    "category": "drugs",
    "severity": "high",
    "enabled": true
  }
]
```

## Device Owner ochrana

### Proč nelze odinstalovat

Device Owner aplikace může blokovat svou vlastní odinstalaci pomocí:
```kotlin
dpm.setUninstallBlocked(admin, context.packageName, true)
```

**Co se stane při pokusu o odinstalaci:**
1. Uživatel se pokusí odinstalovat aplikaci
2. Android systém zkontroluje `isUninstallBlocked()`
3. Pokud je `true`, zobrazí chybu: "Tuto aplikaci nelze odinstalovat"
4. Odinstalace je zablokována na systémové úrovni

### Baseline Restrictions

Výchozí restrikce aplikované při aktivaci Device Owner:
- `DISALLOW_SAFE_BOOT` - Safe Boot
- `DISALLOW_FACTORY_RESET` - Factory Reset
- `DISALLOW_INSTALL_APPS` - Instalace aplikací
- `DISALLOW_UNINSTALL_APPS` - Odinstalace aplikací
- `DISALLOW_CONFIG_DATE_TIME` - Datum/čas
- A další...

Viz [architecture/security-model.md](./architecture/security-model.md) pro detailní popis.

## Imunitní systém (5 vrstev persistence)

### 1. WatchdogService
- Separate process (`:watchdog`)
- Kontroluje každých 5 sekund
- Pokud hlavní služba neběží, spustí ji

### 2. ResurrectionJobService
- JobScheduler (systémová služba)
- Naplánováno každých 15 minut
- Přežije app kill

### 3. ProcessGuardianWorker
- WorkManager (systémová služba)
- Backup recovery mechanismus
- Naplánováno každých 30 minut

### 4. AlarmWatchdog
- AlarmManager heartbeat
- Každou minutu kontroluje stav
- Spustí RestartReceiver pokud služba neběží

### 5. KeepAliveActivity
- Activity-based restart
- Poslední záchrana
- Spustí se z RestartReceiver

Viz [architecture/security-model.md](./architecture/security-model.md) pro detailní popis.

## Smart Shield

### Jak funguje

1. **ContentScanner** skenuje obsah aplikací pomocí Accessibility API
2. **KeywordDetector** používá Aho-Corasick algoritmus pro detekci klíčových slov
3. Při detekci se pořídí screenshot
4. Alert se odešle na backend
5. Rodič obdrží real-time notifikaci

### Kategorie klíčových slov

- `self-harm` - Sebevražda (critical)
- `drugs` - Drogy (high, medium)
- `bullying` - Šikana (high, medium)
- `adult` - Dospělý obsah (high, medium)
- `custom` - Vlastní (high, medium, low)

Viz [reference/feature-matrix.md](./reference/feature-matrix.md) pro detailní popis.

## Error handling

### Network errors
- Retry s exponenciálním backoffem
- Offline režim (pravidla fungují i bez sítě)
- Lokální cache pravidel

### Authentication errors
- 401 → Zastavení agenta
- Požadavek na re-párování

### Process errors
- Ignorování přístupových chyb
- Logování chyb
- Pokračování v běhu

## Logging

**Knihovna**: Timber

**Úrovně**:
- `Timber.d()` - Debug
- `Timber.i()` - Info
- `Timber.w()` - Warning
- `Timber.e()` - Error

**Formát**: Strukturované logy s kontextem

## Rozšíření

### Přidání nového typu pravidla

1. Přidat logiku do `EnforcementService.kt`
2. Přidat do `RuleEnforcer.kt`
3. Aktualizovat backend API
4. Aktualizovat frontend UI

### Přidání nové kategorie Smart Shield

1. Přidat do `backend/app/config/smart_shield_defaults.json`
2. Aktualizovat `KeywordManager.kt`
3. Aktualizovat frontend UI

## Produkční nasazení

Viz [DEPLOYMENT.md](./DEPLOYMENT.md) pro detailní návod na instalaci jako Android aplikace.

