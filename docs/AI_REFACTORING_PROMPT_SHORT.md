# AI Refactoring Prompt - Android Agent (Krátká Verze)

## Úkol

Jsi Senior Architekt, Senior Programátor, Security Expert a UI/UX Specialista. Máš za úkol refaktorovat, optimalizovat a opravit kritické chyby v Android agentovi projektu FamilyEye podle detailního auditu.

**Přečti si detailní audit:** `ANDROID_AGENT_AUDIT_2025.md`

## Prioritní Úkoly

### 🔴 Priorita 1 - Kritické (Okamžitě):

1. **Refaktorovat AppDetectorService.kt (328 řádků)**
   - Rozdělit na: SelfProtectionHandler, AppBlockingHandler, WhitelistManager, LauncherDetector
   - Zmenšit na ~80 řádků (pouze detekce + delegace)

2. **Refaktorovat RuleEnforcer.kt (206 řádků)**
   - Vytvořit Policy Engine: PolicyEngine, AppBlockPolicy, SchedulePolicy, LimitPolicy, DeviceLockPolicy
   - Vytvořit utilities: PackageMatcher, TimeUtils, AppInfoResolver
   - Odstranit duplicity

3. **Refaktorovat SetupWizardScreen.kt (536 řádků)**
   - Rozdělit na step komponenty: WelcomeStep, PinSetupStep, PermissionsStep, PairingStep, CompleteStep
   - Zmenšit orchestrátor na ~100 řádků

4. **Security Hardening:**
   - PIN hashování: SHA-256 → bcrypt/Argon2
   - Odstranit hardcoded backend URL z build.gradle.kts
   - Opravit SSL trust all certificates v debug módu
   - Nelogovat PIN v plaintext

### 🟡 Priorita 2 - Důležité (1 měsíc):

5. **Odstranit duplicity:**
   - Package matching (3x) → PackageMatcher utility
   - Time parsing (inline) → TimeUtils utility
   - App name resolution → AppInfoResolver utility

6. **Odstranit magic numbers:**
   - Vytvořit `config/AgentConstants.kt`
   - Nahradit všechny `delay()` hodnoty konstantami

7. **Security:**
   - Šifrovat API Key a Device ID (EncryptedSharedPreferences)
   - Přesunout API Key z WebSocket URL do HTTP headeru

## Požadavky

- **Single Responsibility:** Každá třída max 200 řádků (ideálně 50-150)
- **DRY:** Odstranit všechny duplicity
- **Testovatelnost:** Všechny nové třídy musí být testovatelné
- **Bezpečnost:** Opravit všechny kritické security chyby
- **Backward Compatibility:** Aplikace musí zůstat funkční během refactoringu

## Nová Struktura

```
policy/          # Policy Engine (nové)
enforcement/     # Enforcement layer (nové)
utils/           # Utilities (nové)
config/          # Constants (nové)
service/         # Refaktorované services
ui/screens/setup/ # Rozdělené setup screens
```

## Postup

1. **Fáze 1:** Utilities + Constants (začni zde)
2. **Fáze 2:** Policy Engine
3. **Fáze 3:** Enforcement Layer
4. **Fáze 4:** UI Refactoring
5. **Fáze 5:** Security Hardening

**Po každé fázi otestuj funkčnost!**

## Výsledek

- ✅ Všechny soubory pod 200 řádků
- ✅ Žádné duplicity
- ✅ Žádné magic numbers
- ✅ Všechny kritické security chyby opraveny
- ✅ Testovatelné komponenty

**Začni s Fází 1 a postupuj systematicky podle auditu.**
