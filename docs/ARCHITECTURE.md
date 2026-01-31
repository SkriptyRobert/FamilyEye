# Architektura systému

## Přehled

Systém se skládá ze čtyř hlavních komponent:
- **Backend Server** (FastAPI) - API, databáze, autentizace
- **Frontend Dashboard** (React) - Webové rozhraní pro rodiče
- **Windows Agent** - Monitorování a vynucování pravidel na Windows zařízeních
- **Android Agent** - Monitorování a vynucování pravidel na Android zařízeních s Device Owner ochranou a Smart Shield

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
│  - Smart Shield │
└────────┬────────┘
         │
         │ HTTPS
         │
    ┌────┴────┐
    ▼         ▼
┌─────────┐ ┌──────────┐
│ Windows │ │ Android  │
│ Agent   │ │ Agent    │
│         │ │          │
│ Monitor │ │ Monitor  │
│ Enforcer│ │ Enforcer │
│ Reporter│ │ Reporter │
│         │ │ Smart    │
│         │ │ Shield   │
│         │ │ Device   │
│         │ │ Owner    │
└─────────┘ └──────────┘
```

## Komponenty

### Backend Server

**Umístění**: `backend/app/`

**Hlavní moduly**:
- `main.py` - FastAPI aplikace, routing
- `models.py` - SQLAlchemy modely
- `api/` - API endpointy (auth, devices, rules, reports, websocket, trust, shield, files)
- `services/` - Business logika (pairing_service, app_filter)
- `database.py` - Databázové připojení
- `config.py` - Konfigurace

**Technologie**:
- FastAPI 0.104.1
- SQLAlchemy 2.0.23
- SQLite (výchozí databáze)
- JWT autentizace
- WebSocket pro real-time komunikaci
- Smart Shield API pro detekci obsahu

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

### Android Agent

**Umístění**: `clients/android/app/src/main/java/com/familyeye/agent/`

**Hlavní moduly**:
- `service/FamilyEyeService.kt` - Hlavní foreground služba
- `service/AppDetectorService.kt` - Accessibility Service pro detekci aplikací
- `service/EnforcementService.kt` - Vynucování pravidel
- `service/RuleEnforcer.kt` - Logika vynucování pravidel
- `service/UsageTracker.kt` - Sledování použití
- `service/Reporter.kt` - Odesílání statistik
- `scanner/ContentScanner.kt` - Smart Shield skenování obsahu
- `scanner/KeywordDetector.kt` - Aho-Corasick detekce klíčových slov
- `device/DeviceOwnerPolicyEnforcer.kt` - Device Owner ochrana
- `receiver/BootReceiver.kt` - Boot receiver pro automatické spuštění
- `receiver/RestartReceiver.kt` - Restart receiver pro obnovení služby

**Technologie**:
- Kotlin
- Android SDK
- Device Owner API
- Accessibility Service API
- WorkManager (persistence)
- JobScheduler (persistence)
- AlarmManager (persistence)
- Room Database (lokální cache)
- OkHttp (HTTP komunikace)
- WebSocket (real-time komunikace)

**Speciální funkce**:
- **Device Owner** - Nejvyšší úroveň ochrany, aplikaci nelze odinstalovat
- **Smart Shield** - Detekce škodlivého obsahu pomocí Aho-Corasick algoritmu
- **5 vrstev persistence** - Watchdog, JobScheduler, WorkManager, AlarmManager, KeepAlive
- **Direct Boot** - Funguje i před odemknutím zařízení PINem

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
Agent → Monitor/Usage (Windows: dle konfigurace; Android: 10 s při zapnutém displeji)
Agent → Reporter/Sync (Android: 60 s při zapnutém displeji; Windows: reporting_interval typ. 300 s)
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

### 6. Smart Shield detekce (Android)

```
Android Agent → ContentScanner → KeywordDetector
Android Agent → Screenshot capture
Android Agent → POST /api/shield/alert → Backend
Backend → Uloží ShieldAlert → Database
Backend → WebSocket notify → Frontend
Frontend → Zobrazí upozornění
```

### 7. Device Owner ochrana (Android)

```
Android Agent → DeviceOwnerPolicyEnforcer
Android Agent → setUninstallBlocked(true)
Android Agent → applyBaselineRestrictions()
Android Agent → applySettingsProtection()
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
- `shield_keywords` - Klíčová slova pro Smart Shield
- `shield_alerts` - Detekce Smart Shield

Viz [DATABASE.md](./DATABASE.md) pro detailní schéma.

## Škálovatelnost

### Současné omezení

- SQLite databáze (single-file)
- Single-threaded agent
- In-memory WebSocket connections

## Rozšíření

### Přidání nové platformy

Android agent je již implementován. Pro přidání další platformy (např. iOS, macOS):

1. Vytvořit `clients/{platform}/agent/`
2. Implementovat stejné rozhraní jako existující agenty
3. Přidat `device_type` do párování
4. Aktualizovat frontend pro nový typ zařízení

### Přidání nového typu pravidla

1. Přidat `rule_type` do `Rule` modelu
2. Implementovat logiku v `enforcer.py`
3. Přidat UI v `RuleEditor.jsx`
4. Aktualizovat API endpointy

Viz [DEVELOPMENT.md](./DEVELOPMENT.md) pro detailní návod.

