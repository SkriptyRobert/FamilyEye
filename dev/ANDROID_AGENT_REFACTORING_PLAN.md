# Android Agent - Detailní Audit a Refactoring Plán

**Datum:** 2025-01-17  
**Verze:** 1.0  
**Autor:** Senior Architekt, Senior Programátor, Security Expert

---

## Executive Summary

Android agent FamilyEye je funkční, ale trpí několika architektonickými problémy, které ztěžují údržbu, testování a budoucí rozvoj. Tento dokument poskytuje detailní analýzu a konkrétní plán refactoringu.

**Hlavní zjištění:**
- 🔴 **3 kritické "God Objects"** vyžadující okamžité rozdělení
- 🟡 **Duplicity v kódu** napříč více soubory
- 🟡 **Tight coupling** mezi službami
- 🟢 **Dobrá základní architektura** (Hilt DI, Repository pattern)

**Doporučená strategie:**
- Fázovaný refactoring (3 fáze, 6-8 týdnů)
- Zachování funkčnosti během refactoringu
- Postupné zlepšování testovatelnosti

---

## 1. Aktuální Architektura

### 1.1 Struktura Projektu

```
clients/android/app/src/main/java/com/familyeye/agent/
├── data/
│   ├── api/              # Network layer
│   ├── local/            # Room database
│   └── repository/       # Repository pattern
├── di/                   # Dependency Injection (Hilt)
├── receiver/             # Broadcast receivers
├── scanner/              # Smart Shield scanner
├── service/              # Core services (PROBLÉM)
└── ui/                   # Compose UI (PROBLÉM)
```

### 1.2 Dependency Graph

```
FamilyEyeService (Orchestrator)
├── AgentConfigRepository
├── UsageTracker
│   ├── RuleEnforcer
│   ├── BlockOverlayManager
│   └── Reporter
├── Reporter
│   ├── FamilyEyeApi
│   ├── UsageLogDao
│   └── KeywordManager
├── RuleEnforcer
│   └── RuleRepository
└── WebSocketClient
    └── AgentConfigRepository

AppDetectorService (Accessibility Service)
├── RuleEnforcer
├── BlockOverlayManager
├── UsageTracker
├── Reporter
└── ContentScanner
    └── KeywordManager
```

**Problém:** Cyklické závislosti a tight coupling.

---

## 2. Kritické Problémy

### 2.1 "God Object" - AppDetectorService.kt (310 řádků)

**Umístění:** `service/AppDetectorService.kt`

**Zodpovědnosti (příliš mnoho):**
1. ✅ Detekce změn aplikací (Accessibility Service)
2. ❌ Whitelist logika (měl by být v PolicyEngine)
3. ❌ Enforcement logika (měl by být v EnforcementService)
4. ❌ Overlay management (přímé volání BlockOverlayManager)
5. ❌ Smart Shield scanning trigger (měl by být v orchestratoru)
6. ❌ Screenshot flow (měl by být v ScreenshotService)
7. ❌ Device lock handling (měl by být v PolicyEngine)
8. ❌ Schedule enforcement (měl by být v PolicyEngine)

**Problémy:**
- Hluboké vnoření (4-5 úrovní)
- Mix synchronní a asynchronní logiky
- Těžko testovatelné (AccessibilityService je těžko mockovatelný)
- Porušuje Single Responsibility Principle

**Aktuální kód (problematické části):**
```kotlin
override fun onAccessibilityEvent(event: AccessibilityEvent?) {
    // 1. Device Lock Check
    if (ruleEnforcer.isDeviceLocked()) {
        if (packageName == "com.android.systemui") {
            performGlobalAction(GLOBAL_ACTION_BACK)
            return
        }
        if (isLauncher(packageName)) {
            blockOverlayManager.show(packageName, BlockType.DEVICE_LOCK)
        } else {
            blockApp(packageName, BlockType.DEVICE_LOCK)
        }
        return
    }
    
    // 2. Whitelist Check
    if (isWhitelisted(packageName)) {
        blockOverlayManager.hide()
        return
    }
    
    // 3. App Block Check
    if (ruleEnforcer.isAppBlocked(packageName)) {
        blockApp(packageName, BlockType.APP_FORBIDDEN)
    } else if (ruleEnforcer.isDeviceScheduleBlocked()) {
        // ... další logika
    }
    // ... další 100+ řádků
}
```

**Doporučená struktura:**
```
service/
├── AppDetectorService.kt (~80 řádků)
│   └── Pouze detekce změn, delegace na PolicyEngine
│
policy/
├── PolicyEngine.kt (~120 řádků)
│   ├── evaluatePolicy(packageName) -> PolicyResult
│   └── Orchestrace všech policy checks
├── AppBlockPolicy.kt (~60 řádků)
├── SchedulePolicy.kt (~60 řádků)
├── LimitPolicy.kt (~50 řádků)
└── DeviceLockPolicy.kt (~40 řádků)
│
enforcement/
├── EnforcementService.kt (~80 řádků)
│   ├── enforceBlock(packageName, blockType)
│   └── Orchestrace blokování
└── WhitelistManager.kt (~30 řádků)
```

---

### 2.2 "God Object" - RuleEnforcer.kt (218 řádků)

**Umístění:** `service/RuleEnforcer.kt`

**Zodpovědnosti:**
1. ✅ Cache rules
2. ❌ App blocking check (měl by být v AppBlockPolicy)
3. ❌ Device lock check (měl by být v DeviceLockPolicy)
4. ❌ Daily limit check (měl by být v LimitPolicy)
5. ❌ Schedule checks (měl by být v SchedulePolicy)
6. ❌ Time limit checks (měl by být v LimitPolicy)
7. ❌ Package matching (duplicitní - měl by být v PackageMatcher)
8. ❌ Time parsing (měl by být v TimeUtils)

**Problémy:**
- 9 různých metod pro různé typy checks
- Duplicitní package matching logika (3x)
- Inline time parsing (měl by být utility)
- Těžko testovatelné (mnoho zodpovědností)

**Aktuální struktura metod:**
```kotlin
class RuleEnforcer {
    fun isAppBlocked(packageName: String): Boolean
    fun isDeviceLocked(): Boolean
    fun isDailyLimitExceeded(totalUsageSeconds: Int): Boolean
    fun isDeviceScheduleBlocked(): Boolean
    fun isAppScheduleBlocked(packageName: String): Boolean
    fun isAppTimeLimitExceeded(packageName: String, usageSeconds: Int): Boolean
    fun isUnlockSettingsActive(): Boolean
    fun getActiveAppScheduleRule(packageName: String): RuleDTO?
    fun getActiveDeviceScheduleRule(): RuleDTO?
    
    // Private helpers
    private fun isRuleActiveNow(rule: RuleDTO): Boolean
    private fun isCurrentTimeInRange(startStr: String, endStr: String): Boolean
    private fun getAppName(packageName: String): String
}
```

**Doporučená struktura:**
```
policy/
├── PolicyEngine.kt (orchestrátor)
│   ├── evaluatePolicy(packageName, context) -> PolicyResult
│   └── Používá všechny policy třídy
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
```

---

### 2.3 "God Object" - SetupWizardScreen.kt (536 řádků)

**Umístění:** `ui/screens/SetupWizardScreen.kt`

**Zodpovědnosti:**
1. ✅ Orchestrace wizardu
2. ❌ Welcome step UI + logika
3. ❌ PIN setup UI + logika + validace
4. ❌ Permissions step UI + logika + request handling
5. ❌ Pairing step (reuse PairingScreen)
6. ❌ Complete step UI

**Problémy:**
- Mix UI a business logiky
- 5 různých kroků v jednom souboru
- Těžko testovatelné
- Těžko udržovatelné

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

### 2.4 Duplicity v Kódu

#### 2.4.1 Package Name Matching (3x duplicitní)

**Nalezeno v:**
- `AppDetectorService.kt` (řádky 242-270)
- `RuleEnforcer.kt` (řádky 37-58, 113-117, 174-178)

**Duplicitní kód:**
```kotlin
// Opakuje se 3x
if (ruleName.equals(packageName, ignoreCase = true)) return true
if (packageName.contains(ruleName, ignoreCase = true)) return true
if (ruleName.equals(appLabel, ignoreCase = true)) return true
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

#### 2.4.2 Time Parsing (inline v RuleEnforcer)

**Nalezeno v:**
- `RuleEnforcer.kt` (řádky 197-218)

**Problém:** Inline time parsing logika

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

#### 2.4.3 App Name Resolution (2x duplicitní)

**Nalezeno v:**
- `AppDetectorService.kt` (implicitně v isWhitelisted)
- `RuleEnforcer.kt` (řádky 64-72)
- `UsageTracker.kt` (řádky 142-150)

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

### 2.5 Tight Coupling

**Problém:** Services jsou příliš propojené

**Aktuální coupling:**
```
AppDetectorService
├── RuleEnforcer
├── BlockOverlayManager
├── UsageTracker
│   ├── RuleEnforcer (cyklická závislost!)
│   └── BlockOverlayManager
├── Reporter
└── ContentScanner

UsageTracker
├── RuleEnforcer (cyklická závislost s AppDetectorService)
└── BlockOverlayManager
```

**Řešení:** Zavést PolicyEngine jako centrální orchestrátor

```
AppDetectorService
└── PolicyEngine
    ├── AppBlockPolicy
    ├── SchedulePolicy
    ├── LimitPolicy
    └── DeviceLockPolicy

UsageTracker
└── PolicyEngine (stejná instance, žádná cyklická závislost)
```

---

### 2.6 Magic Numbers

**Nalezeno:**
- `delay(30_000)` - RULE_FETCH_INTERVAL_MS
- `delay(5000)` - USAGE_TRACK_INTERVAL_MS
- `delay(1000)` - SCREENSHOT_DELAY_MS
- `delay(30000)` - SYNC_INTERVAL_MS

**Řešení:**
```kotlin
// config/AgentConstants.kt
object AgentConstants {
    const val RULE_FETCH_INTERVAL_MS = 30_000L
    const val USAGE_TRACK_INTERVAL_MS = 5_000L
    const val SCREENSHOT_DELAY_MS = 1_000L
    const val SYNC_INTERVAL_MS = 30_000L
    const val HEARTBEAT_INTERVAL_MS = 30_000L
}
```

---

## 3. Navržená Nová Architektura

### 3.1 Nová Struktura Projektu

```
clients/android/app/src/main/java/com/familyeye/agent/
├── data/
│   ├── api/
│   ├── local/
│   └── repository/
│
├── di/
│
├── policy/                    # NOVÉ - Policy engine
│   ├── PolicyEngine.kt
│   ├── AppBlockPolicy.kt
│   ├── SchedulePolicy.kt
│   ├── LimitPolicy.kt
│   └── DeviceLockPolicy.kt
│
├── enforcement/               # NOVÉ - Enforcement layer
│   ├── EnforcementService.kt
│   └── WhitelistManager.kt
│
├── utils/                     # NOVÉ - Utilities
│   ├── PackageMatcher.kt
│   ├── TimeUtils.kt
│   ├── AppInfoResolver.kt
│   └── LauncherDetector.kt
│
├── config/                    # NOVÉ - Configuration
│   └── AgentConstants.kt
│
├── receiver/
├── scanner/
│
├── service/                   # REFAKTOROVANÉ
│   ├── AppDetectorService.kt (zmenšený)
│   ├── FamilyEyeService.kt
│   ├── UsageTracker.kt
│   ├── Reporter.kt
│   └── BlockOverlayManager.kt
│
└── ui/
    ├── screens/
    │   ├── setup/             # NOVÉ - Setup wizard rozdělen
    │   │   ├── SetupWizardScreen.kt
    │   │   └── steps/
    │   └── ...
    └── ...
```

### 3.2 Nový Dependency Graph

```
FamilyEyeService
├── AgentConfigRepository
├── UsageTracker
│   └── PolicyEngine (NO cyklická závislost)
├── Reporter
├── PolicyEngine
└── WebSocketClient

AppDetectorService
├── PolicyEngine (centrální orchestrátor)
└── EnforcementService
    └── BlockOverlayManager

PolicyEngine
├── AppBlockPolicy
│   └── PackageMatcher (utility)
├── SchedulePolicy
│   └── TimeUtils (utility)
├── LimitPolicy
│   └── TimeUtils (utility)
└── DeviceLockPolicy

UsageTracker
├── PolicyEngine (stejná instance)
└── EnforcementService
```

**Výhody:**
- ✅ Žádné cyklické závislosti
- ✅ Jasná separace concerns
- ✅ Testovatelné komponenty
- ✅ Snadná údržba

---

## 4. Detailní Refactoring Plán

### Fáze 1: Utilities a Constants (Týden 1-2)

**Cíl:** Vytvořit utility třídy a konstanty, odstranit duplicity

#### Krok 1.1: Vytvořit utils/ package

**Soubory k vytvoření:**
1. `utils/PackageMatcher.kt` (~30 řádků)
2. `utils/TimeUtils.kt` (~60 řádků)
3. `utils/AppInfoResolver.kt` (~30 řádků)
4. `utils/LauncherDetector.kt` (~20 řádků)
5. `config/AgentConstants.kt` (~20 řádků)

**Migrace:**
- Nahradit duplicitní kód v `AppDetectorService.kt`
- Nahradit duplicitní kód v `RuleEnforcer.kt`
- Nahradit duplicitní kód v `UsageTracker.kt`

**Testování:**
- Unit testy pro každou utility třídu
- Ověřit, že všechny existující testy projdou

---

### Fáze 2: Policy Engine (Týden 3-4)

**Cíl:** Rozdělit RuleEnforcer na Policy Engine s jednotlivými policy třídami

#### Krok 2.1: Vytvořit policy/ package

**Soubory k vytvoření:**
1. `policy/PolicyEngine.kt` (~120 řádků)
   - Orchestrátor pro všechny policy checks
   - `evaluatePolicy(packageName, context) -> PolicyResult`
   
2. `policy/AppBlockPolicy.kt` (~60 řádků)
   - `isBlocked(packageName, rules) -> Boolean`
   - Používá PackageMatcher
   
3. `policy/SchedulePolicy.kt` (~60 řádků)
   - `isDeviceScheduleBlocked(rules) -> Boolean`
   - `isAppScheduleBlocked(packageName, rules) -> Boolean`
   - Používá TimeUtils
   
4. `policy/LimitPolicy.kt` (~50 řádků)
   - `isDailyLimitExceeded(totalUsage, rules) -> Boolean`
   - `isAppTimeLimitExceeded(packageName, usage, rules) -> Boolean`
   
5. `policy/DeviceLockPolicy.kt` (~40 řádků)
   - `isLocked(rules) -> Boolean`

#### Krok 2.2: Refaktorovat RuleEnforcer

**Strategie:**
1. Vytvořit nové policy třídy
2. Upravit RuleEnforcer, aby používal PolicyEngine
3. Postupně migrovat volání z AppDetectorService a UsageTracker
4. Otestovat
5. Odstranit starý RuleEnforcer (nebo ho nechat jako wrapper pro kompatibilitu)

**Migrační kód:**
```kotlin
// Dočasný wrapper pro kompatibilitu
@Singleton
class RuleEnforcer @Inject constructor(
    private val policyEngine: PolicyEngine
) {
    fun isAppBlocked(packageName: String): Boolean {
        return policyEngine.evaluatePolicy(packageName).isBlocked
    }
    
    // ... další wrapper metody
}
```

---

### Fáze 3: Enforcement Layer (Týden 5-6)

**Cíl:** Vytvořit enforcement layer a refaktorovat AppDetectorService

#### Krok 3.1: Vytvořit enforcement/ package

**Soubory k vytvoření:**
1. `enforcement/EnforcementService.kt` (~80 řádků)
   - `enforceBlock(packageName, blockType)`
   - Orchestrace blokování (HOME action + overlay)
   
2. `enforcement/WhitelistManager.kt` (~30 řádků)
   - `isWhitelisted(packageName) -> Boolean`
   - Centralizovaná whitelist logika

#### Krok 3.2: Refaktorovat AppDetectorService

**Před refactoringem (310 řádků):**
```kotlin
class AppDetectorService : AccessibilityService() {
    @Inject lateinit var ruleEnforcer: RuleEnforcer
    @Inject lateinit var blockOverlayManager: BlockOverlayManager
    
    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        // 200+ řádků logiky
    }
    
    private fun isWhitelisted(...) { ... }
    private fun blockApp(...) { ... }
    private fun isLauncher(...) { ... }
}
```

**Po refactoringu (~80 řádků):**
```kotlin
class AppDetectorService : AccessibilityService() {
    @Inject lateinit var policyEngine: PolicyEngine
    @Inject lateinit var enforcementService: EnforcementService
    @Inject lateinit var whitelistManager: WhitelistManager
    
    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        val packageName = event?.packageName?.toString() ?: return
        
        // Update global state
        currentPackage = packageName
        
        // Skip self
        if (packageName == this.packageName) return
        
        // Evaluate policy
        val policyResult = policyEngine.evaluatePolicy(
            packageName = packageName,
            context = PolicyContext(
                currentUsage = usageTracker.getUsageToday(packageName),
                totalUsage = usageTracker.getTotalUsageToday()
            )
        )
        
        // Enforce if needed
        if (policyResult.shouldBlock && !whitelistManager.isWhitelisted(packageName)) {
            enforcementService.enforceBlock(packageName, policyResult.blockType)
        }
        
        // Smart Shield trigger
        if (::contentScanner.isInitialized) {
            contentScanner.processScreen(rootInActiveWindow, packageName)
        }
    }
}
```

---

### Fáze 4: UI Refactoring (Týden 7-8)

**Cíl:** Rozdělit SetupWizardScreen na menší komponenty

#### Krok 4.1: Vytvořit ui/screens/setup/ strukturu

**Soubory k vytvoření:**
1. `ui/screens/setup/SetupWizardScreen.kt` (~100 řádků)
   - Orchestrátor, step navigation
   
2. `ui/screens/setup/steps/WelcomeStep.kt` (~80 řádků)
3. `ui/screens/setup/steps/PinSetupStep.kt` (~100 řádků)
4. `ui/screens/setup/steps/PermissionsStep.kt` (~150 řádků)
5. `ui/screens/setup/steps/PairingStep.kt` (~50 řádků)
6. `ui/screens/setup/steps/CompleteStep.kt` (~50 řádků)

#### Krok 4.2: Refaktorovat SetupWizardScreen

**Strategie:**
1. Vytvořit jednotlivé step komponenty
2. Upravit SetupWizardScreen, aby používal step komponenty
3. Přesunout business logiku do ViewModel
4. Otestovat každý step samostatně

---

## 5. Implementační Detaily

### 5.1 PolicyEngine.kt - Detailní Návrh

```kotlin
@Singleton
class PolicyEngine @Inject constructor(
    private val appBlockPolicy: AppBlockPolicy,
    private val schedulePolicy: SchedulePolicy,
    private val limitPolicy: LimitPolicy,
    private val deviceLockPolicy: DeviceLockPolicy,
    private val ruleRepository: RuleRepository
) {
    private val cachedRules: Flow<List<RuleDTO>> = ruleRepository.getRules()
    
    suspend fun evaluatePolicy(
        packageName: String,
        context: PolicyContext
    ): PolicyResult {
        val rules = cachedRules.first()
        
        // Priority 1: Device Lock (highest)
        if (deviceLockPolicy.isLocked(rules)) {
            return PolicyResult(
                shouldBlock = true,
                blockType = BlockType.DEVICE_LOCK
            )
        }
        
        // Priority 2: App Block
        if (appBlockPolicy.isBlocked(packageName, rules)) {
            return PolicyResult(
                shouldBlock = true,
                blockType = BlockType.APP_FORBIDDEN
            )
        }
        
        // Priority 3: Device Schedule
        if (schedulePolicy.isDeviceScheduleBlocked(rules)) {
            val rule = schedulePolicy.getActiveDeviceScheduleRule(rules)
            return PolicyResult(
                shouldBlock = true,
                blockType = BlockType.DEVICE_SCHEDULE,
                scheduleInfo = rule?.let { "${it.scheduleStartTime} - ${it.scheduleEndTime}" }
            )
        }
        
        // Priority 4: App Schedule
        if (schedulePolicy.isAppScheduleBlocked(packageName, rules)) {
            val rule = schedulePolicy.getActiveAppScheduleRule(packageName, rules)
            return PolicyResult(
                shouldBlock = true,
                blockType = BlockType.APP_SCHEDULE,
                scheduleInfo = rule?.let { "${it.scheduleStartTime} - ${it.scheduleEndTime}" }
            )
        }
        
        // Priority 5: Daily Limit (async check)
        if (limitPolicy.isDailyLimitExceeded(context.totalUsage, rules)) {
            return PolicyResult(
                shouldBlock = true,
                blockType = BlockType.DEVICE_LIMIT
            )
        }
        
        // Priority 6: App Time Limit (async check)
        if (limitPolicy.isAppTimeLimitExceeded(
            packageName,
            context.appUsage,
            rules
        )) {
            return PolicyResult(
                shouldBlock = true,
                blockType = BlockType.APP_LIMIT
            )
        }
        
        return PolicyResult(shouldBlock = false)
    }
}

data class PolicyContext(
    val appUsage: Int,
    val totalUsage: Int
)

data class PolicyResult(
    val shouldBlock: Boolean,
    val blockType: BlockType = BlockType.GENERIC,
    val scheduleInfo: String? = null
)
```

### 5.2 EnforcementService.kt - Detailní Návrh

```kotlin
@Singleton
class EnforcementService @Inject constructor(
    private val blockOverlayManager: BlockOverlayManager
) {
    fun enforceBlock(
        packageName: String,
        blockType: BlockType,
        scheduleInfo: String? = null
    ) {
        Timber.w("Enforcing block: $packageName ($blockType)")
        
        // 1. Send HOME action
        performGlobalAction(GLOBAL_ACTION_HOME)
        
        // 2. Show overlay
        blockOverlayManager.show(packageName, blockType, scheduleInfo)
    }
    
    private fun performGlobalAction(action: Int) {
        // Note: This needs to be called from AccessibilityService context
        // EnforcementService should receive a callback or use a different approach
        // For now, we'll pass the action through BlockOverlayManager
    }
}
```

**Poznámka:** `performGlobalAction` vyžaduje AccessibilityService context. Možná řešení:
1. Předat callback z AppDetectorService
2. Použít EventBus/Flow pro komunikaci
3. Nechat AppDetectorService volat performGlobalAction přímo

---

## 6. Migrační Strategie

### 6.1 Backward Compatibility

**Problém:** Během refactoringu musí aplikace zůstat funkční.

**Řešení:**
1. **Wrapper třídy:** Nechat staré třídy jako wrappery
2. **Postupná migrace:** Migrovat jeden modul po druhém
3. **Feature flags:** Použít feature flags pro novou/starou logiku

**Příklad wrapperu:**
```kotlin
// Dočasný wrapper - odstranit po migraci
@Singleton
class RuleEnforcer @Inject constructor(
    private val policyEngine: PolicyEngine
) {
    @Deprecated("Use PolicyEngine directly")
    fun isAppBlocked(packageName: String): Boolean {
        return runBlocking {
            policyEngine.evaluatePolicy(
                packageName = packageName,
                context = PolicyContext(0, 0)
            ).shouldBlock
        }
    }
    
    // ... další wrapper metody
}
```

### 6.2 Testování

**Strategie:**
1. **Unit testy:** Pro každou novou třídu
2. **Integration testy:** Pro PolicyEngine
3. **E2E testy:** Pro celý flow
4. **Regression testy:** Ověřit, že nic nefunguje hůř

**Test coverage cíl:**
- Policy třídy: 80%+
- Utilities: 90%+
- Enforcement: 70%+

---

## 7. Rizika a Mitigace

### 7.1 Rizika

1. **Breaking changes:** Refactoring může způsobit regrese
   - **Mitigace:** Postupná migrace, rozsáhlé testování

2. **Performance:** Nová architektura může být pomalejší
   - **Mitigace:** Profiling, benchmarky před/po

3. **Čas:** Refactoring může trvat déle než očekáváno
   - **Mitigace:** Realistický plán, buffer čas

4. **Kompatibilita:** Nová architektura může být nekompatibilní
   - **Mitigace:** Wrapper třídy, postupná migrace

### 7.2 Rollback Plán

**Pokud se něco pokazí:**
1. Vrátit se na předchozí commit
2. Použít feature flag pro starou logiku
3. Postupně opravit problémy v nové architektuře

---

## 8. Metriky Úspěchu

### 8.1 Před Refactoringem

- **AppDetectorService:** 310 řádků, 8 zodpovědností
- **RuleEnforcer:** 218 řádků, 9 metod
- **SetupWizardScreen:** 536 řádků, 5 kroků
- **Duplicity:** 3x package matching, 2x time parsing
- **Cyclomatic complexity:** Vysoká (hluboké vnoření)
- **Test coverage:** ~30%

### 8.2 Po Refactoringu (Cíle)

- **AppDetectorService:** ~80 řádků, 1 zodpovědnost
- **Policy třídy:** ~40-60 řádků každá, 1 zodpovědnost
- **SetupWizardScreen:** ~100 řádků, orchestrátor
- **Duplicity:** 0x (vše v utilities)
- **Cyclomatic complexity:** Nízká (flat structure)
- **Test coverage:** 70%+

---

## 9. Časový Plán

### Týden 1-2: Utilities a Constants
- ✅ Vytvořit utils/ package
- ✅ Vytvořit config/AgentConstants.kt
- ✅ Nahradit duplicity
- ✅ Unit testy

### Týden 3-4: Policy Engine
- ✅ Vytvořit policy/ package
- ✅ Refaktorovat RuleEnforcer
- ✅ Migrovat AppDetectorService a UsageTracker
- ✅ Integration testy

### Týden 5-6: Enforcement Layer
- ✅ Vytvořit enforcement/ package
- ✅ Refaktorovat AppDetectorService
- ✅ E2E testy

### Týden 7-8: UI Refactoring
- ✅ Rozdělit SetupWizardScreen
- ✅ UI testy
- ✅ Finalizace

**Celkem: 6-8 týdnů**

---

## 10. Závěr

Tento refactoring plán poskytuje:
- ✅ Jasnou strukturu nové architektury
- ✅ Konkrétní kroky implementace
- ✅ Migrační strategii
- ✅ Rizika a mitigace
- ✅ Metriky úspěchu

**Doporučení:**
1. Začít s Fází 1 (Utilities) - nejméně riziková
2. Postupně pokračovat fázemi 2-4
3. Pravidelně testovat a reviewovat
4. Dokumentovat změny

**Očekávané výsledky:**
- ✅ Lepší testovatelnost
- ✅ Snadnější údržba
- ✅ Menší kognitivní zátěž
- ✅ Možnost paralelního vývoje

---

**Konec dokumentu**
