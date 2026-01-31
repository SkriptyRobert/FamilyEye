# Security Model - Bezpečnostní model

Hluboký technický popis bezpečnostního modelu Smart Shield, Device Owner ochrany a imunitního systému proti killnutí.

## Device Owner: Proč nelze odinstalovat

### Technický detail: setUninstallBlocked()

Device Owner aplikace může blokovat svou vlastní odinstalaci pomocí:

```kotlin
dpm.setUninstallBlocked(admin, context.packageName, true)
```

**Co se stane při pokusu o odinstalaci:**

1. Uživatel se pokusí odinstalovat aplikaci z Nastavení
2. Android systém zkontroluje `isUninstallBlocked()`
3. Pokud je `true`, zobrazí chybu: **"Tuto aplikaci nelze odinstalovat"**
4. Odinstalace je zablokována na systémové úrovni

**Zdroj**: `clients/android/app/src/main/java/com/familyeye/agent/device/DeviceOwnerPolicyEnforcer.kt:setUninstallBlocked()`

### Proč Device Owner nelze odinstalovat bez deaktivace

Device Owner je **nejvyšší úroveň oprávnění** v Androidu. Pouze Device Owner může:

1. **Deaktivovat sám sebe** - `clearDeviceOwnerApp()`
2. **Factory reset** - Vymaže všechna data včetně Device Owner
3. **OEM unlock + Flash** - Přeprogramování zařízení

**Bezpečnostní model:**
- Device Owner je navržen pro **enterprise MDM řešení**
- Rodič má plnou kontrolu přes webové rozhraní
- Dítě nemůže aplikaci odinstalovat ani zabít

## Imunitní systém proti killnutí (5 vrstev)

### Vrstva 1: WatchdogService (Separate Process)

**Proces**: `:watchdog` (separate process)

**Jak funguje:**
- Watchdog běží v **jiném procesu** než hlavní aplikace
- Pokud je hlavní aplikace zabita, watchdog **přežije**
- Každých 5 sekund kontroluje, zda hlavní služba běží
- Pokud neběží, spustí ji pomocí `FamilyEyeService.start()`

**Technický detail:**
```kotlin
private fun checkMainService() {
    try {
        FamilyEyeService.start(this) // Safe to call even if already running
    } catch (e: Exception) {
        Timber.e(e, "Watchdog failed to ping FamilyEyeService")
    }
}
```

**Proč to funguje:**
- Separate process = jiný PID (Process ID)
- Android killuje procesy jednotlivě
- Zabití hlavní aplikace nezabije watchdog

**Zdroj**: `clients/android/app/src/main/java/com/familyeye/agent/service/WatchdogService.kt`

### Vrstva 2: ResurrectionJobService (JobScheduler)

**Jak funguje:**
- JobScheduler běží na **systémové úrovni**
- Naplánováno každých 15 minut
- Přežije app kill (JobScheduler není součástí aplikace)
- Pokud služba neběží, JobScheduler ji spustí

**Technický detail:**
```kotlin
val jobInfo = JobInfo.Builder(JOB_ID, ComponentName(context, ResurrectionJobService::class.java))
    .setPersisted(true) // Survive reboot
    .setPeriodic(15 * 60 * 1000L) // 15 minutes
    .setRequiredNetworkType(JobInfo.NETWORK_TYPE_NONE)
    .build()
```

**Proč to funguje:**
- JobScheduler je systémová služba Androidu
- Nezávislá na aplikaci
- Přežije i agresivní battery management

**Zdroj**: `clients/android/app/src/main/java/com/familyeye/agent/service/ResurrectionJobService.kt`

### Vrstva 3: ProcessGuardianWorker (WorkManager)

**Jak funguje:**
- WorkManager je backup recovery mechanismus
- Naplánováno každých 30 minut
- Přežije app kill
- Pokud služba neběží, WorkManager ji spustí

**Technický detail:**
```kotlin
val guardianRequest = PeriodicWorkRequestBuilder<ProcessGuardianWorker>(
    AgentConstants.GUARDIAN_WORKER_INTERVAL_MIN, TimeUnit.MINUTES
).build()

WorkManager.getInstance(this).enqueueUniquePeriodicWork(
    ProcessGuardianWorker.WORK_NAME,
    ExistingPeriodicWorkPolicy.KEEP,
    guardianRequest
)
```

**Proč to funguje:**
- WorkManager je systémová služba
- Nezávislá na aplikaci
- Backup pro případ, že JobScheduler selže

**Zdroj**: `clients/android/app/src/main/java/com/familyeye/agent/service/ProcessGuardianWorker.kt`

### Vrstva 4: AlarmWatchdog (AlarmManager Heartbeat, smart watchdog)

**Jak funguje:**
- AlarmManager heartbeat se plánuje **jen při zapnutém displeji**. Při zhasnutém displeji agent nebudí systém (snížení varování „Často budí systém“ a spotřeby baterie).
- RestartReceiver po spuštění naplánuje další heartbeat **pouze pokud je displej zapnutý** (`PowerManager.isInteractive`). Při zhasnutém displeji heartbeat neplánuje.
- FamilyEyeService: při SCREEN_OFF volá `AlarmWatchdog.cancel()`, při SCREEN_ON volá `AlarmWatchdog.scheduleHeartbeat()`.
- Pokud aplikace neodpovídá, spustí `RestartReceiver`; ten spustí službu a podle stavu displeje případně naplánuje další heartbeat. Self-revive (JobScheduler, WorkManager, onTaskRemoved) zůstává beze změny.
- `RestartReceiver` spustí službu; `KeepAliveActivity` je poslední záchrana.

**Technický detail:**
- Heartbeat se plánuje v `AlarmWatchdog.scheduleHeartbeat()` (voláno z `FamilyEyeService.onScreenOn()` a z `RestartReceiver` jen když `powerManager.isInteractive == true`).
- Při zhasnutí displeje `FamilyEyeService.onScreenOff()` volá `AlarmWatchdog.cancel()`.

**Proč to funguje:**
- AlarmManager je systémová služba
- Při zapnutém displeji Doze stejně neběží; při zhasnutém nebudíme zařízení zbytečně
- Přežije app kill; obnova zůstává na JobScheduler, WorkManager a onTaskRemoved

**Zdroj**: `clients/android/app/src/main/java/com/familyeye/agent/service/AlarmWatchdog.kt`

### Vrstva 5: KeepAliveActivity (Activity-based Restart)

**Jak funguje:**
- Poslední záchrana
- Spustí se z `RestartReceiver` (AlarmManager)
- Zajistí spuštění služby
- Po spuštění služby se ukončí (neviditelná aktivita)

**Technický detail:**
```kotlin
override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    
    // 1. Ensure Service is running
    FamilyEyeService.start(this)
    
    // 2. Wait for service to stabilize
    CoroutineScope(Dispatchers.Main).launch {
        delay(1000) // Allow service to stabilize
        finish() // Close activity immediately
    }
}
```

**Proč to funguje:**
- Activity má vyšší prioritu než Service
- Android preferuje obnovení Activity před Service
- Po spuštění služby se Activity ukončí (neviditelná)

**Zdroj**: `clients/android/app/src/main/java/com/familyeye/agent/ui/KeepAliveActivity.kt`

## Baseline Restrictions

### Seznam všech restrikcí

Device Owner aplikace může aplikovat následující restrikce (definovány v `DeviceRestrictions.RESTRICTION_MAP`):

| Restrikce | Popis | Co blokuje |
|-----------|-------|------------|
| `disallow_safe_boot` | Safe Boot | Reboot do safe módu |
| `disallow_factory_reset` | Factory Reset | Obnovení továrního nastavení |
| `disallow_add_user` | Přidání uživatele | Vytvoření nového uživatele |
| `disallow_remove_user` | Odebrání uživatele | Smazání uživatele |
| `disallow_install_apps` | Instalace aplikací | Instalace nových aplikací |
| `disallow_uninstall_apps` | Odinstalace aplikací | Odinstalace aplikací |
| `disallow_apps_control` | Kontrola aplikací | Správa aplikací |
| `disallow_modify_accounts` | Úprava účtů | Přidání/odebrání účtů |
| `disallow_debugging` | Debugging | USB debugging |
| `disallow_usb_transfer` | USB přenos | Přenos souborů přes USB |
| `disallow_install_unknown_sources` | Neznámé zdroje | Instalace z neznámých zdrojů |
| `disallow_config_date_time` | Datum/čas | Změna data a času |
| `disallow_mount_physical_media` | Fyzická média | Připojení SD karet |
| `disallow_config_wifi` | WiFi | Konfigurace WiFi |
| `disallow_config_bluetooth` | Bluetooth | Konfigurace Bluetooth |
| `disallow_sms` | SMS | Odesílání SMS |
| `disallow_outgoing_calls` | Odchozí hovory | Volání |
| `disallow_share_location` | Sdílení polohy | GPS poloha |

### Baseline Preset

Výchozí restrikce aplikované při aktivaci Device Owner:

```kotlin
val BASELINE_RESTRICTIONS = listOf(
    UserManager.DISALLOW_SAFE_BOOT,
    UserManager.DISALLOW_FACTORY_RESET,
    UserManager.DISALLOW_ADD_USER,
    UserManager.DISALLOW_REMOVE_USER,
    UserManager.DISALLOW_INSTALL_APPS,
    UserManager.DISALLOW_UNINSTALL_APPS,
    UserManager.DISALLOW_APPS_CONTROL,
    UserManager.DISALLOW_MODIFY_ACCOUNTS,
    UserManager.DISALLOW_INSTALL_UNKNOWN_SOURCES,
    UserManager.DISALLOW_CONFIG_DATE_TIME,
    UserManager.DISALLOW_MOUNT_PHYSICAL_MEDIA
)
```

**Zdroj**: `clients/android/app/src/main/java/com/familyeye/agent/device/DeviceRestrictions.kt`

## Settings Protection

### Proč je to potřeba

Dítě se může pokusit:
1. Vypnout Accessibility Service (potřebný pro detekci aplikací)
2. Vypnout Device Admin (Device Owner)
3. Změnit nastavení baterie (battery optimization)
4. Vypnout notifikace

### Technické řešení: setPackagesSuspended()

Device Owner může **suspendovat** (pozastavit) Settings aplikace:

```kotlin
val settingsPackages = getInstalledSettingsPackages()
dpm.setPackagesSuspended(admin, settingsPackages.toTypedArray(), true)
```

**Co to dělá:**
- Settings aplikace jsou "pozastaveny"
- Nelze je spustit
- Dítě nemůže změnit nastavení

**Které aplikace jsou suspendovány:**
- `com.android.settings` - Hlavní Settings
- `com.miui.securitycenter` - Xiaomi Security Center
- `com.samsung.android.settings` - Samsung Settings
- Ostatní Settings-like aplikace

**Zdroj**: `clients/android/app/src/main/java/com/familyeye/agent/device/DeviceOwnerPolicyEnforcer.kt:applySettingsProtection()`

## Protection Levels

### GOD_MODE (Android 11+)

**Úroveň**: `Build.VERSION_CODES.R` (Android 11)

**Vlastnosti:**
- `setControlDisabledPackages()` - Blokování Force Stop
- Plná kontrola nad zařízením
- Nejvyšší úroveň ochrany

**Zdroj**: `clients/android/app/src/main/java/com/familyeye/agent/device/DeviceOwnerPolicyEnforcer.kt:getProtectionLevel()`

### RESURRECTION_MODE (Android 10 a nižší)

**Úroveň**: Android 10 a nižší

**Vlastnosti:**
- Základní Device Owner ochrana
- 5 vrstev persistence (Watchdog, JobScheduler, WorkManager, AlarmManager, KeepAlive)
- Stále velmi robustní

## Deaktivace Device Owner

### Proces deaktivace

Device Owner může být deaktivován pouze:

1. **Rodičem přes webové rozhraní** - `POST /api/devices/{device_id}/deactivate-device-owner`
2. **Factory reset** - Vymaže všechna data
3. **OEM unlock + Flash** - Přeprogramování zařízení

**Technický proces:**
```kotlin
fun deactivateAllProtections(): Boolean {
    restrictionManager.clearBaselineRestrictions()
    setUninstallBlocked(false)
    safeSetControlDisabledPackages(emptyList())
    applySettingsProtection(false)
    disableKioskMode()
    protectionsActive = false
    
    // Relinquish Device Owner status
    dpm.clearDeviceOwnerApp(context.packageName)
    return true
}
```

**Zdroj**: `clients/android/app/src/main/java/com/familyeye/agent/device/DeviceOwnerPolicyEnforcer.kt:deactivateAllProtections()`

## Technické reference

### Android soubory

- `clients/android/app/src/main/java/com/familyeye/agent/device/DeviceOwnerPolicyEnforcer.kt` - Hlavní Device Owner logika
- `clients/android/app/src/main/java/com/familyeye/agent/device/DeviceRestrictions.kt` - Restrikce a konstanty
- `clients/android/app/src/main/java/com/familyeye/agent/service/WatchdogService.kt` - Watchdog
- `clients/android/app/src/main/java/com/familyeye/agent/service/ResurrectionJobService.kt` - JobScheduler
- `clients/android/app/src/main/java/com/familyeye/agent/service/AlarmWatchdog.kt` - AlarmManager
- `clients/android/app/src/main/java/com/familyeye/agent/ui/KeepAliveActivity.kt` - Activity restart

### Backend soubory

- `backend/app/api/devices/actions.py` - Deaktivace Device Owner endpoint
