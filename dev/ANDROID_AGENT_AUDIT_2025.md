# Kompletní Audit Android Agenta - FamilyEye

**Datum:** 2025-01-17  
**Auditor:** Senior Architekt, Senior Programátor, Security Expert, UI/UX Specialista  
**Rozsah:** Android Agent - Struktura, Modulárnost, Spaghetti Kód, Bezpečnost, Optimalita

---

## Executive Summary

Android agent FamilyEye je **funkční systém rodičovské kontroly** s komplexní funkcionalitou. Celkové hodnocení: **6.5/10**.

**Hlavní zjištění:**
- ✅ **Pozitivní:** Dobrá základní architektura (Hilt DI, Repository pattern, Compose UI)
- ⚠️ **Problémy:** 3 kritické "God Objects", duplicity v kódu, magic numbers
- 🔴 **Kritické:** AppDetectorService má 8+ zodpovědností, RuleEnforcer má duplicity, SetupWizardScreen je monolitický

**Celkové hodnocení:**
- **Architektura:** 7/10
- **Modulárnost:** 5/10
- **Kvalita kódu:** 6/10
- **Bezpečnost:** 6/10
- **Čistota kódu:** 5/10

**Celkem: 6.5/10**

---

## 1. Statistiky Projektu

### 1.1 Základní Metriky

- **Celkem řádků Kotlin kódu:** ~4,486 řádků
- **Počet souborů:** 38 Kotlin souborů
- **Průměrná velikost souboru:** ~118 řádků
- **Největší soubory:**
  1. SetupWizardScreen.kt - **536 řádků** 🔴
  2. PairingScreen.kt - **335 řádků** 🟡
  3. AppDetectorService.kt - **328 řádků** 🔴
  4. FamilyEyeService.kt - **227 řádků** 🟢
  5. RuleEnforcer.kt - **206 řádků** 🟡

### 1.2 Hodnocení Počtu Řádků vzhledem k Funkcionalitě

**Funkcionalita Android agenta:**
- ✅ Accessibility Service pro detekci aplikací
- ✅ Real-time blokování aplikací
- ✅ Time tracking a limity
- ✅ Schedule enforcement
- ✅ Smart Shield (content scanning)
- ✅ Device pairing
- ✅ PIN ochrana
- ✅ Self-protection (anti-tampering)
- ✅ Usage reporting
- ✅ WebSocket komunikace

**Hodnocení:**
- ✅ **4,486 řádků je přiměřené** pro tuto funkcionalitu
- ✅ Pro komplexní rodičovskou kontrolu je to rozumné množství
- ⚠️ Některé soubory jsou zbytečně velké (signál pro refactoring)

**Srovnání:**
- Komplexní Android aplikace: obvykle 3k-8k řádků
- Projekt je v rozumném rozsahu ✅

---

## 2. Struktura a Organizace

### 2.1 Aktuální Struktura Projektu

```
clients/android/app/src/main/java/com/familyeye/agent/
├── data/
│   ├── api/              # Network layer (Retrofit, WebSocket)
│   ├── local/            # Room database (Entities, DAOs)
│   └── repository/       # Repository pattern (interfaces + impl)
├── di/                   # Dependency Injection (Hilt modules)
├── receiver/             # Broadcast receivers
├── scanner/              # Smart Shield scanner
├── service/              # Core services (PROBLÉM)
└── ui/                   # Compose UI (PROBLÉM)
    ├── components/       # Reusable components
    ├── screens/          # Screen composables
    ├── theme/            # Theme definitions
    └── viewmodel/        # ViewModels
```

**Hodnocení struktury: 7/10**

**Pozitivní:**
- ✅ Jasná separace vrstev (data, service, ui)
- ✅ Repository pattern správně implementován
- ✅ Dependency Injection (Hilt) správně použit
- ✅ Moderní UI s Jetpack Compose

**Problémy:**
- ⚠️ `service/` obsahuje příliš mnoho zodpovědností
- ⚠️ `ui/screens/` obsahuje monolitické komponenty
- ⚠️ Chybí `utils/` package pro utility funkce
- ⚠️ Chybí `policy/` package pro policy engine

---

## 3. Kritické Problémy - "God Objects"

### 3.1 AppDetectorService.kt (328 řádků) 🔴 KRITICKÉ

**Umístění:** `service/AppDetectorService.kt`

**Zodpovědnosti (příliš mnoho - 8+):**
1. ✅ Detekce změn aplikací (Accessibility Service) - OK
2. ❌ Self-protection logika (řádky 150-184) - měl by být v SelfProtectionHandler
3. ❌ Whitelist logika (řádky 294-322) - měl by být v WhitelistManager
4. ❌ Launcher detection (řádky 286-292) - měl by být v LauncherDetector utility
5. ❌ Enforcement logika (řádky 187-260) - měl by být v EnforcementService
6. ❌ Smart Shield trigger (řádky 264-267) - OK, ale může být lépe organizováno
7. ❌ Screenshot flow (řádky 69-101, 330-351) - měl by být v ScreenshotService
8. ❌ Blocking orchestration (řádky 324-328) - měl by být v EnforcementService

**Problémy:**
- **Hluboké vnoření:** 4-5 úrovní v `onAccessibilityEvent` (řádky 131-283)
- **Mix synchronní a asynchronní logiky:** Synchronní checks + async coroutines
- **Těžko testovatelné:** AccessibilityService je těžko mockovatelný
- **Porušuje Single Responsibility Principle:** 8+ různých zodpovědností

**Aktuální kód (problematické části):**
```kotlin
override fun onAccessibilityEvent(event: AccessibilityEvent?) {
    // 1. Self-protection check (50+ řádků)
    if (isDeviceAdminScreen || isPackageInstaller) {
        // ... komplexní logika
    }
    
    // 2. Device Lock check
    if (ruleEnforcer.isDeviceLocked()) {
        // ... další logika
    }
    
    // 3. Whitelist check
    if (isWhitelisted(packageName)) {
        // ...
    }
    
    // 4. App Block check
    if (ruleEnforcer.isAppBlocked(packageName)) {
        // ...
    } else if (ruleEnforcer.isDeviceScheduleBlocked()) {
        // ...
    } else if (ruleEnforcer.isAppScheduleBlocked(packageName)) {
        // ...
    } else {
        // Async checks
        serviceScope.launch {
            // ...
        }
    }
    
    // 5. Smart Shield trigger
    // ...
}
```

**Doporučená struktura:**
```
service/
├── AppDetectorService.kt (~80 řádků)
│   └── Pouze detekce změn, delegace na Handlers
│
policy/
├── PolicyEngine.kt (~120 řádků)
│   └── Orchestrace všech policy checks
│
enforcement/
├── EnforcementService.kt (~80 řádků)
│   └── Orchestrace blokování
├── SelfProtectionHandler.kt (~60 řádků)
│   └── Anti-tampering logika
└── WhitelistManager.kt (~30 řádků)
    └── Whitelist logika
│
utils/
├── LauncherDetector.kt (~20 řádků)
└── ScreenshotService.kt (~50 řádků)
```

**Dopad refactoringu:**
- ✅ Zlepší testovatelnost (Handlers jsou testovatelné samostatně)
- ✅ Sníží kognitivní zátěž (každý soubor má jednu zodpovědnost)
- ✅ Usnadní údržbu (změny v jedné oblasti neovlivní ostatní)

---

### 3.2 RuleEnforcer.kt (206 řádků) 🟡 HORNÍ HRANICE

**Umístění:** `service/RuleEnforcer.kt`

**Zodpovědnosti:**
1. ✅ Cache rules - OK
2. ❌ App blocking check - měl by být v AppBlockPolicy
3. ❌ Device lock check - měl by být v DeviceLockPolicy
4. ❌ Daily limit check - měl by být v LimitPolicy
5. ❌ Schedule checks - měl by být v SchedulePolicy
6. ❌ Time limit checks - měl by být v LimitPolicy
7. ❌ Package matching - **DUPLICITNÍ** (3x v kódu)
8. ❌ Time parsing - **DUPLICITNÍ** (inline, měl by být utility)

**Problémy:**
- **9 různých metod** pro různé typy checks
- **Duplicitní package matching** (řádky 43-58, 115-117, 176-178)
- **Inline time parsing** (řádky 197-219) - měl by být v TimeUtils
- **Těžko testovatelné** - mnoho zodpovědností

**Duplicitní kód - Package Matching:**
```kotlin
// Opakuje se 3x v RuleEnforcer.kt:
// Řádky 43-58 (isAppBlocked)
if (ruleName.equals(packageName, ignoreCase = true)) return@any true
if (packageName.contains(ruleName, ignoreCase = true)) return@any true
if (ruleName.equals(appLabel, ignoreCase = true)) return@any true

// Řádky 115-117 (isAppScheduleBlocked) - STEJNÉ
// Řádky 176-178 (isAppTimeLimitExceeded) - STEJNÉ
```

**Duplicitní kód - Time Parsing:**
```kotlin
// Řádky 197-219 - inline time parsing
private fun isCurrentTimeInRange(startStr: String, endStr: String): Boolean {
    val now = java.util.Calendar.getInstance()
    val currentMinutes = now.get(Calendar.HOUR_OF_DAY) * 60 + now.get(Calendar.MINUTE)
    
    fun parseMinutes(timeStr: String): Int {
        val parts = timeStr.split(":")
        return parts[0].toInt() * 60 + parts[1].toInt()
    }
    // ...
}
```

**Doporučená struktura:**
```
policy/
├── PolicyEngine.kt (orchestrátor)
│   └── evaluatePolicy(packageName, context) -> PolicyResult
│
├── AppBlockPolicy.kt
│   └── isBlocked(packageName, rules) -> Boolean
│
├── SchedulePolicy.kt
│   ├── isDeviceScheduleBlocked(rules) -> Boolean
│   └── isAppScheduleBlocked(packageName, rules) -> Boolean
│
├── LimitPolicy.kt
│   ├── isDailyLimitExceeded(totalUsage, rules) -> Boolean
│   └── isAppTimeLimitExceeded(packageName, usage, rules) -> Boolean
│
└── DeviceLockPolicy.kt
    └── isLocked(rules) -> Boolean
│
utils/
├── PackageMatcher.kt
│   └── matches(packageName, ruleName, appLabel) -> Boolean
└── TimeUtils.kt
    ├── isCurrentTimeInRange(start, end) -> Boolean
    └── parseMinutes(timeStr) -> Int
```

---

### 3.3 SetupWizardScreen.kt (536 řádků) 🔴 KRITICKÉ

**Umístění:** `ui/screens/SetupWizardScreen.kt`

**Zodpovědnosti:**
1. ✅ Orchestrace wizardu - OK
2. ❌ Welcome step UI + logika (řádky 118-122)
3. ❌ PIN setup UI + logika + validace (řádky 124-142)
4. ❌ Permissions step UI + logika + request handling (řádky 145-200+)
5. ❌ Pairing step (řádky 200+)
6. ❌ Complete step UI (řádky 400+)

**Problémy:**
- **5 různých kroků v jednom souboru**
- **Mix UI a business logiky** - validace PINu je v UI komponentu
- **Těžko testovatelné** - nelze testovat jednotlivé kroky samostatně
- **Těžko udržovatelné** - změna jednoho kroku vyžaduje editaci velkého souboru

**Doporučená struktura:**
```
ui/screens/setup/
├── SetupWizardScreen.kt (~100 řádků)
│   └── Orchestrátor, step navigation
│
├── steps/
│   ├── WelcomeStep.kt (~80 řádků)
│   ├── PinSetupStep.kt (~100 řádků)
│   │   └── PIN validace, UI
│   ├── PermissionsStep.kt (~150 řádků)
│   │   └── Permission checks, requests
│   ├── PairingStep.kt (~50 řádků)
│   │   └── Wrapper pro PairingScreen
│   └── CompleteStep.kt (~50 řádků)
│
└── viewmodel/
    └── SetupWizardViewModel.kt
        └── Business logika wizardu
```

---

## 4. Duplicity v Kódu

### 4.1 Package Name Matching (3x duplicitní) 🔴

**Nalezeno v:**
- `RuleEnforcer.kt` (řádky 43-58, 115-117, 176-178)

**Duplicitní kód:**
```kotlin
// Opakuje se 3x
if (ruleName.equals(packageName, ignoreCase = true)) return@any true
if (packageName.contains(ruleName, ignoreCase = true)) return@any true
if (ruleName.equals(appLabel, ignoreCase = true)) return@any true
```

**Řešení:**
```kotlin
// utils/PackageMatcher.kt
object PackageMatcher {
    fun matches(
        packageName: String,
        ruleName: String,
        appLabel: String
    ): Boolean {
        return ruleName.equals(packageName, ignoreCase = true) ||
               packageName.contains(ruleName, ignoreCase = true) ||
               ruleName.equals(appLabel, ignoreCase = true)
    }
}
```

**Dopad:** Snížení kódu o ~15 řádků, lepší udržovatelnost.

---

### 4.2 Time Parsing (inline v RuleEnforcer) 🟡

**Nalezeno v:**
- `RuleEnforcer.kt` (řádky 197-219)

**Problém:** Inline time parsing logika, která by měla být v utility třídě.

**Řešení:**
```kotlin
// utils/TimeUtils.kt
object TimeUtils {
    fun isCurrentTimeInRange(startStr: String, endStr: String): Boolean {
        val now = Calendar.getInstance()
        val currentMinutes = now.get(Calendar.HOUR_OF_DAY) * 60 + 
                            now.get(Calendar.MINUTE)
        
        val startMinutes = parseMinutes(startStr)
        val endMinutes = parseMinutes(endStr)
        
        if (endMinutes < startMinutes) {
            return currentMinutes >= startMinutes || currentMinutes < endMinutes
        }
        return currentMinutes in startMinutes until endMinutes
    }
    
    fun parseMinutes(timeStr: String): Int {
        val parts = timeStr.split(":")
        return parts[0].toInt() * 60 + parts[1].toInt()
    }
    
    fun getCurrentMinutes(): Int {
        val now = Calendar.getInstance()
        return now.get(Calendar.HOUR_OF_DAY) * 60 + now.get(Calendar.MINUTE)
    }
}
```

---

### 4.3 App Name Resolution (2x duplicitní) 🟡

**Nalezeno v:**
- `RuleEnforcer.kt` (řádky 64-72)
- Pravděpodobně i v dalších souborech

**Řešení:**
```kotlin
// utils/AppInfoResolver.kt
object AppInfoResolver {
    fun getAppName(context: Context, packageName: String): String {
        return try {
            val packageManager = context.packageManager
            val info = packageManager.getApplicationInfo(packageName, 0)
            packageManager.getApplicationLabel(info).toString()
        } catch (e: Exception) {
            packageName.split(".").last()
        }
    }
}
```

---

## 5. Magic Numbers

### 5.1 Nalezené Magic Numbers

**Nalezeno v:**
- `AppDetectorService.kt`: `delay(1000)` - SCREENSHOT_DELAY_MS
- `UsageTracker.kt`: `delay(5000)` - USAGE_TRACK_INTERVAL_MS
- `Reporter.kt`: `delay(30000)` - SYNC_INTERVAL_MS
- `FamilyEyeService.kt`: `delay(30_000)` - RULE_FETCH_INTERVAL_MS
- `ContentScanner.kt`: `SCAN_INTERVAL_MS = 2000L` - ✅ Dobře (konstanta)

**Problém:** Magic numbers ztěžují údržbu a konfiguraci.

**Řešení:**
```kotlin
// config/AgentConstants.kt
object AgentConstants {
    const val RULE_FETCH_INTERVAL_MS = 30_000L
    const val USAGE_TRACK_INTERVAL_MS = 5_000L
    const val SCREENSHOT_DELAY_MS = 1_000L
    const val SYNC_INTERVAL_MS = 30_000L
    const val SCAN_INTERVAL_MS = 2_000L
    const val HEARTBEAT_INTERVAL_MS = 30_000L
}
```

---

## 6. Spaghetti Kód Indikátory

### 6.1 Hluboké Vnoření v AppDetectorService.kt

**Problém:** `onAccessibilityEvent` má 4-5 úrovní vnoření:

```kotlin
override fun onAccessibilityEvent(event: AccessibilityEvent?) {
    if (!isPaired) return
    
    if (event.eventType == AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED) {
        if (packageName == this.packageName) return
        
        if (isDeviceAdminScreen || isPackageInstaller) {
            if (::ruleEnforcer.isInitialized && ruleEnforcer.isUnlockSettingsActive()) {
                // ...
            } else {
                // ...
            }
        }
        
        if (::ruleEnforcer.isInitialized && ::blockOverlayManager.isInitialized) {
            if (ruleEnforcer.isDeviceLocked()) {
                if (packageName == "com.android.systemui") {
                    // ...
                }
                if (isLauncher(packageName)) {
                    // ...
                } else {
                    // ...
                }
            }
            // ... další 3 úrovně
        }
    }
}
```

**Doporučení:** Použít early returns a extrahovat metody.

---

### 6.2 Mix Synchronní a Asynchronní Logiky

**Problém:** V `AppDetectorService.onAccessibilityEvent` je mix:
- Synchronní checks (Device Lock, Whitelist, App Block)
- Asynchronní checks (Daily Limit, App Time Limit) - v `serviceScope.launch`

**Doporučení:** Sjednotit přístup - buď vše synchronní (s cache), nebo vše asynchronní.

---

## 7. Detailní Security Hardening Audit

### 7.1 Kritické Bezpečnostní Rizika 🔴

#### 7.1.1 PIN Hashování - Pouze SHA-256 bez Salt 🔴 KRITICKÉ

**Umístění:** `data/repository/AgentConfigRepositoryImpl.kt` (řádky 101-104)

```kotlin
private fun hashPin(pin: String): String {
    val bytes = MessageDigest.getInstance("SHA-256").digest(pin.toByteArray())
    return bytes.joinToString("") { "%02x".format(it) }
}
```

**Riziko:** 
- SHA-256 bez salt je zranitelné vůči rainbow table útokům
- Pokud je databáze kompromitována, PIN může být rychle prolomen
- Stejný PIN na různých zařízeních bude mít stejný hash

**Doporučení:**
```kotlin
// Použít bcrypt nebo Argon2
import org.mindrot.jbcrypt.BCrypt

private fun hashPin(pin: String): String {
    // bcrypt automaticky přidává salt
    return BCrypt.hashpw(pin, BCrypt.gensalt(12))
}

private fun verifyPin(pin: String, hash: String): Boolean {
    return BCrypt.checkpw(pin, hash)
}

// Nebo použít device-specific salt
private fun hashPin(pin: String): String {
    val deviceId = getDeviceId() // unique per device
    val salt = "${deviceId}_${Build.SERIAL}".toByteArray()
    val bytes = MessageDigest.getInstance("SHA-256").digest(pin.toByteArray() + salt)
    return bytes.joinToString("") { "%02x".format(it) }
}
```

**Priorita:** VYSOKÁ - implementovat okamžitě

---

#### 7.1.2 API Key a Device ID v Plaintext 🟡 STŘEDNÍ

**Umístění:** `data/repository/AgentConfigRepositoryImpl.kt` (řádky 45-49)

```kotlin
override suspend fun savePairingData(deviceId: String, apiKey: String) {
    dataStore.edit { prefs ->
        prefs[Keys.DEVICE_ID] = deviceId
        prefs[Keys.API_KEY] = apiKey  // Plaintext!
    }
}
```

**Riziko:**
- DataStore Preferences jsou šifrované pouze pokud je zařízení locked (Android 9+)
- Na unlocked zařízení jsou data v plaintext
- API Key je citlivá data - měla by být šifrovaná vždy

**Doporučení:**
```kotlin
// Použít EncryptedSharedPreferences nebo Android Keystore
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

private val masterKey = MasterKey.Builder(context)
    .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
    .build()

private val encryptedPrefs = EncryptedSharedPreferences.create(
    context,
    "agent_encrypted_prefs",
    masterKey,
    EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
    EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
)

override suspend fun savePairingData(deviceId: String, apiKey: String) {
    encryptedPrefs.edit()
        .putString("device_id", deviceId)
        .putString("api_key", apiKey)
        .apply()
}
```

**Priorita:** STŘEDNÍ - implementovat v příští verzi

---

#### 7.1.3 Hardcoded Backend URL v Build Konfiguraci 🔴 KRITICKÉ

**Umístění:** `build.gradle.kts` (řádky 26, 35)

```kotlin
buildTypes {
    debug {
        buildConfigField("String", "BACKEND_URL", "\"https://192.168.0.145:8000\"")
    }
    release {
        buildConfigField("String", "BACKEND_URL", "\"https://192.168.0.145:8000\"")
    }
}
```

**Riziko:**
- Hardcoded IP adresa v build konfiguraci
- Stejná hodnota pro debug i release build
- Nelze změnit bez rebuildu aplikace
- IP adresa je viditelná v APK (dekompilace)

**Doporučení:**
1. **Odstranit hardcoded URL z build.gradle.kts**
2. **Používat pouze dynamickou URL z pairing procesu**
3. **Pokud je potřeba default, použít environment variable:**

```kotlin
// build.gradle.kts
buildTypes {
    debug {
        val defaultUrl = project.findProperty("DEFAULT_BACKEND_URL") 
            ?: "\"\""
        buildConfigField("String", "BACKEND_URL", defaultUrl)
    }
    release {
        buildConfigField("String", "BACKEND_URL", "\"\"")
    }
}
```

**Priorita:** VYSOKÁ - odstranit okamžitě

---

#### 7.1.4 SSL/TLS - Trust All Certificates v Debug Módu 🔴 KRITICKÉ

**Umístění:** `di/NetworkModule.kt` (řádky 96-107)

```kotlin
if (BuildConfig.DEBUG) {
    // Trust all certificates for local development (self-signed)
    val trustAllCerts = arrayOf<TrustManager>(object : X509TrustManager {
        override fun checkClientTrusted(chain: Array<out X509Certificate>?, authType: String?) {}
        override fun checkServerTrusted(chain: Array<out X509Certificate>?, authType: String?) {}
        override fun getAcceptedIssuers(): Array<X509Certificate> = arrayOf()
    })
    
    builder.sslSocketFactory(sslContext.socketFactory, trustAllCerts[0] as X509TrustManager)
    builder.hostnameVerifier { _, _ -> true }  // ⚠️ DANGEROUS!
}
```

**Riziko:**
- V debug módu aplikace akceptuje všechny certifikáty
- Pokud se debug build dostane do produkce, je aplikace zranitelná vůči MITM útokům
- Hostname verification je vypnutá

**Doporučení:**
1. **Použít pouze pro lokální development s konkrétním certifikátem:**
```kotlin
if (BuildConfig.DEBUG && BuildConfig.BUILD_TYPE == "debug") {
    // Trust only specific self-signed certificate
    val cert = loadCertificateFromAssets("backend_cert.pem")
    val trustManager = createTrustManagerForCertificate(cert)
    builder.sslSocketFactory(sslContext.socketFactory, trustManager)
    builder.hostnameVerifier { hostname, _ -> 
        hostname == "192.168.0.145" || hostname == "localhost"
    }
}
```

2. **NEBO použít network_security_config.xml (což už je implementováno ✅)**

**Priorita:** VYSOKÁ - opravit okamžitě

---

### 7.2 Střední Bezpečnostní Rizika 🟡

#### 7.2.1 Hardcoded Keywords v KeywordManager 🟡

**Umístění:** `scanner/KeywordManager.kt` (řádky 20-24)

```kotlin
init {
    cachedKeywords = listOf(
        ShieldKeyword(0, 0, "sebevražda", "danger", "high", true),
        ShieldKeyword(0, 0, "zabiju", "danger", "high", true),
        ShieldKeyword(0, 0, "drogy", "danger", "high", true)
    )
}
```

**Riziko:**
- Hardcoded keywords v kódu - těžko udržovatelné
- Nelze aktualizovat bez rebuildu aplikace
- Keywords jsou viditelné v APK (dekompilace)

**Doporučení:**
1. **Přesunout do konfiguračního souboru:**
```kotlin
// assets/keywords.json
[
  {"keyword": "sebevražda", "category": "danger", "severity": "high"},
  ...
]

// KeywordManager.kt
private fun loadDefaultKeywords(): List<ShieldKeyword> {
    val json = context.assets.open("keywords.json").bufferedReader().use { it.readText() }
    // Parse JSON
}
```

2. **Nebo použít pouze server-side keywords** (aktuálně se synchronizují ✅)

**Priorita:** STŘEDNÍ

---

#### 7.2.2 WebSocket API Key v URL Query String 🟡

**Umístění:** `data/api/WebSocketClient.kt` (řádek 80)

```kotlin
val url = "$baseUrl/ws/device/$deviceId?api_key=$apiKey"
```

**Riziko:**
- API Key je v URL query string
- Může být logován v server logs
- Může být viditelný v network traces

**Doporučení:**
```kotlin
// Použít HTTP header místo query string
val request = Request.Builder()
    .url("$baseUrl/ws/device/$deviceId")
    .addHeader("X-API-Key", apiKey)
    .build()
```

**Priorita:** STŘEDNÍ

---

#### 7.2.3 Network Security Config - Hardcoded IP Adresy 🟡

**Umístění:** `res/xml/network_security_config.xml` (řádky 13-14)

```xml
<domain includeSubdomains="true">192.168.0.145</domain>
<domain includeSubdomains="true">localhost</domain>
```

**Riziko:**
- Hardcoded IP adresy v konfiguraci
- Nelze změnit bez rebuildu

**Doporučení:**
- Pro standalone deployment je to OK (lokální síť)
- Pro produkci by měly být dynamické nebo použít wildcard

**Priorita:** NÍZKÁ (pro standalone je OK)

---

### 7.3 Nižší Bezpečnostní Rizika 🟢

#### 7.3.1 Logování Citlivých Dat 🟢

**Nalezeno:**
- `WebSocketClient.kt` řádek 82: `Timber.d("Connecting to WebSocket: $baseUrl/ws/device/***")` ✅ Dobře (maskováno)
- `FamilyEyeService.kt` řádek 146: `Timber.i("PIN Reset Command Received. New PIN: $newPin")` ⚠️ PIN je logován!

**Riziko:**
- PIN může být v log souborech
- Logy mohou být přístupné jiným aplikacím

**Doporučení:**
```kotlin
// NELOGOVAT PIN!
Timber.i("PIN Reset Command Received. New PIN: ***")

// Nebo použít podmíněné logování pouze v debug
if (BuildConfig.DEBUG) {
    Timber.d("PIN Reset: $newPin")
} else {
    Timber.i("PIN Reset Command Received")
}
```

**Priorita:** NÍZKÁ

---

#### 7.3.2 HTTP Logging v Debug Módu 🟢

**Umístění:** `di/NetworkModule.kt` (řádky 90-94)

```kotlin
if (BuildConfig.DEBUG) {
    val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BODY  // ⚠️ Loguje celé requesty včetně API keys
    }
    builder.addInterceptor(loggingInterceptor)
}
```

**Riziko:**
- V debug módu se logují celé HTTP requesty včetně API keys
- Pokud se debug build dostane do produkce, API keys jsou v logách

**Doporučení:**
```kotlin
if (BuildConfig.DEBUG) {
    val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.HEADERS  // Nebo BASIC, ne BODY
    }
    // Nebo použít custom interceptor, který maskuje API keys
}
```

**Priorita:** NÍZKÁ

---

### 7.4 Pozitivní Bezpečnostní Aspekty ✅

1. **`allowBackup="false"`** ✅
   - AndroidManifest.xml řádek 43
   - Zabraňuje zálohování citlivých dat

2. **Network Security Config** ✅
   - `cleartextTrafficPermitted="false"` ✅
   - Pouze HTTPS/WSS komunikace

3. **Device Admin Protection** ✅
   - Anti-tampering mechanismus
   - Detekce pokusů o deaktivaci

4. **Self-Protection** ✅
   - Blokování Device Admin deactivation
   - Blokování uninstall pokusů

5. **PIN Protection** ✅
   - PIN je vyžadován pro přístup k nastavení
   - Hash je uložen (i když slabý)

---

### 7.5 Security Hardening Doporučení - Priorita

#### Priorita 1 (Kritické - Okamžitě):
1. ✅ **Zlepšit PIN hashování** - bcrypt/Argon2 + salt
2. ✅ **Odstranit hardcoded backend URL** z build.gradle.kts
3. ✅ **Opravit SSL trust all** v debug módu
4. ✅ **Nelogovat PIN** v plaintext

#### Priorita 2 (Střední - 1 měsíc):
1. ✅ **Šifrovat API Key a Device ID** - EncryptedSharedPreferences
2. ✅ **Přesunout API Key z URL** do HTTP headeru
3. ✅ **Přesunout hardcoded keywords** do assets

#### Priorita 3 (Nízká - 2-3 měsíce):
1. ✅ **Zlepšit HTTP logging** - maskovat citlivá data
2. ✅ **Audit všech logů** - ověřit, že neobsahují citlivá data

---

## 8. Přebytečný/Nadbytečný Kód

### 8.1 Zakomentovaný Kód

**Nalezeno:**
- `AppDetectorService.kt` řádek 149: `// ... (Core Blocking Logic - Keep as is)`
- Některé komentáře jsou redundantní

**Doporučení:** Odstranit zakomentovaný kód nebo implementovat.

---

### 8.2 Duplicitní Komentáře

**Nalezeno:**
- `PairingScreen.kt` řádky 35, 47, 58: Stejný komentář o QR formátu 3x

**Doporučení:** Sjednotit komentáře.

---

### 8.3 Nepoužívané Importy

**Doporučení:** Zkontrolovat IDE warnings pro nepoužívané importy.

---

## 9. Zbytečné Soubory

### 9.1 Testovací Soubory

**Nalezeno:** Žádné zbytečné soubory v hlavním kódu.

**Poznámka:** Build artefakty by neměly být v repozitáři (ale to je mimo scope tohoto auditu).

---

## 10. Modulárnost a Separace

### 10.1 Hodnocení Modulárnosti: 5/10

**Pozitivní:**
- ✅ Jasná separace vrstev (data, service, ui)
- ✅ Dependency Injection správně implementováno
- ✅ Repository pattern pro data access
- ✅ Separace concerns (UsageTracker, Reporter, RuleEnforcer jsou oddělené)

**Problémy:**
- ⚠️ Některé služby mají příliš mnoho zodpovědností
- ⚠️ UI komponenty jsou příliš velké (monolitické screens)
- ⚠️ Chybí abstrakce pro některé utility funkce
- ⚠️ Chybí policy engine (vše je v RuleEnforcer)

**Doporučení pro zlepšení modulárnosti:**

1. **Vytvořit `policy/` package:**
   ```
   policy/
   ├── PolicyEngine.kt
   ├── AppBlockPolicy.kt
   ├── SchedulePolicy.kt
   ├── LimitPolicy.kt
   └── DeviceLockPolicy.kt
   ```

2. **Vytvořit `utils/` package:**
   ```
   utils/
   ├── PackageMatcher.kt
   ├── TimeUtils.kt
   ├── AppInfoResolver.kt
   └── LauncherDetector.kt
   ```

3. **Vytvořit `enforcement/` package:**
   ```
   enforcement/
   ├── EnforcementService.kt
   ├── SelfProtectionHandler.kt
   └── WhitelistManager.kt
   ```

4. **Rozdělit UI screens na menší komponenty:**
   ```
   ui/screens/setup/
   ├── SetupWizardScreen.kt
   ├── WelcomeStep.kt
   ├── PinSetupStep.kt
   ├── PermissionsStep.kt
   └── CompleteStep.kt
   ```

---

## 11. Čistota a Optimalita Kódu

### 11.1 Hodnocení Čistoty: 5/10

**Pozitivní:**
- ✅ Většina souborů je v rozumném rozsahu (50-200 řádků)
- ✅ Použití moderních Kotlin features (sealed classes, coroutines)
- ✅ Dobré komentáře v některých částech

**Problémy:**
- 🔴 3 soubory nad 300 řádků (kritické)
- 🟡 2 soubory 200-300 řádků (hraniční)
- 🟡 Duplicity v kódu
- 🟡 Magic numbers
- 🟡 Hluboké vnoření

**Doporučení:**
- Soubory nad 400 řádků: **refaktorovat okamžitě**
- Soubory 200-400 řádků: **zvážit rozdělení**
- Soubory pod 200 řádků: **OK**

---

## 12. Doporučení a Akční Plán

### 12.1 Priorita 1 (Kritické - 1-2 týdny)

1. **Refactoring AppDetectorService:**
   - ✅ Rozdělit na AppDetectorService + Handlers
   - ✅ Vytvořit SelfProtectionHandler
   - ✅ Vytvořit WhitelistManager
   - ✅ Vytvořit LauncherDetector utility

2. **Refactoring RuleEnforcer:**
   - ✅ Rozdělit na Policy Engine s jednotlivými policy třídami
   - ✅ Vytvořit PackageMatcher utility
   - ✅ Vytvořit TimeUtils utility

3. **Bezpečnost:**
   - ✅ Zlepšit PIN hashování (bcrypt + salt)

### 12.2 Priorita 2 (Důležité - 1 měsíc)

1. **Refactoring SetupWizardScreen:**
   - ✅ Rozdělit na jednotlivé step komponenty

2. **Odstranit duplicity:**
   - ✅ Vytvořit utility třídy
   - ✅ Sjednotit time parsing

3. **Magic numbers:**
   - ✅ Vytvořit AgentConstants.kt

### 12.3 Priorita 3 (Doporučené - 2-3 měsíce)

1. **Kvalita kódu:**
   - ✅ Odstranit magic numbers
   - ✅ Zlepšit error handling
   - ✅ Přidat více unit testů

2. **Dokumentace:**
   - ✅ Dokumentovat architekturu
   - ✅ Přidat API dokumentaci

---

## 13. Závěr

Android agent FamilyEye má **solidní základ** s moderními technologiemi a dobrou separací vrstev. Hlavní problémy jsou:

1. **3 kritické "God Objects"** - vyžadují refactoring
2. **Duplicity v kódu** - lze řešit postupně
3. **Bezpečnostní rizika** - vyžadují okamžité řešení
4. **Magic numbers** - snadné řešení

**Celkové hodnocení: 6.5/10**

S implementací doporučení by projekt mohl dosáhnout **8-8.5/10**.

**Klíčové body:**
- ✅ Počet řádků kódu je přiměřený pro funkcionalitu
- ⚠️ Některé soubory jsou zbytečně velké
- ⚠️ Duplicity ztěžují údržbu
- ✅ Základní architektura je dobrá

---

**Konec auditu**
