# System Design - Architektura systému

Hluboký technický popis architektury Smart Shield s Mermaid diagramy, toky dat a životním cyklem aplikace.

## Tok dat

### Hlavní tok: Android Agent -> Backend -> Frontend

```mermaid
graph LR
    A[Android Agent] -->|REST API| B[FastAPI Backend]
    B -->|SQLite| C[Database]
    B -->|WebSocket| D[React Frontend]
    A -->|WebSocket| B
    B -->|WebSocket| D
    E[Screenshot Upload] -->|HTTP POST| B
    B -->|File Storage| F[uploads/screenshots/]
```

### Detailní tok dat při detekci klíčového slova

```mermaid
sequenceDiagram
    participant AS as AccessibilityService
    participant CS as ContentScanner
    participant KD as KeywordDetector
    participant ADS as AppDetectorService
    participant BE as Backend API
    participant WS as WebSocket
    participant FE as Frontend

    AS->>CS: processScreen(rootNode, packageName)
    CS->>CS: extractText() - DFS traversal
    CS->>KD: findAny(normalizedText)
    KD-->>CS: keyword found
    CS->>ADS: handleDetection(keyword, packageName)
    ADS->>ADS: captureScreenshot()
    ADS->>BE: POST /api/shield/alert
    BE->>BE: Spam prevention check
    BE->>BE: Save alert to DB
    BE->>WS: notify_user(shield_alert)
    WS->>FE: Real-time notification
```

## Životní cyklus aplikace

### Boot sequence

```mermaid
flowchart TD
    A[Device Boot] --> B{Direct Boot?}
    B -->|Android 7.0+| C[ACTION_LOCKED_BOOT_COMPLETED]
    B -->|Standard| D[ACTION_BOOT_COMPLETED]
    C --> E[BootReceiver.onReceive]
    D --> E
    E --> F[FamilyEyeService.start]
    F --> G[FamilyEyeService.onCreate]
    G --> H[Apply Device Owner Restrictions]
    G --> I[Start WatchdogService]
    G --> J[Schedule ResurrectionJobService]
    G --> K[Schedule ProcessGuardianWorker]
    G --> L[Start AlarmWatchdog]
    G --> M[Start Monitoring Tasks]
```

### Direct Boot vysvětlení

**Co je Direct Boot?**

Direct Boot je funkce Androidu 7.0+, která umožňuje aplikacím běžet **před odemknutím zařízení PINem**. To znamená, že Smart Shield může běžet i když je telefon zamčený.

**Proč aplikace přežije restart bez PINu?**

1. **ACTION_LOCKED_BOOT_COMPLETED** se spustí před odemknutím
2. `BootReceiver` zachytí tento intent
3. `FamilyEyeService.start()` se spustí v "direct boot" módu
4. Služba běží v šifrovaném úložišti, ale má přístup k Device Owner API

**Technický detail:**
- Aplikace musí mít `android:directBootAware="true"` v AndroidManifest.xml
- Data jsou uložena v `DeviceEncryptedStorage` (dostupné před odemknutím)
- Po odemknutí PINem se přepne na `CredentialEncryptedStorage`

**Zdroj**: `clients/android/app/src/main/AndroidManifest.xml`

### Service Start - Všechny inicializace

Po spuštění `FamilyEyeService.onCreate()` se provede:

1. **Foreground Service Notification** - Služba běží na popředí
2. **Device Owner Restrictions** - Aplikace baseline restrikcí
3. **Watchdog Service** - Spuštění watchdogu v separátním procesu
4. **JobScheduler Resurrection** - Naplánování obnovení služby
5. **WorkManager Guardian** - Backup recovery mechanismus
6. **Monitoring Tasks** - Spuštění sledovacích úloh
7. **Screen State Receiver** - Registrace receiveru pro screen on/off
8. **Watchdog Monitoring** - Vzájemné monitorování watchdogu
9. **Alarm Heartbeat** - Plánuje se při zapnutí displeje; při zhasnutí se zruší (smart watchdog, šetrnost k baterii)

**Zdroj**: `clients/android/app/src/main/java/com/familyeye/agent/service/FamilyEyeService.kt:onCreate()`

## Android Service Survival - Imunitní systém

### Flowchart: Co se stane při crash/kill

```mermaid
flowchart TD
    A[FamilyEyeService Running] --> B{Service Killed?}
    B -->|No| A
    B -->|Yes| C[WatchdogService Detects]
    C --> D[WatchdogService.start FamilyEyeService]
    D --> E{Service Started?}
    E -->|No| F[ResurrectionJobService]
    F --> G[JobScheduler Restart]
    G --> E
    E -->|No| H[ProcessGuardianWorker]
    H --> I[WorkManager Restart]
    I --> E
    E -->|No| J[AlarmWatchdog]
    J --> K[AlarmManager Heartbeat]
    K --> L[RestartReceiver]
    L --> M[KeepAliveActivity]
    M --> N[FamilyEyeService.start]
    N --> E
    E -->|Yes| A
```

### Vrstvy persistence (5 vrstev)

1. **WatchdogService** (separate process `:watchdog`)
   - Kontroluje každých 5 sekund
   - Pokud hlavní služba není spuštěna, spustí ji
   - **Zdroj**: `clients/android/app/src/main/java/com/familyeye/agent/service/WatchdogService.kt`

2. **ResurrectionJobService** (JobScheduler)
   - Naplánováno každých 15 minut
   - Přežije app kill (JobScheduler běží na systémové úrovni)
   - **Zdroj**: `clients/android/app/src/main/java/com/familyeye/agent/service/ResurrectionJobService.kt`

3. **ProcessGuardianWorker** (WorkManager)
   - Backup recovery mechanismus
   - Naplánováno každých 15 minut (`GUARDIAN_WORKER_INTERVAL_MIN`)
   - Přežije app kill
   - **Zdroj**: `clients/android/app/src/main/java/com/familyeye/agent/service/ProcessGuardianWorker.kt`

4. **AlarmWatchdog** (AlarmManager, smart watchdog)
   - Interval heartbeat: 2 minuty při zapnutém displeji. Heartbeat se plánuje **jen při zapnutém displeji**. Při zhasnutém displeji RestartReceiver heartbeat neplánuje; FamilyEyeService při SCREEN_OFF volá `AlarmWatchdog.cancel()`, při SCREEN_ON volá `scheduleHeartbeat()`. Cíl: snížit „Často budí systém“ a spotřebu baterie. Self-revive (JobScheduler, WorkManager, onTaskRemoved) zůstává beze změny.
   - Pokud aplikace neodpovídá, spustí `RestartReceiver`
   - **Zdroj**: `clients/android/app/src/main/java/com/familyeye/agent/service/AlarmWatchdog.kt`

5. **KeepAliveActivity** (Activity-based restart)
   - Poslední záchrana
   - Spustí se z `RestartReceiver`
   - Zajistí spuštění služby a pak se ukončí
   - **Zdroj**: `clients/android/app/src/main/java/com/familyeye/agent/ui/KeepAliveActivity.kt`

## Device Owner Provisioning - Sequence Diagram

```mermaid
sequenceDiagram
    participant PC as PC Browser
    participant WebADB as WebADB
    participant USB as USB Cable
    participant Android as Android Device
    participant ADB as ADB Daemon
    participant DPM as Device Policy Manager
    participant App as FamilyEye App

    PC->>WebADB: requestDevice()
    WebADB->>USB: WebUSB API
    USB->>Android: USB Connection
    Android-->>USB: Device Selected
    USB-->>WebADB: Device Connected
    WebADB->>ADB: Authenticate
    ADB-->>WebADB: Authenticated
    PC->>WebADB: spawn('dpm set-device-owner')
    WebADB->>ADB: Execute Command
    ADB->>DPM: set-device-owner
    DPM->>DPM: Validate (no accounts)
    DPM->>App: onProfileProvisioningComplete()
    App->>App: DeviceOwnerPolicyEnforcer.onDeviceOwnerActivated()
    App->>App: setUninstallBlocked(true)
    App->>App: applyBaselineRestrictions()
    App-->>DPM: Success
    DPM-->>ADB: Success
    ADB-->>WebADB: Output: "Success"
    WebADB-->>PC: Command Complete
```

## WebSocket komunikace

### Real-time updates

```mermaid
graph TB
    A[Android Agent] -->|WebSocket Connect| B[Backend WebSocket Server]
    B -->|Subscribe| C[Device Connection Manager]
    D[Frontend] -->|WebSocket Connect| B
    B -->|Subscribe| E[User Connection Manager]
    F[Parent Action] -->|POST /api/devices/lock| B
    B -->|Send Command| A
    G[Alert Detected] -->|POST /api/shield/alert| B
    B -->|Notify| D
```

**WebSocket endpoint**: `/ws/{device_id}`

**Příkazy odesílané na zařízení**:
- `LOCK_NOW` - Zamknutí
- `UNLOCK_NOW` - Odemknutí
- `REFRESH_RULES` - Obnovení pravidel
- `SCREENSHOT_NOW` - Pořízení screenshotu
- `DEACTIVATE_DEVICE_OWNER` - Deaktivace Device Owner
- `REACTIVATE_DEVICE_OWNER` - Reaktivace Device Owner

**Notifikace odesílané rodiči**:
- `shield_alert` - Detekce klíčového slova
- `device_status` - Změna stavu zařízení

**Zdroj**: `backend/app/api/websocket.py`

## Screenshot upload flow

```mermaid
sequenceDiagram
    participant AS as AppDetectorService
    participant SH as ScreenshotHandler
    participant BE as Backend API
    participant FS as File Storage
    participant WS as WebSocket
    participant FE as Frontend

    AS->>AS: handleSmartShieldDetection()
    AS->>SH: captureScreenshot()
    SH->>SH: Take Screenshot (MediaProjection)
    SH->>SH: Compress to JPEG
    SH->>BE: POST /api/files/upload
    BE->>FS: Save to uploads/screenshots/
    BE-->>SH: Return URL
    SH->>BE: POST /api/shield/alert (with screenshot_url)
    BE->>BE: Save alert to DB
    BE->>WS: notify_user(shield_alert)
    WS->>FE: Real-time notification
    FE->>BE: GET /api/files/screenshots/{device_id}/{filename}
    BE-->>FE: Screenshot image
```

## Technické reference

### Backend soubory

- `backend/app/main.py` - FastAPI aplikace, router registrace
- `backend/app/api/websocket.py` - WebSocket server
- `backend/app/api/shield.py` - Smart Shield endpointy
- `backend/app/api/reports/` - Report endpointy

### Android soubory

- `clients/android/app/src/main/java/com/familyeye/agent/receiver/BootReceiver.kt` - Boot receiver
- `clients/android/app/src/main/java/com/familyeye/agent/service/FamilyEyeService.kt` - Hlavní služba
- `clients/android/app/src/main/java/com/familyeye/agent/service/WatchdogService.kt` - Watchdog
- `clients/android/app/src/main/java/com/familyeye/agent/service/ResurrectionJobService.kt` - JobScheduler
- `clients/android/app/src/main/java/com/familyeye/agent/service/AlarmWatchdog.kt` - AlarmManager
- `clients/android/app/src/main/java/com/familyeye/agent/service/AppDetectorService.kt` - Accessibility Service

### Frontend soubory

- `frontend/src/services/websocket.js` - WebSocket klient
- `frontend/src/services/api.js` - REST API klient
- `frontend/src/components/DeviceOwnerSetup.jsx` - WebADB setup
