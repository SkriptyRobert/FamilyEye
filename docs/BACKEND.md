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
│   ├── devices.py       # Správa zařízení
│   ├── rules.py         # Správa pravidel
│   ├── reports.py       # Statistiky a reporty
│   ├── websocket.py     # WebSocket
│   └── trust.py         # SSL certifikáty
└── services/
    └── pairing_service.py # Párování zařízení
```

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
python run_https.py  # HTTPS server
# nebo
python service_wrapper.py  # Windows služba
```

## Konfigurace

**Soubor**: `backend/app/config.py`

**Proměnné prostředí**:
- `SECRET_KEY` - JWT secret key
- `DATABASE_URL` - Databázové připojení
- `BACKEND_HOST` - Host (výchozí: 0.0.0.0)
- `BACKEND_PORT` - Port (výchozí: 8000)
- `BACKEND_URL` - URL backendu

**Výchozí hodnoty**:
- Port: 8000
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

### Devices (`api/devices.py`)

**Endpointy**:
- `POST /api/devices/pairing/token` - Vytvoření pairing tokenu
- `GET /api/devices/pairing/qr/{token}` - QR kód pro párování
- `POST /api/devices/pairing/pair` - Párování zařízení
- `GET /api/devices/` - Seznam zařízení
- `GET /api/devices/{device_id}` - Detail zařízení
- `PUT /api/devices/{device_id}` - Aktualizace zařízení
- `DELETE /api/devices/{device_id}` - Smazání zařízení
- `POST /api/devices/{device_id}/lock` - Zamknutí zařízení
- `POST /api/devices/{device_id}/unlock` - Odemknutí zařízení
- `POST /api/devices/{device_id}/pause-internet` - Pozastavení internetu
- `POST /api/devices/{device_id}/resume-internet` - Obnovení internetu

**Funkce**:
- `verify_device_api_key()` - Validace API klíče agenta

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

### Reports (`api/reports.py`)

**Endpointy**:
- `POST /api/reports/agent/report` - Agent report statistik
- `POST /api/reports/agent/critical-event` - Kritické události
- `GET /api/reports/device/{device_id}/usage` - Použití zařízení
- `GET /api/reports/device/{device_id}/summary` - Souhrn statistik
- `GET /api/reports/device/{device_id}/usage-by-hour` - Použití po hodinách
- `GET /api/reports/device/{device_id}/usage-trends` - Trendy použití
- `GET /api/reports/device/{device_id}/weekly-pattern` - Týdenní vzory
- `GET /api/reports/device/{device_id}/app-details` - Detail aplikace
- `GET /api/reports/device/{device_id}/app-trends` - Trendy aplikace
- `DELETE /api/reports/cleanup` - Vyčištění starých logů

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

1. Vytvořit soubor v `api/` nebo přidat do existujícího
2. Definovat router s `APIRouter()`
3. Přidat endpointy s dekorátory
4. Zaregistrovat router v `main.py`:
   ```python
   app.include_router(novy_router, prefix="/api/novy", tags=["novy"])
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

