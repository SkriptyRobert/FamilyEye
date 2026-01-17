## Audit projektu FamilyEye (hloubkový audit: duplicity, lean, refactoring, security pro domácí standalone)

**Datum auditu:** 2026-01-17  
**Rozsah:** backend, frontend, Android agent, Windows agent, instalátor, dokumentace, dev skripty  
**Cíl:** zhodnotit duplicity, nadbytečné/testovací artefakty, spaghetti/refactoring hot-spoty, “lean” stav (jen nutné pro běh) a bezpečnostní rizika ve scénáři domácího standalone provozu

---

## Executive summary

Projekt má celkově rozumně navrženou architekturu (oddělený backend/frontend, agenti zvlášť), ale workspace (a potenciálně i repo) je v praxi **nelean** kvůli přítomnosti velkých build/dev artefaktů a runtime dat. Kódově je největší problém udržovatelnosti **monolitický Windows enforcer** a několik “God-file” hot-spotů v backendu a UI. V bezpečnosti (i pro domácí provoz) jsou největší rizika **defaultní SECRET_KEY**, **veřejné statické servírování screenshotů**, a možnost špatné konfigurace TLS/verify.

**Celkové hodnocení (kvalita/udržovatelnost/lean/security): 6.5/10**  

---

## Metodika a poznámky k měření

- Audit vychází z analýzy stromu souborů, velikostí, seznamu největších souborů, hledání “test/dev/build/log/cache” artefaktů, a identifikace refactoring hot-spotů podle délky souborů.
- Počty řádků níže jsou počítané pro “core” soubory a **nezahrnují** typicky ignorované nebo generované adresáře: `node_modules`, `venv`, `__pycache__`, `build`, `dist`, `.git`. Pokud by byly commitované, reálné LOC i objem by byl výrazně vyšší.

---

## Inventura: co v projektu není “lean” (artefakty, runtime data, testovací věci)

### Největší “nelean” položky podle velikosti (workspace)

Následující položky nejsou nutné pro běh logiky projektu jako takové (jsou to závislosti, buildy, logy, runtime data, release artefakty). Pokud jsou commitované nebo distribuované společně se zdrojáky, zbytečně zvyšují riziko i náklady.

- **`clients/android/app/build/`**: ~302.9 MB (build artefakty, nemají být součástí zdrojáků)
- **`frontend/node_modules/`**: ~112.1 MB (závislosti, nemají být ve zdrojácích)
- **`backend/venv/`**: ~76.0 MB (Python venv, nemá být ve zdrojácích)
- **`installer/agent/output/`**: ~75.0 MB (hotové instalátory, release artefakty, typicky mimo repo)
- **`installer/agent/dist/`**: ~26.0 MB (zkompilované EXE, release artefakty)
- **`installer/agent/build/`**: ~36.8 MB (build artefakty)
- **`backend/uploads/`**: ~2.2 MB (runtime screenshots; v repu navíc výrazný privacy risk)
- **`backend/app.log`**: ~5.3 MB (log soubor; v repu je to citlivé i zbytečné)
- **`parental_control.db`**: ~0.5 MB (runtime DB; nemá být commitovaná)
- **`clients/android/build_log*.txt`**: build logy (nejsou nutné pro běh)

Poznámka: v kořenové `.gitignore` už je velká část těchto věcí uvedena (např. `node_modules/`, `venv/`, `build/`, `dist/`, `output/`, `*.db`, `*.log`). To je správně. Přesto je důležité ověřit, že nic z toho není historicky commitováno, a že při distribuci “source zip” se tyto adresáře nepřibalují.

### Core kód: přibližný objem (bez build/venv/node_modules/dist)

Celkem cca **36 788 řádků** napříč ~181 soubory těchto typů:
- `.py`: 11 859 řádků
- `.kt`: 4 653 řádků
- `.jsx`: 6 996 řádků
- `.js`: 1 285 řádků
- `.css`: 8 956 řádků
- `.json`: 3 039 řádků

Hodnocení: množství kódu je pro funkce projektu přiměřené, ale existuje několik souborů, které jsou zbytečně velké a koncentrují příliš mnoho zodpovědností (viz sekce refactoring).

---

## Duplicity a redundantní části (kód, dokumentace, build/ops soubory)

### Funkční duplicita v backendu

- **`backend/app/services/insights_service.py` vs `backend/app/services/experimental/insights_service.py`**
  - Obsah je prakticky stejný; liší se hlavně komentářem a “EXPERIMENTAL” štítkem.
  - Dopad: zvyšuje mentální zátěž, riziko “opravil jsem to v jednom souboru, ale ne ve druhém”.
  - Doporučení: sjednotit na jednu implementaci (např. ponechat `insights_service.py`, experimental odstranit nebo převést na dokumentační poznámku/testy).

### Duplicity / deriváty v dokumentaci

- **`docs/*.md.resolved`**
  - Typicky jde o pracovní/derivovaný stav dokumentu.
  - Dopad: šum v repu, riziko udržování dvou “pravd”.
  - Doporučení: archivovat mimo repo nebo držet jen jednu canonical verzi.

### Testovací a pomocné skripty, které nejsou nutné pro běh

Tyto soubory jsou užitečné pro vývoj/build, ale nejsou nutné pro runtime:

- **`installer/agent/test.iss`**
  - Testovací instalátor, obsahuje testovací hodnoty (např. hardcoded health URL na localhost) a slabší bezpečnostní nastavení (např. ssl_verify false v generované konfiguraci).
  - Doporučení: jasně oddělit od produkčního instalátoru (`setup_agent.iss`) a nebrat jako “produkční zdroj pravdy”. Pokud se nepoužívá, odstranit.

- **`dev/*.bat`**
  - Dev convenience skripty (start/stop/pair). V pohodě pro interní vývoj, ale pro “lean release source” by měly být buď dokumentované jako dev-only, nebo přesunuté do `tools/` apod.

- **`clients/android/build_log*.txt`**
  - Build logy, nejsou součástí produktu.

### Release/build artefakty přítomné v repu (potenciálně)

- `installer/agent/build/`, `installer/agent/dist/`, `installer/agent/output/`  
  - Doporučení: držet mimo repo nebo v samostatném “releases” úložišti.

### Runtime data soubory přítomné ve stromu

- **`backend/uploads/screenshots/...`**
  - Vysoké privacy riziko, navíc šum pro repo.
  - Doporučení: nikdy necommitovat; zavést retention a přístup přes autentizaci (viz security).

- **`clients/windows/agent/report_queue.json`, `clients/windows/agent/usage_cache.json`**
  - Pravděpodobně runtime cache/queue.
  - Doporučení: necommitovat (mít šablonu nebo vytvářet za běhu).

- **`backend/app.log`**
  - Runtime log soubor, nepatří do repa.

- **`parental_control.db`**
  - Runtime DB, nepatří do repa.

---

## Spaghetti kód a refactoring hot-spoty

Tady je seznam největších souborů v “core” kódu (mimo build/venv/node_modules/dist) a proč jsou kandidáti na refactoring:

### Windows agent

- **`clients/windows/agent/enforcer.py` (~881 řádků)**
  - Indikace “God object”: obsahuje fetch pravidel, time sync, enforcement app bloků, schedule, limity, network block, notifikace, shutdown logiku.
  - Riziko: změny v jedné oblasti rozbíjí jinou, špatná testovatelnost, vysoká kognitivní zátěž.
  - Doporučení refaktoringu (minimální rozdělení):
    - `rules_fetcher.py` (komunikace + caching)
    - `time_provider.py` (trusted time + sync)
    - `enforce_apps.py` (app block + kill)
    - `enforce_limits.py` (time limit, daily limit)
    - `enforce_schedule.py` (schedule logika)
    - `enforce_network.py` (firewall / vpn / proxy)
    - `enforcer.py` pouze orchestrátor a state

- **`clients/windows/agent/monitor.py` (~716 řádků)** a **`clients/windows/agent/network_control.py` (~489 řádků)**
  - Doporučení: zkontrolovat SRP, vytáhnout “rules mapping” a parsery do pomocných modulů, sjednotit datové modely.

### Android agent

- **`clients/android/app/src/main/java/com/familyeye/agent/service/AppDetectorService.kt` (~310 řádků)**
  - `onAccessibilityEvent` řeší současně: detekci app, whitelist, enforcement, overlay, async usage checks, Smart Shield scanning, screenshot flow.
  - Doporučení: rozdělit na “policy engine” (co blokovat) a “effects” (jak blokovat: overlay/home/back, report, screenshot).

- **`clients/android/app/src/main/java/com/familyeye/agent/ui/screens/SetupWizardScreen.kt` (~549 řádků)** a **`PairingScreen.kt` (~342 řádků)**
  - Příznak UI monolitu: hodně logiky v jednom souboru.
  - Doporučení: rozdělit na menší Compose komponenty + ViewModel use-cases.

### Backend

- **`backend/app/api/reports/summary_endpoint.py` (~566 řádků)**, **`backend/app/api/devices.py` (~476 řádků)**, **`backend/app/api/reports/stats_endpoints.py` (~458 řádků)**
  - Častý problém: “endpoint soubory” míchají validaci, business logiku, agregace, formátování odpovědí.
  - Doporučení: přesunout výpočty a agregace do `services/` a v API nechávat jen IO vrstvy.

### Frontend

- **`frontend/src/utils/formatting.js` (~617 řádků)**, **`frontend/src/components/RuleEditor.jsx` (~548 řádků)**, **`Reports.jsx` (~399 řádků)**
  - Doporučení: rozdělit utility podle domén (time/formatting/charts) a komponenty rozřezat na menší “presentational” části.

---

## Lean posouzení: obsahuje projekt “jen to nutné”?

### Co je nutné pro běh (domácí standalone)

- Backend (`backend/app` + requirements + spouštěcí skripty)
- Frontend zdrojáky (`frontend/src`) a buď:
  - build proces (pak `dist` generovat), nebo
  - hotové `frontend/dist` pokud je cílem “single-binary/standalone balík”, kde backend servíruje statický frontend
- Agenti (Android/Windows) zdrojáky

### Co typicky nutné není (a zvyšuje šum i riziko)

- `frontend/node_modules`, `backend/venv` (závislosti, generovat/instalovat)
- `clients/android/app/build`, `installer/agent/build`, `installer/agent/dist`, `installer/agent/output` (build/release)
- runtime data: `backend/uploads/**`, `backend/app.log`, `parental_control.db`, agent cache JSONy
- build logy (`clients/android/build_log*.txt`)
- odvozené doc soubory (`docs/*.resolved`)

Hodnocení: jako “source repo” to zatím nepůsobí lean (ve workspace je hodně generovaných věcí). Na úrovni architektury je ale možné projekt snadno “zleanovat” hlavně úklidem artefaktů a jasnou separací build vs runtime.

---

## Security pro domácí standalone použití: rizika a proč

### Threat model (domácí)

I když je cílem “domácí standalone”, typické reálné hrozby jsou:
- dítě má lokální přístup k počítači/telefonu (pokusy o bypass)
- další zařízení v domácí LAN (návštěvy, nezabezpečené Wi-Fi)
- škodlivý web/rozšíření v prohlížeči rodiče (dashboard) nebo dítěte
- chybné vystavení backendu do internetu (port forwarding, veřejná IP, cloud)

### Rizika identifikovaná v projektu

#### Vysoká závažnost (i doma)

- **Defaultní `SECRET_KEY` v backendu**
  - Pokud zůstane default, útočník může snadněji falšovat JWT nebo narušit autentizaci (záleží na přesné implementaci tokenů).
  - Doma je to pořád vysoké riziko, protože kompromitace backendu nebo únik tokenu je reálný scénář.

- **Veřejné statické servírování uploadů**
  - Backend mountuje `uploads/` jako statické soubory (`/static/uploads/...`), tedy screenshoty jsou dostupné bez dodatečné autorizace na úrovni web serveru.
  - Proč je to problém doma: pokud je backend dostupný v LAN, kdokoliv v LAN může zkusit stahovat soubory, a URL screenshotu se může objevit v logách/UI/API.

#### Střední závažnost (záleží na nasazení)

- **CORS nastavené na `*`**
  - Pokud API používá jen bearer tokeny a nejsou cookies, CORS samo o sobě nezpůsobí průnik bez tokenu.
  - Proč je to pořád riziko: zbytečně to rozšiřuje “browser attack surface” (při XSS nebo úniku tokenu) a je to špatný default pro situace, kdy se backend omylem vystaví mimo LAN.

- **TLS/verify režim a self-signed certy**
  - V testovacím instalátoru je naznačen režim “akceptuj self-signed” a konfigurace `ssl_verify: false`.
  - Doma: MITM přes kompromitovanou Wi-Fi/router je reálný scénář. Pokud by klienti ignorovali ověření certifikátu, lze podvrhnout server.

- **API klíče a citlivá data v plaintextu**
  - Pokud jsou API klíče uložené v DB v plaintextu, kompromitace DB znamená kompromitaci agentů.

#### Nižší závažnost (spíš kvalita/udržovatelnost)

- **Hardcoded `BACKEND_URL` v Android build konfiguraci**
  - Primárně maintainability/UX problém (párování/konfigurace), sekundárně i security (snadné přesměrování na špatný server při nepozorném buildu).

### Security doporučení (prioritizace pro domácí standalone)

- **Priorita 1 (nutné):**
  - vynutit nastavení `SECRET_KEY` bez defaultu
  - chránit přístup k uploadům (ne servírovat screenshoty jako veřejné statické soubory; nebo použít jednorázové/signed URL)
  - zamezit `ssl_verify: false` v produkčních cestách

- **Priorita 2 (doporučené):**
  - omezit CORS na konkrétní originy dashboardu
  - zavést rate limiting (i doma pomůže proti “noise” a primitivním pokusům)
  - nastavit retenční politiku pro screenshoty a logy (a necommitovat je)

---

## Konkrétní seznam souborů k posouzení/odstranění z repa (pokud nejsou čistě lokální)

### Dev/build/test artefakty

- `backend/venv/`
- `frontend/node_modules/`
- `clients/android/app/build/`
- `installer/agent/build/`
- `installer/agent/dist/`
- `installer/agent/output/`
- `clients/android/build_log*.txt`
- `installer/agent/test.iss` (pokud není aktivně používán)
- `dev/*.bat` (ponechat, ale označit jako dev-only)

### Runtime data (nepatří do zdrojáků)

- `backend/uploads/**`
- `backend/app.log`
- `parental_control.db`
- `clients/windows/agent/report_queue.json`
- `clients/windows/agent/usage_cache.json`

---

## Doporučený postup (krátký, praktický)

- **Lean cleanup (1-2 hodiny):**
  - ověřit, že artefakty nejsou commitované; pokud ano, odstranit z historie (git) a ponechat jen v release pipeline
  - sjednotit `insights_service.py` (odstranit experimental duplicitu)
  - odstranit nebo archivovat `docs/*.resolved`
  - odstranit runtime data (uploads, db, logs) ze zdrojového stromu

- **Refactoring (1-3 dny):**
  - rozdělit `clients/windows/agent/enforcer.py` na menší moduly podle zodpovědností
  - rozdělit `AppDetectorService.kt` na policy + effects
  - přesunout těžké agregace v backend reportech do `services/`

- **Security hardening pro domácí režim (0.5-2 dny):**
  - odstranit defaultní `SECRET_KEY`, vynutit konfiguraci
  - zabezpečit přístup ke screenshotům (neveřejné static mount)
  - auditovat, kde se může objevit `ssl_verify: false` a uzamknout to pro produkční buildy
  - omezit CORS na dashboard originy

---

**Konec auditu**

