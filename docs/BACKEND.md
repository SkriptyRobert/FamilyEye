# Backend dokumentace

## Přehled

Backend je postaven na FastAPI a poskytuje REST API a WebSocket pro komunikaci s frontendem a agenty.

## Struktura

```
backend/app/
├── __init__.py
├── main.py              # FastAPI aplikace
├── config.py            # Konfigurace
├── database.py          # Databázové připojení
├── models.py            # SQLAlchemy modely
├── schemas.py           # Pydantic schémata
├── cache.py             # Cache implementace
├── ssl_manager.py       # SSL certifikáty
├── api/                 # API endpointy
│   ├── auth.py          # Autentizace
│   ├── devices/         # Správa zařízení (balíček)
│   │   ├── __init__.py  # Sjednocený router
│   │   ├── crud.py      # CRUD, seznam, detail, úprava, smazání
│   │   ├── pairing.py   # Párování (token, QR, pair)
│   │   ├── actions.py   # Rychlé akce (lock, unlock, pause-internet, atd.)
│   │   ├── settings.py  # Nastavení ochrany (settings-protection)
│   │   └── utils.py     # verify_device_api_key a pomocné funkce
│   ├── rules.py         # Správa pravidel
│   ├── reports/         # Statistiky a reporty (balíček)
│   │   ├── __init__.py  # Sjednocený router
│   │   ├── agent_endpoints.py   # Agent report, critical-event, screenshot
│   │   ├── device_endpoints.py  # Dotazy na použití, cleanup, running processes
│   │   ├── stats_endpoints.py   # usage-by-hour, usage-trends, weekly-pattern, app-details, app-trends
│   │   └── summary_endpoint.py  # Souhrn zařízení (dashboard), Smart Insights
│   ├── websocket.py     # WebSocket
│   ├── trust.py         # SSL certifikáty
│   ├── files.py         # Nahrávání a servírování screenshotů
│   └── shield.py        # Smart Shield (klíčová slova, alerty)
└── services/
    ├── pairing_service.py   # Párování zařízení
    ├── cleanup_service.py    # Mazání starých dat, čištění při smazání zařízení
    ├── insights_service.py  # Smart Insights (focus, wellness, anomálie)
    ├── stats_service.py     # Pomocné výpočty statistik (denní použití, rozsahy)
    └── summary_service.py    # Výpočet souhrnu použití a limitů
backend/scripts/
├── __init__.py
├── init_admin.py        # Vytvoření prvního rodičovského účtu
```

V kořeni `backend/` dále leží pomocné skripty:
- `run_https.py` - Spuštění HTTPS serveru.
- `service.py` - Správa Windows služby.

## Spuštění

### Vývoj

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python run_https.py
```

### Produkce

```bash
# Manuální spuštění (bez instalátoru)
python run_https.py          # HTTPS server (self-signed certy v ./certs nebo ProgramData)

# Windows služba
python service.py install    # registrace / správa služby přes Python skript
python service.py start
```

## Konfigurace

**Soubor**: `backend/app/config.py`

**Proměnné prostředí**:
- `SECRET_KEY` - JWT secret key
- `DATABASE_URL` - Databázové připojení
- `BACKEND_HOST` - Host (výchozí: 0.0.0.0)
- `BACKEND_PORT` - Port (výchozí: 8443)
- `BACKEND_URL` - URL backendu

**Výchozí hodnoty**:
- Port: 8443
- Database: SQLite (`parental_control.db`)
- JWT expirace: 24 hodin

## API moduly

### Auth (`api/auth.py`)

**Endpointy**:
- `POST /api/auth/register` - Registrace uživatele
- `POST /api/auth/login` - Přihlášení
- `GET /api/auth/me` - Informace o uživateli

**Funkce**:
- `get_current_user()` - Validace JWT tokenu
- `get_current_parent()` - Ověření role rodiče
- `create_access_token()` - Generování JWT

### Devices (`api/devices/`)

Balíček spojuje routery z `crud`, `pairing`, `actions` a `settings`.

**Endpointy** (shrnutí):
- Párování: `POST /api/devices/pairing/token`, `GET /api/devices/pairing/qr/{token}`, `POST /api/devices/pairing/pair`
- CRUD: `GET /api/devices/`, `GET /api/devices/{device_id}`, `PUT /api/devices/{device_id}`, `DELETE /api/devices/{device_id}`
- Akce: `POST /api/devices/{device_id}/lock`, `unlock`, `pause-internet`, `resume-internet`, deaktivace Device Owner
- Nastavení: `PUT /api/devices/{device_id}/settings-protection`

**Moduly**:
- `crud.py` - Seznam, detail, úprava, smazání zařízení
- `pairing.py` - Generování tokenu, QR, přijetí párování od agenta
- `actions.py` - Rychlé akce (lock/unlock, síť, Device Owner deaktivace)
- `settings.py` - Ochrana nastavení (full/off) a výjimky
- `utils.py` - `verify_device_api_key()` pro validaci API klíče agenta

### Rules (`api/rules.py`)

**Endpointy**:
- `POST /api/rules/` - Vytvoření pravidla
- `GET /api/rules/device/{device_id}` - Pravidla pro zařízení
- `GET /api/rules/{rule_id}` - Detail pravidla
- `PUT /api/rules/{rule_id}` - Aktualizace pravidla
- `DELETE /api/rules/{rule_id}` - Smazání pravidla
- `POST /api/rules/agent/fetch` - Agent endpoint pro načtení pravidel

**Typy pravidel**:
- `app_block` - Blokování aplikace
- `time_limit` - Časový limit pro aplikaci
- `daily_limit` - Denní limit pro celé zařízení
- `schedule` - Časové okno pro použití
- `lock_device` - Zamknutí zařízení
- `network_block` - Blokování sítě
- `website_block` - Blokování webu

### Reports (`api/reports/`)

Balíček rozděluje endpointy do čtyř modulů.

**Moduly**:
- `agent_endpoints.py` - `POST /api/reports/agent/report`, `critical-event`, nahrání screenshotu
- `device_endpoints.py` - `GET /api/reports/device/{device_id}/usage`, cleanup, běžící procesy
- `stats_endpoints.py` - `usage-by-hour`, `usage-trends`, `weekly-pattern`, `app-details`, `app-trends`
- `summary_endpoint.py` - `GET /api/reports/device/{device_id}/summary` (dashboard, Smart Insights)

**Optimalizace**:
- Cache pro statistiky (5-10 minut)
- Agregace na databázové úrovni
- Limitování počtu dní pro dotazy

### WebSocket (`api/websocket.py`)

**Endpoint**: `WS /api/ws/{user_id}`

**Funkce**:
- Real-time aktualizace pro frontend
- Broadcast zpráv uživateli
- Automatické odpojení při chybě

### Trust (`api/trust.py`)

**Endpointy**:
- `GET /api/trust/ca.crt` - Stažení CA certifikátu
- `GET /api/trust/info` - Informace o SSL
- `GET /api/trust/qr.png` - QR kód pro certifikát
- `GET /api/trust/status` - Status SSL

### Files (`api/files.py`)

Nahrávání a servírování screenshotů z agentů.

**Endpointy**:
- `GET /api/files/screenshots/{device_id}/{filename}` - Zobrazení screenshotu (auth)
- `POST /api/files/upload/screenshot` - Nahrání screenshotu (agent s API key)

### Shield (`api/shield.py`)

Smart Shield: klíčová slova a alerty z detekce obsahu.

**Endpointy**:
- `GET /api/shield/keywords/{device_id}` - Seznam klíčových slov
- `POST /api/shield/keywords` - Přidání klíčového slova
- `DELETE /api/shield/keywords/{keyword_id}` - Smazání klíčového slova
- `POST /api/shield/agent/keywords` - Agent načte klíčová slova
- `POST /api/shield/alert` - Agent ohlásí detekci
- `GET /api/shield/alerts/{device_id}` - Seznam alertů
- `DELETE /api/shield/alerts/{alert_id}` - Smazání alertu
- `POST /api/shield/alerts/batch-delete` - Hromadné smazání alertů

## Databázové modely

Viz [DATABASE.md](./DATABASE.md) pro detailní popis.

## Služby

### Pairing Service (`services/pairing_service.py`)

**Funkce**:
- `generate_pairing_token()` - Generování tokenu
- `validate_pairing_token()` - Validace tokenu
- `generate_qr_code()` - Generování QR kódu
- `create_device_from_pairing()` - Vytvoření zařízení

**Tok párování**:
1. Rodič vytvoří pairing token
2. Agent odešle pairing request s tokenem
3. Backend vytvoří zařízení a vrátí API key
4. Agent uloží konfiguraci

### Cleanup Service (`services/cleanup_service.py`)

Mazání starých dat a čištění při smazání zařízení.

**Funkce**:
- `cleanup_old_data()` - Mazání starých usage_logs (např. 90 dní), screenshotů (např. 30 dní)
- `cleanup_device_data()` - Kompletní odstranění zařízení včetně souborů a záznamů v DB
- Voláno z daily tasku v `main.py` a při DELETE zařízení

### Insights Service (`services/insights_service.py`)

Smart Insights: metriky focus, wellness a anomálie z usage logů.

**Funkce**:
- `calculate_focus_metrics()` - Hluboká práce, přepínání kontextu, flow index
- Metriky wellness a detekce anomálií pro zobrazení na dashboardu
- Používá se v `summary_endpoint` při sestavování souhrnu

### Stats Service (`services/stats_service.py`)

Pomocné výpočty pro statistiky.

**Funkce**:
- `calculate_day_usage_minutes()` - Unikátní minuty použití pro daný den
- `calculate_day_usage_range()` - Agregace použití v časovém rozsahu
- Sdílená logika pro endpointy v `api/reports/stats_endpoints.py`

### Summary Service (`services/summary_service.py`)

Výpočet souhrnu použití a limitů pro dashboard.

**Funkce**:
- `calculate_precise_usage()` - Přesné denní použití (interval merging)
- Agregace aplikací, pravidel a limitů pro jeden device
- Používá `app_filter` pro vyloučení blacklistovaných aplikací
- Používá se v `api/reports/summary_endpoint.py`

## Inicializace admina

Skript **`backend/scripts/init_admin.py`** slouží k vytvoření prvního rodičovského (admin) účtu. Vytvoří tabulky, pokud neexistují, a přidá uživatele s rolí `parent`.

**Použití**:
```bash
cd backend
python scripts/init_admin.py <email> <password>
```

**Typické použití**:
- Manuální vytvoření účtu před prvním přihlášením
- Instalační průvodce serveru ho volá s e‑mailem a heslem zadanými v průvodci (viz [DEPLOYMENT.md](DEPLOYMENT.md), installer)

**Chování**:
- Pokud účet s daným e‑mailem již existuje, skript to oznámí a nic nemění.
- Heslo se ukládá jako hash (stejná funkce jako v `api/auth`).

## Cache

**Soubor**: `cache.py`

**Implementace**: In-memory cache s TTL

**Použití**:
- Statistiky (5-10 minut)
- Pravidla (30 sekund)
- Device info (1 minuta)

## SSL/TLS

**Soubor**: `ssl_manager.py`

**Funkce**:
- Automatická generace self-signed certifikátů
- CA certifikát pro důvěru
- QR kód pro snadnou instalaci

**Umístění certifikátů**: `certs/`

## Logging

**Konfigurace**: `main.py`

**Úrovně**:
- INFO - Obecné informace
- WARNING - Varování
- ERROR - Chyby
- DEBUG - Ladění

**Výstup**:
- Konzole (stdout)
- Soubor (`app.log`)

## Rozšíření

### Přidání nového endpointu

1. Vytvořit modul v `api/` (soubor nebo podmodul v balíčku `api/devices/`, `api/reports/`)
2. Definovat router s `APIRouter()`
3. Přidat endpointy s dekorátory
4. Zaregistrovat router v `main.py`; u balíčků se importuje router z `api.devices` resp. `api.reports`:
   ```python
   from .api import auth, devices, rules, reports, ...
   app.include_router(devices.router, prefix="/api/devices", tags=["devices"])
   ```

### Přidání nového modelu

1. Přidat třídu do `models.py`
2. Vytvořit Pydantic schéma v `schemas.py`
3. Přidat migraci (pokud používáte Alembic)
4. Aktualizovat API endpointy

### Přidání nové služby

1. Vytvořit soubor v `services/`
2. Implementovat business logiku
3. Importovat a použít v API endpointech

## Testování

```bash
# Spuštění testů (pokud existují)
pytest tests/

# Manuální testování API
python verify_api.py
```

## Produkční nasazení

Viz [DEPLOYMENT.md](./DEPLOYMENT.md) pro detailní návod.

