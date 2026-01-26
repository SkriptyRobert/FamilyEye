# Architektura systému

## Přehled

Systém se skládá ze tří hlavních komponent:
- **Backend Server** (FastAPI) - API, databáze, autentizace
- **Frontend Dashboard** (React) - Webové rozhraní pro rodiče
- **Windows Agent** - Monitorování a vynucování pravidel na zařízení

## Architektonický diagram

```
┌─────────────────┐
│  Frontend       │
│  (React)        │◄──┐
└────────┬────────┘   │
         │            │
         │ HTTP/WS    │
         ▼            │
┌─────────────────┐   │
│  Backend        │   │
│  (FastAPI)      │───┘
│  - API          │
│  - Database     │
│  - WebSocket    │
└────────┬────────┘
         │
         │ HTTPS
         │
┌────────▼────────┐
│  Windows Agent  │
│  - Monitor      │
│  - Enforcer     │
│  - Reporter     │
└─────────────────┘
```

## Komponenty

### Backend Server

**Umístění**: `backend/app/`

**Hlavní moduly**:
- `main.py` - FastAPI aplikace, routing
- `models.py` - SQLAlchemy modely
- `api/` - API endpointy (auth, devices, rules, reports, websocket, trust)
- `services/` - Business logika (pairing_service)
- `database.py` - Databázové připojení
- `config.py` - Konfigurace

**Technologie**:
- FastAPI 0.104.1
- SQLAlchemy 2.0.23
- SQLite (výchozí databáze)
- JWT autentizace
- WebSocket pro real-time komunikaci

### Frontend Dashboard

**Umístění**: `frontend/src/`

**Hlavní komponenty**:
- `App.jsx` - Hlavní routing, autentizace
- `components/` - UI komponenty
  - `Dashboard.jsx` - Hlavní dashboard
  - `DeviceList.jsx` - Seznam zařízení
  - `RuleEditor.jsx` - Editor pravidel
  - `Reports.jsx` - Statistiky a reporty
  - `charts/` - Grafické komponenty
- `services/api.js` - API klient
- `utils/` - Pomocné funkce

**Technologie**:
- React 18.2.0
- React Router 6.20.0
- Vite 5.0.8
- Recharts 3.6.0 (grafy)
- Axios 1.6.2 (HTTP klient)

### Windows Agent

**Umístění**: `clients/windows/agent/`

**Hlavní moduly**:
- `main.py` - Hlavní agent, orchestrace
- `monitor/` - Monitorování aplikací
- `enforcer/` - Vynucování pravidel
- `reporter.py` - Odesílání statistik
- `network_control.py` - Kontrola sítě
- `config.py` - Konfigurace agenta

**Technologie**:
- Python 3.x
- psutil (monitorování procesů)
- pywin32 (Windows API)
- requests (HTTP komunikace)

## Tok dat

### 1. Autentizace

```
Frontend → POST /api/auth/login → Backend
Backend → JWT Token → Frontend
Frontend → Bearer Token v header → Backend
```

### 2. Párování zařízení

```
Frontend → POST /api/devices/pairing/token → Backend
Backend → Pairing Token → Frontend
Frontend → Zobrazí QR kód
Agent → POST /api/devices/pairing/pair → Backend
Backend → Device + API Key → Agent
Agent → Uloží config.json
```

### 3. Monitorování

```
Agent → Monitor Loop (každých 5s)
Agent → Reporter Loop (každých 60s)
Agent → POST /api/reports/agent/report → Backend
Backend → Uloží UsageLog → Database
```

### 4. Vynucování pravidel

```
Agent → POST /api/rules/agent/fetch → Backend
Backend → Rules + Usage Stats → Agent
Agent → Enforcer Loop (každých 2s)
Agent → Kontrola pravidel → Akce (kill, block, notify)
```

### 5. Real-time aktualizace

```
Frontend → WebSocket /api/ws/{user_id} → Backend
Backend → Broadcast updates → Frontend
```

## Bezpečnost

### Autentizace

- **Rodiče**: JWT token (24h platnost)
- **Agenti**: API Key + Device ID
- **Hesla**: bcrypt hash (fallback pbkdf2_sha256)

### Komunikace

- **HTTPS**: Self-signed certifikáty (vývoj)
- **SSL/TLS**: Automatická generace certifikátů
- **CORS**: Konfigurovatelné pro produkci

### Oprávnění

- **Rodiče**: Plný přístup ke svým zařízením
- **Agenti**: Pouze vlastní data (validace API Key)

## Databáze

**Typ**: SQLite (výchozí)

**Tabulky**:
- `users` - Uživatelé (rodiče/děti)
- `devices` - Zařízení
- `rules` - Pravidla
- `usage_logs` - Statistiky použití
- `pairing_tokens` - Dočasné tokeny pro párování

Viz [DATABASE.md](./DATABASE.md) pro detailní schéma.

## Škálovatelnost

### Současné omezení

- SQLite databáze (single-file)
- Single-threaded agent
- In-memory WebSocket connections

### Možná vylepšení

- PostgreSQL/MySQL pro produkci
- Redis pro cache
- Message queue pro asynchronní zpracování
- Load balancer pro více instancí

## Rozšíření

### Přidání nové platformy (např. Android)

1. Vytvořit `clients/android/agent/`
2. Implementovat stejné rozhraní jako Windows agent
3. Přidat `device_type` do párování
4. Aktualizovat frontend pro nový typ zařízení

### Přidání nového typu pravidla

1. Přidat `rule_type` do `Rule` modelu
2. Implementovat logiku v `enforcer.py`
3. Přidat UI v `RuleEditor.jsx`
4. Aktualizovat API endpointy

Viz [DEVELOPMENT.md](./DEVELOPMENT.md) pro detailní návod.

