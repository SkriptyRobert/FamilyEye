# AI Refactoring Prompt - Android Agent FamilyEye

## Kontext

Jsi Senior Architekt, Senior Programátor, Security Expert a UI/UX Specialista. Máš za úkol refaktorovat, optimalizovat a opravit kritické chyby v Android agentovi projektu FamilyEye (rodičovská kontrola).

## Tvoje Role

- **Senior Architekt:** Navrhni lepší architekturu, rozděl "God Objects", vytvoř modulární strukturu
- **Senior Programátor:** Optimalizuj kód, odstraň duplicity, zlepši čitelnost
- **Security Expert:** Oprav všechny bezpečnostní chyby, implementuj security hardening
- **UI/UX Specialista:** Zlepši UI komponenty, rozděl monolitické screens

## Aktuální Stav Projektu

**Struktura:**
```
clients/android/app/src/main/java/com/familyeye/agent/
├── data/          # Repository pattern, Room DB, DataStore
├── di/            # Hilt Dependency Injection
├── receiver/      # Broadcast receivers
├── scanner/       # Smart Shield scanner
├── service/       # Core services (PROBLÉM - God Objects)
└── ui/            # Compose UI (PROBLÉM - monolitické screens)
```

**Technologie:**
- Kotlin, Jetpack Compose, Hilt DI, Room DB, DataStore
- Retrofit, OkHttp, WebSocket
- Accessibility Service, Device Admin

**Statistiky:**
- ~4,486 řádků Kotlin kódu
- 38 souborů
- 3 kritické "God Objects" (328, 206, 536 řádků)

## Kritické Problémy K Opravení

### 1. "God Objects" - REFAKTOROVAT

#### 1.1 AppDetectorService.kt (328 řádků) 🔴 KRITICKÉ

**Aktuální problémy:**
- 8+ zodpovědností v jednom souboru
- Hluboké vnoření (4-5 úrovní)
- Mix synchronní a asynchronní logiky
- Self-protection, whitelist, enforcement vše v jednom souboru

**Co udělat:**
1. **Rozdělit na Handlers:**
   - Vytvoř `service/SelfProtectionHandler.kt` (~60 řádků)
     - `checkForTampering(packageName, className) -> TamperingResult`
     - `shouldBlockSettings(packageName) -> Boolean`
   - Vytvoř `service/AppBlockingHandler.kt` (~80 řádků)
     - `checkBlocking(packageName) -> BlockCheckResult`
     - Orchestrace všech blocking checks
   - Vytvoř `utils/WhitelistManager.kt` (~30 řádků)
     - `isWhitelisted(packageName) -> Boolean`
   - Vytvoř `utils/LauncherDetector.kt` (~20 řádků)
     - `isLauncher(packageName) -> Boolean`

2. **Zmenšit AppDetectorService na ~80 řádků:**
   - Pouze detekce změn aplikací
   - Delegace na Handlers
   - Smart Shield trigger
   - Screenshot flow (možná extrahovat do ScreenshotService)

**Požadovaná struktura:**
```kotlin
class AppDetectorService : AccessibilityService() {
    @Inject lateinit var selfProtectionHandler: SelfProtectionHandler
    @Inject lateinit var appBlockingHandler: AppBlockingHandler
    @Inject lateinit var whitelistManager: WhitelistManager
    
    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        val packageName = event?.packageName?.toString() ?: return
        
        // 1. Self-protection check
        if (handleSelfProtection(packageName, className)) return
        
        // 2. Whitelist check
        if (whitelistManager.isWhitelisted(packageName)) return
        
        // 3. Blocking check
        when (val result = appBlockingHandler.checkBlocking(packageName)) {
            is BlockCheckResult.Allowed -> hideOverlay()
            is BlockCheckResult.Block -> enforceBlock(result)
        }
        
        // 4. Smart Shield trigger
        triggerSmartShieldScan(packageName)
    }
}
```

---

#### 1.2 RuleEnforcer.kt (206 řádků) 🔴 KRITICKÉ

**Aktuální problémy:**
- 9 metod pro různé typy checks
- Duplicitní package matching (3x)
- Inline time parsing
- Těžko testovatelné

**Co udělat:**
1. **Vytvořit Policy Engine:**
   - Vytvoř `policy/PolicyEngine.kt` (~120 řádků)
     - `evaluatePolicy(packageName, context) -> PolicyResult`
     - Orchestrace všech policy checks
   - Vytvoř `policy/AppBlockPolicy.kt` (~60 řádků)
     - `isBlocked(packageName, rules) -> Boolean`
   - Vytvoř `policy/SchedulePolicy.kt` (~60 řádků)
     - `isDeviceScheduleBlocked(rules) -> Boolean`
     - `isAppScheduleBlocked(packageName, rules) -> Boolean`
   - Vytvoř `policy/LimitPolicy.kt` (~50 řádků)
     - `isDailyLimitExceeded(totalUsage, rules) -> Boolean`
     - `isAppTimeLimitExceeded(packageName, usage, rules) -> Boolean`
   - Vytvoř `policy/DeviceLockPolicy.kt` (~40 řádků)
     - `isLocked(rules) -> Boolean`

2. **Vytvořit Utilities:**
   - Vytvoř `utils/PackageMatcher.kt` (~30 řádků)
     - `matches(packageName, ruleName, appLabel) -> Boolean`
     - Odstranit duplicity
   - Vytvoř `utils/TimeUtils.kt` (~60 řádků)
     - `isCurrentTimeInRange(start, end) -> Boolean`
     - `parseMinutes(timeStr) -> Int`
     - `getCurrentMinutes() -> Int`
   - Vytvoř `utils/AppInfoResolver.kt` (~30 řádků)
     - `getAppName(context, packageName) -> String`

3. **Refaktorovat RuleEnforcer:**
   - Buď odstranit (nahradit PolicyEngine)
   - Nebo nechat jako wrapper pro backward compatibility

---

#### 1.3 SetupWizardScreen.kt (536 řádků) 🔴 KRITICKÉ

**Aktuální problémy:**
- 5 kroků v jednom souboru
- Mix UI a business logiky
- Těžko testovatelné

**Co udělat:**
1. **Rozdělit na step komponenty:**
   - Vytvoř `ui/screens/setup/SetupWizardScreen.kt` (~100 řádků)
     - Orchestrátor, step navigation
   - Vytvoř `ui/screens/setup/steps/WelcomeStep.kt` (~80 řádků)
   - Vytvoř `ui/screens/setup/steps/PinSetupStep.kt` (~100 řádků)
     - PIN validace, UI
   - Vytvoř `ui/screens/setup/steps/PermissionsStep.kt` (~150 řádků)
     - Permission checks, requests
   - Vytvoř `ui/screens/setup/steps/PairingStep.kt` (~50 řádků)
     - Wrapper pro PairingScreen
   - Vytvoř `ui/screens/setup/steps/CompleteStep.kt` (~50 řádků)

2. **Přesunout business logiku do ViewModel:**
   - Validace PINu
   - Permission checks
   - Step navigation logika

---

### 2. Duplicity v Kódu - ODSTRANIT

**Nalezené duplicity:**
1. **Package Matching** - 3x v RuleEnforcer.kt
   - Řádky 43-58, 115-117, 176-178
   - **Řešení:** Vytvořit `utils/PackageMatcher.kt`

2. **Time Parsing** - inline v RuleEnforcer.kt
   - Řádky 197-219
   - **Řešení:** Vytvořit `utils/TimeUtils.kt`

3. **App Name Resolution** - v několika souborech
   - **Řešení:** Vytvořit `utils/AppInfoResolver.kt`

**Akce:** Vytvoř všechny utility třídy a nahraď duplicitní kód jejich použitím.

---

### 3. Magic Numbers - ODSTRANIT

**Nalezené magic numbers:**
- `delay(1000)` → `SCREENSHOT_DELAY_MS`
- `delay(5000)` → `USAGE_TRACK_INTERVAL_MS`
- `delay(30000)` → `SYNC_INTERVAL_MS`
- `delay(30_000)` → `RULE_FETCH_INTERVAL_MS`

**Co udělat:**
1. Vytvoř `config/AgentConstants.kt`:
```kotlin
object AgentConstants {
    const val RULE_FETCH_INTERVAL_MS = 30_000L
    const val USAGE_TRACK_INTERVAL_MS = 5_000L
    const val SCREENSHOT_DELAY_MS = 1_000L
    const val SYNC_INTERVAL_MS = 30_000L
    const val SCAN_INTERVAL_MS = 2_000L
    const val HEARTBEAT_INTERVAL_MS = 30_000L
}
```

2. Nahraď všechny magic numbers konstantami.

---

### 4. Security Hardening - OPRAVIT KRITICKÉ CHYBY

#### 4.1 PIN Hashování 🔴 KRITICKÉ

**Aktuální kód:**
```kotlin
private fun hashPin(pin: String): String {
    val bytes = MessageDigest.getInstance("SHA-256").digest(pin.toByteArray())
    return bytes.joinToString("") { "%02x".format(it) }
}
```

**Co udělat:**
- Použít bcrypt nebo Argon2
- Nebo přidat device-specific salt

**Implementace:**
```kotlin
// Přidat dependency: implementation("org.mindrot:jbcrypt:0.4")
import org.mindrot.jbcrypt.BCrypt

private fun hashPin(pin: String): String {
    return BCrypt.hashpw(pin, BCrypt.gensalt(12))
}

override suspend fun verifyPin(pin: String): Boolean {
    val storedHash = dataStore.data.first()[Keys.PIN_HASH] ?: return false
    return try {
        BCrypt.checkpw(pin, storedHash)
    } catch (e: Exception) {
        false
    }
}
```

---

#### 4.2 Hardcoded Backend URL 🔴 KRITICKÉ

**Aktuální kód:**
```kotlin
// build.gradle.kts
buildConfigField("String", "BACKEND_URL", "\"https://192.168.0.145:8000\"")
```

**Co udělat:**
1. Odstranit hardcoded URL z build.gradle.kts
2. Používat pouze dynamickou URL z pairing procesu
3. Pokud je potřeba default, použít prázdný string:

```kotlin
buildTypes {
    debug {
        buildConfigField("String", "BACKEND_URL", "\"\"")
    }
    release {
        buildConfigField("String", "BACKEND_URL", "\"\"")
    }
}
```

4. Upravit WebSocketClient.kt, aby nepoužíval BuildConfig.BACKEND_URL:
```kotlin
// WebSocketClient.kt - řádek 79
// PŘED:
val baseUrl = BuildConfig.BACKEND_URL.replace("https://", "wss://").replace("http://", "ws://")

// PO:
val backendUrl = configRepository.getBackendUrl() ?: return
val baseUrl = backendUrl.replace("https://", "wss://").replace("http://", "ws://")
```

---

#### 4.3 SSL/TLS Trust All Certificates 🔴 KRITICKÉ

**Aktuální kód:**
```kotlin
// NetworkModule.kt - řádky 96-107
if (BuildConfig.DEBUG) {
    builder.sslSocketFactory(sslContext.socketFactory, trustAllCerts[0] as X509TrustManager)
    builder.hostnameVerifier { _, _ -> true }  // ⚠️ DANGEROUS!
}
```

**Co udělat:**
- Odstranit trust all certificates
- Použít pouze network_security_config.xml (už je implementováno)
- Nebo trust pouze specifický certifikát z assets

**Implementace:**
```kotlin
// Odstranit trust all kód
// Použít pouze network_security_config.xml
// Pokud je potřeba self-signed cert, použít @raw/backend_cert
```

---

#### 4.4 API Key v Plaintext 🟡 STŘEDNÍ

**Aktuální kód:**
```kotlin
// AgentConfigRepositoryImpl.kt
override suspend fun savePairingData(deviceId: String, apiKey: String) {
    dataStore.edit { prefs ->
        prefs[Keys.API_KEY] = apiKey  // Plaintext!
    }
}
```

**Co udělat:**
- Použít EncryptedSharedPreferences pro citlivá data

**Implementace:**
```kotlin
// Přidat dependency: implementation("androidx.security:security-crypto:1.1.0-alpha06")
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

// V DataModule.kt
@Provides
@Singleton
fun provideEncryptedPrefs(@ApplicationContext context: Context): SharedPreferences {
    val masterKey = MasterKey.Builder(context)
        .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
        .build()
    
    return EncryptedSharedPreferences.create(
        context,
        "agent_encrypted_prefs",
        masterKey,
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
    )
}

// V AgentConfigRepositoryImpl.kt
@Inject constructor(
    private val dataStore: DataStore<Preferences>,
    private val encryptedPrefs: SharedPreferences  // NOVÉ
) {
    override suspend fun savePairingData(deviceId: String, apiKey: String) {
        // Uložit do encrypted prefs
        encryptedPrefs.edit()
            .putString("device_id", deviceId)
            .putString("api_key", apiKey)
            .apply()
    }
}
```

---

#### 4.5 WebSocket API Key v URL 🟡 STŘEDNÍ

**Aktuální kód:**
```kotlin
// WebSocketClient.kt - řádek 80
val url = "$baseUrl/ws/device/$deviceId?api_key=$apiKey"
```

**Co udělat:**
- Přesunout API Key do HTTP headeru

**Implementace:**
```kotlin
val request = Request.Builder()
    .url("$baseUrl/ws/device/$deviceId")
    .addHeader("X-API-Key", apiKey)
    .build()
```

---

#### 4.6 PIN Logování 🟡 NÍZKÁ

**Aktuální kód:**
```kotlin
// FamilyEyeService.kt - řádek 146
Timber.i("PIN Reset Command Received. New PIN: $newPin")
```

**Co udělat:**
- Maskovat PIN v logách

**Implementace:**
```kotlin
Timber.i("PIN Reset Command Received. New PIN: ***")
// Nebo podmíněně v debug
if (BuildConfig.DEBUG) {
    Timber.d("PIN Reset: $newPin")
} else {
    Timber.i("PIN Reset Command Received")
}
```

---

### 5. Spaghetti Kód - ZLEPŠIT

**Problémy:**
- Hluboké vnoření (4-5 úrovní)
- Mix synchronní a asynchronní logiky
- Těžko čitelné podmínky

**Co udělat:**
1. **Použít early returns:**
```kotlin
// PŘED:
if (condition1) {
    if (condition2) {
        if (condition3) {
            // ...
        }
    }
}

// PO:
if (!condition1) return
if (!condition2) return
if (!condition3) return
// ...
```

2. **Extrahovat metody:**
   - Každá metoda by měla mít max 20-30 řádků
   - Jedna zodpovědnost na metodu

3. **Sjednotit async/sync:**
   - Buď vše synchronní (s cache)
   - Nebo vše asynchronní

---

## Požadavky na Refactoring

### Obecné Zásady:

1. **Single Responsibility Principle:**
   - Každá třída má jednu zodpovědnost
   - Každá metoda dělá jednu věc

2. **DRY (Don't Repeat Yourself):**
   - Odstranit všechny duplicity
   - Vytvořit utility třídy

3. **Testovatelnost:**
   - Všechny nové třídy musí být testovatelné
   - Použít dependency injection
   - Minimalizovat side effects

4. **Čitelnost:**
   - Max 200 řádků na soubor (ideálně 50-150)
   - Max 3 úrovně vnoření
   - Smysluplné názvy proměnných a metod

5. **Bezpečnost:**
   - Opravit všechny kritické security chyby
   - Šifrovat citlivá data
   - Nelogovat citlivá data

### Struktura Nových Souborů:

```
clients/android/app/src/main/java/com/familyeye/agent/
├── policy/                    # NOVÉ
│   ├── PolicyEngine.kt
│   ├── AppBlockPolicy.kt
│   ├── SchedulePolicy.kt
│   ├── LimitPolicy.kt
│   └── DeviceLockPolicy.kt
│
├── enforcement/               # NOVÉ
│   ├── EnforcementService.kt
│   ├── SelfProtectionHandler.kt
│   └── WhitelistManager.kt
│
├── utils/                     # NOVÉ
│   ├── PackageMatcher.kt
│   ├── TimeUtils.kt
│   ├── AppInfoResolver.kt
│   └── LauncherDetector.kt
│
├── config/                    # NOVÉ
│   └── AgentConstants.kt
│
├── service/                   # REFAKTOROVANÉ
│   ├── AppDetectorService.kt (zmenšený)
│   ├── AppBlockingHandler.kt (nový)
│   ├── FamilyEyeService.kt
│   ├── UsageTracker.kt
│   ├── Reporter.kt
│   └── BlockOverlayManager.kt
│
└── ui/
    ├── screens/
    │   ├── setup/             # NOVÉ
    │   │   ├── SetupWizardScreen.kt
    │   │   └── steps/
    │   └── ...
```

---

## Požadované Výsledky

### Metriky Před/Po:

**Před:**
- AppDetectorService: 328 řádků, 8 zodpovědností
- RuleEnforcer: 206 řádků, 9 metod, duplicity
- SetupWizardScreen: 536 řádků, 5 kroků
- Duplicity: 3x package matching, 2x time parsing
- Security: SHA-256 bez salt, hardcoded URL, trust all certs

**Po:**
- AppDetectorService: ~80 řádků, 1 zodpovědnost
- Policy třídy: ~40-60 řádků každá, 1 zodpovědnost
- SetupWizardScreen: ~100 řádků (orchestrátor)
- Duplicity: 0x (vše v utilities)
- Security: bcrypt, encrypted storage, bez hardcoded URL

### Kvalita Kódu:

- ✅ Všechny soubory pod 200 řádků
- ✅ Žádné duplicity
- ✅ Žádné magic numbers
- ✅ Všechny kritické security chyby opraveny
- ✅ Testovatelné komponenty
- ✅ Čistá architektura

---

## Postup Práce

### Fáze 1: Utilities a Constants (Začni zde)
1. Vytvoř `config/AgentConstants.kt`
2. Vytvoř `utils/PackageMatcher.kt`
3. Vytvoř `utils/TimeUtils.kt`
4. Vytvoř `utils/AppInfoResolver.kt`
5. Vytvoř `utils/LauncherDetector.kt`
6. Nahraď všechny duplicity a magic numbers

### Fáze 2: Policy Engine
1. Vytvoř `policy/PolicyEngine.kt`
2. Vytvoř jednotlivé policy třídy
3. Refaktoruj RuleEnforcer (nebo nahraď)
4. Aktualizuj AppBlockingHandler (pokud už existuje)

### Fáze 3: Enforcement Layer
1. Vytvoř `enforcement/SelfProtectionHandler.kt`
2. Vytvoř `enforcement/WhitelistManager.kt`
3. Vytvoř `enforcement/EnforcementService.kt`
4. Refaktoruj AppDetectorService

### Fáze 4: UI Refactoring
1. Rozděl SetupWizardScreen na step komponenty
2. Přesuň business logiku do ViewModel

### Fáze 5: Security Hardening
1. Oprav PIN hashování (bcrypt)
2. Odstranit hardcoded backend URL
3. Opravit SSL trust all
4. Implementovat EncryptedSharedPreferences
5. Přesunout API Key z URL do headeru
6. Maskovat PIN v logách

---

## Důležité Poznámky

1. **Backward Compatibility:**
   - Během refactoringu musí aplikace zůstat funkční
   - Použít wrapper třídy pokud je potřeba
   - Postupná migrace

2. **Testování:**
   - Po každé fázi otestovat funkčnost
   - Ověřit, že všechny existující testy projdou
   - Přidat unit testy pro nové třídy

3. **Dokumentace:**
   - Přidat KDoc komentáře k novým třídám
   - Dokumentovat změny v architektuře

4. **Git:**
   - Commituj po každé fázi
   - Použij smysluplné commit messages
   - Vytvoř feature branch pro refactoring

---

## Očekávané Výsledky

Po dokončení refactoringu by měl projekt mít:

✅ **Čistou architekturu:**
- Modulární struktura
- Jedna zodpovědnost na třídu
- Testovatelné komponenty

✅ **Bezpečný kód:**
- Všechny kritické security chyby opraveny
- Citlivá data šifrovaná
- Bez hardcoded credentials

✅ **Optimalizovaný kód:**
- Žádné duplicity
- Žádné magic numbers
- Čitelný a udržovatelný

✅ **Lepší testovatelnost:**
- Malé, fokusované třídy
- Dependency injection
- Snadné mockování

---

## Začni Práci

Začni s **Fází 1: Utilities a Constants**. Vytvoř všechny utility třídy a konstanty, pak pokračuj postupně dalšími fázemi.

**Důležité:** Po každé fázi otestuj, že aplikace stále funguje. Pokud najdeš nějaké problémy, oprav je před pokračováním.

**Použij tento prompt jako vodítko a postupuj systematicky fázemi 1-5.**

---

**Konec promptu**
