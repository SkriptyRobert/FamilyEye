# Testy - Souhrn vytvořených testů
**Date:** 2026-01-26

---

## ✅ VYTVOŘENÉ TESTY

### **Android Unit Tests** (`src/test/java/`)

#### 1. **UsageTrackerTest.kt** ⭐ **KRITICKÉ**
**Umístění:** `clients/android/app/src/test/java/com/familyeye/agent/service/UsageTrackerTest.kt`

**Testuje:**
- ✅ Reset `lastCheckTime` při gapu >60s (prevence phantom usage)
- ✅ Zachování `lastCheckTime` při gapu <60s
- ✅ Přeskakování vlastního package při trackingu
- ✅ Přeskakování trackingu když je obrazovka vypnutá
- ✅ Přeskakování trackingu když je overlay aktivní
- ✅ Zpracování časových skoků (backwards time jump)
- ✅ Kombinování lokálního a remote usage (`getUsageToday`, `getTotalUsageToday`)

**Důvod:** UsageTracker je kritický pro správné počítání času!

---

#### 2. **EnforcementServiceTest.kt** ⭐ **KRITICKÉ**
**Umístění:** `clients/android/app/src/test/java/com/familyeye/agent/enforcement/EnforcementServiceTest.kt`

**Testuje:**
- ✅ Vlastní package je vždy whitelisted
- ✅ Detekce tampering pokusů
- ✅ Device Lock blokuje všechny aplikace
- ✅ Whitelisted aplikace jsou povoleny
- ✅ Blocked aplikace jsou blokovány
- ✅ Device Schedule blokuje aplikace
- ✅ Aplikace které projdou všechny kontroly jsou povoleny

**Důvod:** EnforcementService rozhoduje o blokování - kritické pro bezpečnost!

---

### **Android Instrumented Tests** (`src/androidTest/java/`)

#### 3. **AgentDatabaseTest.kt** ⭐ **KRITICKÉ**
**Umístění:** `clients/android/app/src/androidTest/java/com/familyeye/agent/data/local/AgentDatabaseTest.kt`

**Testuje:**
- ✅ Vložení a načtení UsageLog
- ✅ Výpočet duration pro package (`getUsageDurationForPackage`)
- ✅ Výpočet celkového usage (`getTotalUsageToday`)
- ✅ Vložení a načtení Rule
- ✅ Mazání Rule
- ✅ Filtrování Rules podle app

**Důvod:** Databáze je kritická pro ukládání dat - musí fungovat správně!

---

### **Backend Tests** (`backend/tests/`)

#### 4. **conftest.py** ✅ **INFRASTRUCTURE**
**Umístění:** `backend/tests/conftest.py`

**Obsahuje:**
- ✅ `db_session` fixture - in-memory databáze pro testy
- ✅ `test_user` fixture - testovací uživatel
- ✅ `test_device` fixture - testovací zařízení
- ✅ `override_get_db` fixture - pro FastAPI dependency override

**Důvod:** Sdílené fixtures pro všechny backend testy!

---

#### 5. **test_rules_endpoint.py** ⭐ **KRITICKÉ**
**Umístění:** `backend/tests/test_rules_endpoint.py`

**Testuje:**
- ✅ Agent může fetchovat rules (`/api/rules/agent/fetch`)
- ✅ Invalid API key vrací 401
- ✅ Správný výpočet `daily_usage` a `usage_by_app`

**Důvod:** Rules endpoint je kritický - agent z něj získává pravidla!

---

#### 6. **test_stats_service.py** ✅ **DŮLEŽITÉ**
**Umístění:** `backend/tests/test_stats_service.py`

**Testuje:**
- ✅ `calculate_day_usage_minutes` - počítá unikátní minuty (ne součet)
- ✅ `get_app_day_duration` - správně sčítá duration
- ✅ `get_activity_boundaries` - vrací první a poslední čas

**Důvod:** Stats service počítá statistiky - musí být přesné!

---

#### 7. **test_pairing.py** ✅ **ROZŠÍŘENO**
**Umístění:** `backend/tests/test_pairing.py`

**Přidáno:**
- ✅ `test_generate_pairing_token_with_db_session` - test s reálnou databází

**Důvod:** Pairing je kritické pro připojení zařízení!

---

## 🔧 GITHUB ACTIONS WORKFLOWS

### **1. tests.yml** ✅ **VYTVOŘENO A DOPLNĚNO**
**Umístění:** `.github/workflows/tests.yml`

**Obsahuje:**
- ✅ Backend tests job
- ✅ Android unit tests job
- ✅ Android instrumented tests job (nově přidáno)
- ✅ Frontend tests job
- ✅ Test summary job

**Vylepšení:**
- ✅ Přidán `--cov-report=xml` pro coverage
- ✅ Přidány environment variables
- ✅ `continue-on-error: true` pro instrumented testy (vyžadují emulator)

---

### **2. release.yml** ✅ **VYTVOŘENO**
**Umístění:** `.github/workflows/release.yml`

**Funkce:**
- ✅ Automaticky vytvoří release po úspěšných testech
- ✅ Tag = verze z `build.gradle.kts`
- ✅ Pouze na main/master branch
- ✅ Pouze pokud všechny testy projdou

---

## 📊 TEST COVERAGE

### **Před:**
- Android: 5 testů (238 LOC)
- Backend: 4 testy
- Frontend: 1 test
- **Celkem:** ~10 testů

### **Po:**
- Android: **8 testů** (+3 nové)
  - UsageTrackerTest.kt (8 testů)
  - EnforcementServiceTest.kt (7 testů)
  - AgentDatabaseTest.kt (6 instrumented testů)
- Backend: **7 testů** (+3 nové)
  - test_rules_endpoint.py (3 testy)
  - test_stats_service.py (3 testy)
  - test_pairing.py (rozšířeno)
- Frontend: 1 test (beze změny)
- **Celkem:** ~16 testů (+6 nových)

---

## ✅ CO JE OCHRÁNĚNO

### **Kritické funkce:**
1. ✅ **Time tracking** - UsageTrackerTest.kt
2. ✅ **Enforcement/Blocking** - EnforcementServiceTest.kt
3. ✅ **Database operations** - AgentDatabaseTest.kt
4. ✅ **Rules fetching** - test_rules_endpoint.py
5. ✅ **Stats calculation** - test_stats_service.py
6. ✅ **Pairing** - test_pairing.py

### **Co ještě chybí (nízká priorita):**
- Repository testy (AgentConfigRepository, RuleRepository)
- ViewModel testy
- Frontend component testy
- Integration testy

---

## 🚀 JAK TO FUNGUJE

### **Při každém PR:**
1. GitHub automaticky spustí všechny testy
2. Pokud test selže → PR se NEMŮŽE mergnut ❌
3. Pokud testy projdou → PR může být mergnut ✅

### **Po úspěšném merge:**
1. Testy se znovu spustí
2. Pokud projdou → automatický release 🚀
3. Release má tag podle verze (v1.0.26, v1.0.27, atd.)

---

## 📝 SOUHRN

**Vytvořeno:**
- ✅ 3 nové Android testy (UsageTracker, EnforcementService, Database)
- ✅ 3 nové Backend testy (rules endpoint, stats service, pairing)
- ✅ conftest.py pro sdílené fixtures
- ✅ GitHub Actions workflows (tests.yml, release.yml)
- ✅ Room testing dependency přidána

**Ochrana:**
- ✅ Kritické funkce jsou testovány
- ✅ Automatické testování při každém PR
- ✅ Automatický release po úspěšných testech

**Stav:** ✅ **PŘIPRAVENO PRO VEŘEJNÝ REPOZITÁŘ!**
