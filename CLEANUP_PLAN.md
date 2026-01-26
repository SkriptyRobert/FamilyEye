# Systematický audit projektu - Detailní plán čištění

## Metodika

Projít každou složku soubor po souboru a kategorizovat:

1. **ESSENTIAL** - Kritický produkční kód (ZACHOVAT)
2. **TEST** - Testovací soubory (ZACHOVAT)
3. **BUILD_ARTIFACT** - Generované soubory (ODSTRANIT)
4. **UTILITY** - Jednorázové utility (HODNOTIT)
5. **MIGRATION** - Migrační skripty (HODNOTIT - ponechat jako dokumentaci)
6. **DUPLICATE** - Duplicitní soubory (ODSTRANIT starší)
7. **DOCUMENTATION** - Dokumentace (ZACHOVAT, ale opravit chyby)
8. **LOG_FILES** - Log soubory (ODSTRANIT)
9. **TEMP_FILES** - Dočasné soubory (ODSTRANIT)
10. **CONFIG_TEMPLATE** - Konfigurační šablony (ZACHOVAT)

## ⚠️ VYNECHANÉ SLOŽKY (NEDOTÝKAT SE)

- `/dev` - Vývojářské poznámky (vynechat podle požadavku)
- `/installer` - Instalátory (NEDOTÝKAT SE - kritické!)
- `/.github` - CI/CD workflows (ZACHOVAT)
- `/certs` - SSL certifikáty (ZACHOVAT - mohou být generované)

## Root level

### ESSENTIAL - ZACHOVAT
- `.env.example` ✅
- `.gitignore` ✅
- `.cursorrules` ✅
- `LICENSE`, `LICENSE_IMAGES` ✅
- `README.md`, `README_CZ.md` ✅
- `SECURITY.md`, `SECURITY_CZ.md` ✅
- `CONTRIBUTING.md`, `CONTRIBUTING_CZ.md` ✅
- `TESTS_OVERVIEW.md` ✅

## Backend (`backend/`)

### Produkční kód - ZACHOVAT
- `app/` - celá složka ✅
- `requirements.txt` ✅
- `pytest.ini` ✅
- `run_https.py` ✅
- `service_wrapper.py` ✅

### Testy - ZACHOVAT
- `tests/` - celá složka ✅

### Migrační skripty - HODNOTIT
- `migrate_db_uptime.py` - jednorázový, NENÍ importován ✅ (ponechat jako dokumentaci)
- `update_db.py` - jednorázový, NENÍ importován ✅ (ponechat jako dokumentaci)

## Frontend (`frontend/`)

### Produkční kód - ZACHOVAT
- `src/` - celá složka ✅
- `public/` ✅
- `index.html` ✅
- `package.json`, `package-lock.json` ✅
- `vite.config.js` ✅
- `vitest.config.js` ✅
- `service_wrapper.py` ✅

### Testy - ZACHOVAT
- `src/components/DeviceOwnerSetup.test.jsx` ✅
- `src/test/setup.js` ✅

## Clients

### Windows Agent (`clients/windows/`)
- `agent/` - celá složka ✅
- `child_agent.py` ✅
- `README.md` ✅
- `requirements.txt` ✅

### Android (`clients/android/`)
- Celá složka ✅ (kromě log souborů - viz níže)

## Installer (`installer/`)

### ⚠️ NEDOTÝKAT SE - KRITICKÉ
- `agent/` - celá složka ✅
- `server/` - celá složka ✅
- `README.md` ✅

## Dokumentace (`docs/`)

### ZACHOVAT - Všechny soubory
- Všechny `.md` soubory ✅
- `assets/` ✅

## Log soubory - K ODSTRAŇOVÁNÍ

### Android log soubory (`clients/android/`)
- `test_log.txt` ❌
- `build_log*.txt` (všechny) ❌
- `compile_errors*.txt` (všechny) ❌
- `gradle_error*.txt` (všechny) ❌
- `debug_logs.txt` ❌
- `build_out.txt` ❌
- `accessibility_logs.txt` ❌
- `familyeye_logs.txt` ❌
- `raw_logs.txt` ❌
- `full_logs.txt` ❌
- `device_logs.txt` ❌
- `compile_log.txt` ❌
- `build_v107.txt` ❌
- `build_error_v106.txt` ❌
- `build_fix.txt` ❌
- `build_diag.txt` ❌
- `build_error*.txt` (všechny) ❌
- `physical_device_log.txt` ❌
- `build_log_utf8.txt` ❌
- `build_log_harden*.txt` (všechny) ❌

### Android test logy (`clients/android/tests/manual/`)
- `manual_test_logs.txt` ❌
- `test2_result_log.txt` ❌

## Konfigurační soubory - HODNOTIT

### Windows Agent runtime config
- `clients/windows/agent/config.json` - runtime config (ZACHOVAT pokud je template) ✅
- `clients/windows/config.json` - template? (ZACHOVAT pokud je template) ✅
- `clients/windows/agent/report_queue.json` - runtime data? (ODSTRANIT pokud je runtime) ❌
- `clients/windows/agent/usage_cache.json` - runtime data? (ODSTRANIT pokud je runtime) ❌

## Cache soubory - ODSTRAŇOVAT

- `.pytest_cache/` - pytest cache (ODSTRANIT) ❌
- `backend/.pytest_cache/` - pytest cache (ODSTRANIT) ❌

## Akční plán

### Fáze 1: Analýza každého souboru
1. Projít každý soubor v každé složce
2. Zkontrolovat importy a závislosti
3. Ověřit, zda je soubor používán
4. Kategorizovat podle výše uvedených kategorií

### Fáze 2: Bezpečné odstranění
1. Vytvořit seznam souborů k odstranění
2. Ověřit, že nejsou importovány
3. Ověřit, že nejsou zmíněny v dokumentaci (kromě log souborů)
4. Odstranit pouze log soubory a cache soubory

### Fáze 3: Ověření
1. Ověřit, že projekt se stále kompiluje
2. Ověřit, že testy stále běží
3. Ověřit, že instalátory nejsou ovlivněny

## Seznam souborů k odstranění

### ⚠️ DŮLEŽITÉ: Před odstraněním vždy ověřit, že soubor není importován nebo používán!

### Log soubory (Android) - RUNTIME DATA
Tyto soubory jsou generovány při build/test procesu a neměly by být v repo:

- [ ] `clients/android/test_log.txt`
- [ ] `clients/android/build_log.txt`
- [ ] `clients/android/build_log_2.txt`
- [ ] `clients/android/build_log_3.txt`
- [ ] `clients/android/build_log_4.txt`
- [ ] `clients/android/build_log_5.txt`
- [ ] `clients/android/build_log_6.txt`
- [ ] `clients/android/build_log_7.txt`
- [ ] `clients/android/build_log_8.txt`
- [ ] `clients/android/build_log_9.txt`
- [ ] `clients/android/build_log_utf8.txt`
- [ ] `clients/android/build_log_harden.txt`
- [ ] `clients/android/build_log_harden_2.txt`
- [ ] `clients/android/build_v107.txt`
- [ ] `clients/android/build_out.txt`
- [ ] `clients/android/build_fix.txt`
- [ ] `clients/android/build_diag.txt`
- [ ] `clients/android/build_error.txt`
- [ ] `clients/android/build_error_2.txt`
- [ ] `clients/android/build_error_3.txt`
- [ ] `clients/android/build_error_4.txt`
- [ ] `clients/android/build_error_5.txt`
- [ ] `clients/android/build_error_v106.txt`
- [ ] `clients/android/compile_log.txt`
- [ ] `clients/android/compile_errors.txt`
- [ ] `clients/android/compile_errors_3.txt`
- [ ] `clients/android/gradle_error.txt`
- [ ] `clients/android/gradle_error_2.txt`
- [ ] `clients/android/debug_logs.txt`
- [ ] `clients/android/accessibility_logs.txt`
- [ ] `clients/android/familyeye_logs.txt`
- [ ] `clients/android/raw_logs.txt`
- [ ] `clients/android/full_logs.txt`
- [ ] `clients/android/device_logs.txt`
- [ ] `clients/android/physical_device_log.txt`
- [ ] `clients/android/tests/manual/manual_test_logs.txt`
- [ ] `clients/android/tests/manual/test2_result_log.txt`

### Cache soubory - GENEROVANÉ
- [ ] `.pytest_cache/` (celá složka - pokud existuje)
- [ ] `backend/.pytest_cache/` (celá složka - pokud existuje)

### Runtime data - GENEROVANÉ ZA BĚHU
Tyto soubory jsou vytvářeny dynamicky agentem a neměly by být v repo:
- [ ] `clients/windows/agent/report_queue.json` (runtime data - generuje se za běhu)
- [ ] `clients/windows/agent/usage_cache.json` (runtime data - generuje se za běhu)

**POZNÁMKA**: Tyto soubory jsou již v `.gitignore`, ale pokud jsou v repo, měly by být odstraněny.

## ✅ VYKONANÉ ČIŠTĚNÍ

### Odstraněno: 39 souborů

#### Android log soubory (37 souborů)
- ✅ Všechny `build_log*.txt` soubory (12 souborů)
- ✅ Všechny `build_error*.txt` soubory (6 souborů)
- ✅ Všechny `compile_errors*.txt` soubory (2 soubory)
- ✅ Všechny `gradle_error*.txt` soubory (2 soubory)
- ✅ Ostatní log soubory (15 souborů)
- ✅ Test logy z `tests/manual/` (2 soubory)

**Celková velikost**: ~20 MB uvolněného místa

#### Runtime data (2 soubory)
- ✅ `clients/windows/agent/report_queue.json` (runtime data)
- ✅ `clients/windows/agent/usage_cache.json` (runtime data)

### Aktualizováno
- ✅ `.gitignore` - přidány pravidla pro všechny typy log souborů

## Poznámky

- ✅ Všechny změny byly bezpečné - pouze runtime data a log soubory
- ✅ Instalátory (`installer/`) se NEDOTÝKALY
- ✅ Složka `/dev` se VYNECHALA
- ✅ Všechny produkční soubory zůstaly nedotčené
