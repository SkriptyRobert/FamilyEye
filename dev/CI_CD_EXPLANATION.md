# CI/CD Workflow Explanation
**Date:** 2026-01-26

---

## 🎯 JAK TO FUNGUJE

### **Workflow: `.github/workflows/tests.yml`**

#### **Kdy se spustí:**
1. ✅ **Při každém push** do main/master/android-fix-process
2. ✅ **Při každém Pull Request** (PR)
3. ✅ **Automaticky** - bez zásahu člověka

#### **Co dělá:**
1. **Backend Tests:**
   - Spustí `pytest backend/tests/`
   - Zkontroluje, že všechny testy projdou
   - Pokud test selže → PR se NEMŮŽE mergnout ❌

2. **Android Tests:**
   - Spustí `./gradlew test`
   - Zkontroluje unit testy
   - Pokud test selže → PR se NEMŮŽE mergnout ❌

3. **Frontend Tests:**
   - Spustí `npm test`
   - Zkontroluje React testy
   - Pokud test selže → PR se NEMŮŽE mergnout ❌

#### **Výsledek:**
- ✅ **Všechny testy projdou** → PR může být mergnut
- ❌ **Jakýkoliv test selže** → PR se NEMŮŽE mergnut (ochrana!)

---

## 🚀 AUTOMATICKÝ RELEASE

### **Workflow: `.github/workflows/release.yml`**

#### **Kdy se spustí:**
- ✅ **AUTOMATICKY** po úspěšném dokončení testů
- ✅ **Pouze** pokud všechny testy projdou
- ✅ **Pouze** na main/master branch

#### **Co dělá:**
1. Zkontroluje, že všechny testy prošly ✅
2. Vytvoří **GitHub Release** s tagem
3. Tag = verze z `build.gradle.kts` (např. `v1.0.26`)

#### **Výsledek:**
- ✅ **Automatický release** po úspěšných testech
- ✅ **Jistota**, že release obsahuje pouze funkční kód
- ✅ **Historie verzí** automaticky vytvářená

---

## 📋 PRAKTICKÝ PŘÍKLAD

### **Scénář: Contributor vytvoří PR**

1. **Contributor:**
   - Forkne repozitář
   - Udělá změny v kódu
   - Vytvoří Pull Request

2. **GitHub Actions (automaticky):**
   ```
   → Spustí backend testy
   → Spustí Android testy  
   → Spustí frontend testy
   ```

3. **Výsledek:**
   - ✅ **Testy projdou** → PR může být mergnut
   - ❌ **Test selže** → PR se NEMŮŽE mergnut (červený ❌)

4. **Po merge do main:**
   ```
   → Testy se znovu spustí
   → Pokud projdou → Automatický release v1.0.27
   ```

---

## ✅ CO TO ZAJIŠŤUJE

### **1. Ochrana před rozbitím:**
- ❌ Pokud někdo pošle kód, který rozbije testy → PR se NEMŮŽE mergnut
- ✅ Pouze kód, který projde testy, může být mergnut

### **2. Automatické testování:**
- ✅ Nemusíte manuálně spouštět testy
- ✅ GitHub to udělá automaticky při každém PR

### **3. Automatické release:**
- ✅ Po úspěšných testech se automaticky vytvoří release
- ✅ Jistota, že release obsahuje pouze funkční kód

### **4. Historie verzí:**
- ✅ Každý release má tag (v1.0.26, v1.0.27, atd.)
- ✅ Snadné rollback, pokud je potřeba

---

## 🔧 CO POTŘEBUJETE

### **1. Testy napsané:**
- ✅ Backend testy v `backend/tests/`
- ✅ Android testy v `clients/android/app/src/test/`
- ✅ Frontend testy (pokud máte)

### **2. GitHub Actions workflow:**
- ✅ `.github/workflows/tests.yml` - **VYTVOŘENO!**
- ✅ `.github/workflows/release.yml` - **VYTVOŘENO!**

### **3. conftest.py pro backend:**
- ✅ `backend/tests/conftest.py` - **VYTVOŘENO!**

---

## 📝 JAK TO NASTAVIT

### **1. Commit a push:**
```bash
git add .github/workflows/
git add backend/tests/conftest.py
git commit -m "feat: Add CI/CD workflows for automated testing"
git push
```

### **2. GitHub automaticky:**
- ✅ Rozpozná workflow soubory
- ✅ Začne je používat při PR

### **3. Testování:**
- Vytvořte test PR
- GitHub automaticky spustí testy
- Uvidíte výsledky v PR

---

## 🎓 CO TO ZNAMENÁ PRO CONTRIBUTING

### **Pro contributora:**
1. **Udělá změny** v kódu
2. **Vytvoří PR**
3. **GitHub automaticky:**
   - Spustí testy
   - Zobrazí výsledky v PR
4. **Pokud testy selžou:**
   - ❌ PR se NEMŮŽE mergnut
   - Contributor musí opravit testy
5. **Pokud testy projdou:**
   - ✅ PR může být mergnut
   - ✅ Po merge → automatický release

### **Pro vás (maintainer):**
- ✅ **Nemusíte manuálně testovat** - GitHub to udělá
- ✅ **Jistota**, že merged kód je funkční
- ✅ **Automatické release** po úspěšných testech

---

## 💡 VÝHODY

### **1. Bezpečnost:**
- ❌ Nelze mergnout kód, který rozbije testy
- ✅ Pouze funkční kód může být mergnut

### **2. Automatizace:**
- ✅ Nemusíte manuálně spouštět testy
- ✅ Automatické release po úspěšných testech

### **3. Profesionalita:**
- ✅ Ukazuje, že projekt má testy
- ✅ Ukazuje, že testy jsou automatizované
- ✅ Důvěryhodnost pro contributory

---

## ✅ ZÁVĚR

**Ano, přesně tak to funguje!**

1. ✅ **Testy se spustí automaticky** při každém PR
2. ✅ **Pokud testy projdou** → PR může být mergnut
3. ✅ **Pokud testy selžou** → PR se NEMŮŽE mergnut
4. ✅ **Po úspěšném merge** → automatický release

**Vytvořil jsem:**
- ✅ `.github/workflows/tests.yml` - automatické testování
- ✅ `.github/workflows/release.yml` - automatický release
- ✅ `backend/tests/conftest.py` - test fixtures

**Teď stačí commitnout a pushnout - GitHub to začne používat automaticky!** 🚀
