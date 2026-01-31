# Plan overeni spravnosti a profesionality MkDocs dokumentace

Tento dokument definuje plan forenzniho overeni dokumentace vuci kodu (na urovni cloud-init, SUSE, Terraform) a obsahuje **Discrepancy Report** z prvni analyzy.

---

## 1. Cile a principy

- **Vernost kodu**: Kazda funkce nebo endpoint uvedeny v dokumentaci musi existovat ve zdrojovem kodu a odpovidat chovani.
- **Tutorial „Grandma Test“**: Kroky v tutoriálech musi logicky navazovat a odkazovat na skutecne UI (tlacitka, labely, cesty).
- **Konzistence konfigurace**: `mkdocs.yml` nav musi odpovidat existujicim souborum; zadne rozbité interni odkazy.

---

## 2. Plan overeni (kroky)

### A. Feature Verification (Kod vs. Dokumentace)

| Ukol | Popis |
|------|--------|
| A1 | Prohledat `clients/android/app/src/main/` (Kotlin) a `backend/app/api/` (Python) pro vsechny entity zminene v docs (funkce, endpointy, konstanty). |
| A2 | Pro kazdou funkci zminenou v dokumentaci (napr. „Blocks TikTok“, „Aho-Corasick“, „rate limit 2 s“) overit, ze odpovidajici retezec nebo logika existuje v kodu nebo v `app-config.json` / `smart_shield_defaults.json`. |
| A3 | Vystup: seznam varovani typu „Doc tvrdi X, ale kod pro X chybi nebo se lisi.“ |

### B. Tutorial Logic Check (Grandma Test)

| Ukol | Popis |
|------|--------|
| B1 | Projit vsechny soubory v `docs/tutorials/` a `docs/how-to/` a mentalne simulovat kroky. |
| B2 | Overit **Missing Links**: Z krok 2 logicky vede krok 3? (napr. „Pripojte USB“ -> „Spustte prikaz“.) |
| B3 | Overit **Dead Ends**: Odkazuje tutorial na tlacitko nebo sekci, ktera v `frontend/src` neexistuje (jiný label nebo chybi)? |
| B4 | Akce: Upravit kroky tak, aby odpovidaly skutecnym labelum z React komponent (napr. „Nové pravidlo“ misto „Přidat pravidlo“, „Přidat“ misto „Přidat zařízení“ tam, kde je to presneji). |

### C. Configuration Consistency (mkdocs.yml vs. filesystem)

| Ukol | Popis |
|------|--------|
| C1 | Pro kazdy polozku v `nav` v `mkdocs.yml` overit, ze soubor existuje v `docs/` (relativne k docs). |
| C2 | Zkontrolovat interni odkazy v .md souborech: `[text](path)` – path musi vest na existujici soubor nebo platnou anchor. |
| C3 | Overit, ze obrazky (napr. `../images/dashboard.png`) existuji v `docs/images/` nebo `docs/assets/`. |

### D. API Documentation vs. Backend

| Ukol | Popis |
|------|--------|
| D1 | Pro kazdy endpoint v `reference/api-docs.md` overit existenci v `backend/app/api/` a shodu metody, cesty a hlavnich parametru. |
| D2 | Overit, ze response priklady (pole, typy) odpovidaji schemas a skutecne odpovedi (napr. `RuleResponse`, `PairingResponse`). |
| D3 | Zkontrolovat chybejici endpointy: co frontend/agenti volaji a neni v api-docs (napr. `GET /api/devices/pairing/status/{token}`). |

### E. Odkaz na referencni dokumentaci (cloud-init / SUSE / Terraform styl)

- Jednotna struktura sekci: Purpose, Requirements, Steps, Technical details, See also.
- Kazda „feature“ ma odkaz na zdrojovy soubor a radku („Zdroj: `backend/app/...`“).
- Verze a datum „Posledni aktualizace“ u klicovych stranek.
- Žádné „možná“, „obvykle“ bez odkazu na kod – pouze overene informace.

---

## 3. Discrepancy Report (vysledky forenzni analyzy)

### 3.1 Halucinace / nesoulad dokumentace s kodem

| # | Dokument | Tvrzeni | Stav |
|---|----------|---------|------|
| 1 | **how-to/unblock-app.md**, **how-to/restore-access.md** | Kroky „Dočasně povolit“ + nastaveni doby (30 min, 1 h). | **HALLUCINATION**: Ve frontendu (`RuleCard.jsx`, `RuleEditor.jsx`) existuje pouze „Smazat“ a „Upravit“. Žádné tlacitko „Dočasně povolit“ ani casovac. |
| 2 | **reference/feature-matrix.md** | „SCAN_INTERVAL_MS = 2000L (2 sekundy)“ pro rate limiting skenovani. | **OBSOLETE**: V `AgentConstants.kt` je `CONTENT_SCAN_INTERVAL_MS = 1_000L` (1 sekunda). |
| 3 | **docs/tutorials/first-setup.md** | „Klepněte na **Přidat pravidlo**“. | **NESOULAD**: V `RuleEditor.jsx` je tlacitko **„Nové pravidlo“**, ne „Přidat pravidlo“. |
| 4 | **docs/tutorials/first-setup.md**, **android-agent.md** | „Přidat zařízení“ (obrazovka / tab). | **DROBNY NESOULAD**: V `Dashboard.jsx` je tab s labelem **„Přidat“** (`label: 'Přidat'`, id `pairing`). Kontext je jasny, ale presne by melo byt „Přidat“ nebo doplneno „(Přidat zařízení)“ dle skutecneho UI. |

### 3.2 Rozbité nebo matouci kroky v tutoriálech

| # | Dokument | Problem |
|---|----------|--------|
| 1 | **how-to/unblock-app.md** | „Klepněte na **Vypnout** (toggle enabled)“ – V UI se zobrazuji pouze pravidla s `enabled === true` (GET `/api/rules/device/{id}` vrací jen enabled). Disabled pravidla v seznamu nejsou; neni tedy „toggle Vypnout“ na kartě. Deaktivace = Upravit pravidlo a nastavit enabled na false, nebo Smazat. |
| 2 | **how-to/change-pin.md** | Kroky „Najděte **Změnit PIN**“ v Android aplikaci – nebylo overeno, zda `SettingsScreen.kt` / UI skutecne obsahuje tento presny text. Doporuceni: overit v Android zdrojich a pripadne sjednotit label. |
| 3 | **getting-started.md** | Odkaz „Device Owner Setup“ – V `DeviceList.jsx` je modal s titulkem „Device Owner Setup“ a tlacitko „Aktivovat \"Device Owner\"“. Dokumentace je v souladu. |

### 3.3 Konfigurace mkdocs.yml vs. filesystem

| # | Problem |
|---|--------|
| 1 | V **nav** jsou pod Tutorials pouze `getting-started.md` a `first-setup.md`. V `docs/tutorials/` existuji take: `android-agent.md`, `pairing-devices.md`, `server-installation.md`, `windows-agent.md` – **nejsou v nav**, takze v postranni navigaci chybi. |
| 2 | V sekci „Pro vyvojare“ chybi **AGENT.md** – soubor v `docs/` existuje a `INDEX.md` na nej odkazuje, ale v `mkdocs.yml` v nav neni. |
| 3 | Vsechny ostatni polozky v nav (INDEX.md, how-to, reference, architecture, BACKEND, FRONTEND, ...) odkazuji na existujici soubory – **OK**. |

### 3.4 Chybejici nebo zastarale API v reference

| # | Problem |
|---|--------|
| 1 | **GET /api/devices/pairing/status/{token}** – Vola ho `DevicePairing.jsx` pro polling stavu spárování. V `reference/api-docs.md` tento endpoint **neni zdokumentovaný**. |
| 2 | **POST /api/devices/{device_id}/reset-pin** – Je implementovaný v `actions.py` a zdokumentovaný v how-to/change-pin; v api-docs.md neni samostatny endpoint pro reset-pin – doporuceni doplnit. |
| 3 | **POST /api/devices/{device_id}/deactivate-device-owner**, **reactivate-device-owner** – V backendu existuji, v `reference/api-docs.md` chybi – doporuceni doplnit. |

### 3.5 Overene shody (bez zmeny)

- TikTok / tiktok: v `app-config.json` (friendlyNames, whitelist) a v `RuleEditor.jsx` placeholder – dokumentace „Blokování aplikace (např. TikTok)“ je v poradku.
- KeywordDetector.kt, ContentScanner.kt, KeywordManager.kt – cesty a existence odpovidaji feature-matrix.
- WorkManager a AlarmManager – oba zminene v docs i kodu; dokumentace odpovida.
- Aho-Corasick, IGNORED_PACKAGES (YouTube, Netflix, Spotify), MAX_NODES = 500 – shoda s kodem.
- RESET_PIN, reset_pin endpoint, change-pin how-to – shoda.
- „Odemknout zařízení“, „Obnovit internet“ – existuji v Overview/WindowsDeviceCard/QuickActionsBar.
- „Nastavení slov“, „Rychlé přidání“ – v `SmartShield.jsx` odpovida.
- Odkazy na BACKEND.md, FRONTEND.md, ARCHITECTURE.md, reference/*, how-to/* z INDEX.md – soubory existuji.

---

## 4. Doporcene akce (prioritne)

1. **Odstranit nebo preformulovat „Dočasně povolit“** v how-to/unblock-app.md a how-to/restore-access.md – buď implementovat funkci, nebo z dokumentace odstranit a popsát pouze Smazat / Upravit (vypnout).  
   **Provedeno:** Odstraněno z obou souborů; restore-access odkazuje na unblock-app; unblock-app popisuje pouze Smazat a Upravit (deaktivace přes formulář).
2. **Aktualizovat feature-matrix.md**: zmenit „2 sekundy“ na „1 sekunda“ u CONTENT_SCAN_INTERVAL_MS a uvádět zdroj `AgentConstants.CONTENT_SCAN_INTERVAL_MS`.  
   **Provedeno:** Upraveno na `CONTENT_SCAN_INTERVAL_MS = 1_000L` (1 s) a zdroj `AgentConstants.kt`.
3. **Sjednotit labely v tutoriálech**: „Přidat pravidlo“ -> „Nové pravidlo“; „Přidat zařízení“ -> „Přidat“ (nebo doplnit vysvetleni podle UI).  
   **Provedeno:** first-setup.md a android-agent.md upraveny („Nové pravidlo“, záložka „Přidat“).
4. **Doplnit do mkdocs.yml nav**: tutorialy `android-agent`, `pairing-devices`, `server-installation`, `windows-agent`; do „Pro vyvojare“ pridat `AGENT.md`.  
   **Provedeno:** Všechny čtyři tutorialy a AGENT.md doplněny do nav.
5. **Doplnit do reference/api-docs.md**: GET pairing/status/{token}, POST reset-pin, POST deactivate-device-owner, POST reactivate-device-owner.  
   **Provedeno:** Všechny čtyři endpointy zdokumentovány v sekci Zařízení.
6. **Upravit how-to/unblock-app.md**: sekci „Vypnout (toggle)“ prepsat tak, aby odpovidala skutecnosti (Upravit pravidlo / enabled; GET vrací jen enabled pravidla).  
   **Provedeno:** Sekce přepsána na deaktivaci přes „Upravit“ a vysvětleno, že seznam zobrazuje jen aktivní pravidla.

**Dodatečně:** how-to/change-pin.md – v Android UI není položka „Změnit PIN“ v Nastavení; doplněna věta, že pro změnu PINu se používá webové rozhraní (Resetovat PIN).

---

## 5. Zaver

Plan overeni je definovan v sekcich 2 a 4. Discrepancy Report (sekce 3) identifikuje halucinace (Dočasně povolit), zastarale hodnoty (scan interval), nesoulad labelu (Přidat pravidlo vs. Nové pravidlo), chybejici polozky v nav a chybejici API endpointy v reference. Po provedeni doporucenych akci bude dokumentace v souladu s kodem a na urovni referencni dokumentace (cloud-init, SUSE, Terraform) v rozsahu „feature vs. code“ a „tutorial vs. UI“.
