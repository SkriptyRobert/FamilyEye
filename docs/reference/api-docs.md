# API Documentation - Kompletní reference endpointů

Kompletní technická dokumentace všech API endpointů Smart Shield backendu. Tento dokument slouží jako reference pro vývojáře a integraci.

## Base URL

- **Vývoj**: `http://localhost:8000`
- **Produkce**: `https://your-domain:8000`

## Autentizace

### Rodiče (Frontend)

**Metoda**: Bearer Token (JWT)

**Header**:
```
Authorization: Bearer <jwt_token>
```

**Získání tokenu**:
- `POST /api/auth/login` - Přihlášení
- `POST /api/auth/register` - Registrace

**Platnost**: 24 hodin (nastaveno v `settings.ACCESS_TOKEN_EXPIRE_MINUTES`)

### Agenti

**Metoda**: API Key + Device ID v request body

**Request body**:
```json
{
  "device_id": "uuid",
  "api_key": "uuid"
}
```

**Získání**: Při párování zařízení (`POST /api/devices/pairing/pair`)

## Endpointy

### Autentizace

#### POST /api/auth/register

Registrace nového uživatele.

**Request Body**:
```json
{
  "email": "parent@example.com",
  "password": "secure_password",
  "role": "parent"
}
```

**Response** (201 Created):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Error Codes**:
- `400` - Email již existuje nebo neplatný role
- `429` - Příliš mnoho pokusů (rate limit: 3 za minutu)

**Zdroj**: `backend/app/api/auth.py:register()`

#### POST /api/auth/login

Přihlášení uživatele.

**Request Body**:
```json
{
  "email": "parent@example.com",
  "password": "secure_password"
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Error Codes**:
- `401` - Neplatný email nebo heslo
- `429` - Příliš mnoho pokusů (rate limit: 5 za minutu)

**Zdroj**: `backend/app/api/auth.py:login()`

#### GET /api/auth/me

Informace o přihlášeném uživateli.

**Headers**: `Authorization: Bearer <token>`

**Response** (200 OK):
```json
{
  "id": 1,
  "email": "parent@example.com",
  "role": "parent",
  "created_at": "2024-01-01T00:00:00Z"
}
```

**Error Codes**:
- `401` - Neplatný nebo expirovaný token

**Zdroj**: `backend/app/api/auth.py:get_current_user_info()`

### Zařízení

#### POST /api/devices/pairing/token

Vytvoření pairing tokenu pro párování zařízení.

**Headers**: `Authorization: Bearer <token>`

**Response** (200 OK):
```json
{
  "token": "550e8400-e29b-41d4-a716-446655440000",
  "expires_at": "2024-01-01T00:05:00Z",
  "pairing_url": "parental-control://pair?token=550e8400-e29b-41d4-a716-446655440000&backend=https://..."
}
```

**Expirace**: 5 minut

**Zdroj**: `backend/app/api/devices/pairing.py:create_pairing_token()`

#### GET /api/devices/pairing/qr/{token}

QR kód pro párování.

**Headers**: `Authorization: Bearer <token>`

**Response** (200 OK):
```json
{
  "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
  "token": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Zdroj**: `backend/app/api/devices/pairing.py:get_pairing_qr_code()`

#### POST /api/devices/pairing/pair

Párování zařízení (voláno agentem).

**Request Body**:
```json
{
  "token": "550e8400-e29b-41d4-a716-446655440000",
  "device_name": "Dětský telefon",
  "device_type": "android",
  "mac_address": "AA:BB:CC:DD:EE:FF",
  "device_id": "550e8400-e29b-41d4-a716-446655440001"
}
```

**Response** (200 OK):
```json
{
  "device_id": "550e8400-e29b-41d4-a716-446655440001",
  "api_key": "550e8400-e29b-41d4-a716-446655440002",
  "backend_url": "https://192.168.1.100:8000"
}
```

**Error Codes**:
- `400` - Neplatný nebo expirovaný token
- `404` - Token nenalezen

**Zdroj**: `backend/app/api/devices/pairing.py:pair_device()`

#### GET /api/devices/

Seznam všech zařízení rodiče.

**Headers**: `Authorization: Bearer <token>`

**Response** (200 OK):
```json
[
  {
    "id": 1,
    "name": "Dětský telefon",
    "device_type": "android",
    "mac_address": "AA:BB:CC:DD:EE:FF",
    "device_id": "550e8400-e29b-41d4-a716-446655440001",
    "parent_id": 1,
    "child_id": null,
    "api_key": "550e8400-e29b-41d4-a716-446655440002",
    "paired_at": "2024-01-01T00:00:00Z",
    "last_seen": "2024-01-01T12:00:00Z",
    "is_active": true,
    "is_online": true,
    "has_lock_rule": false,
    "has_network_block": false,
    "is_device_owner": true,
    "device_owner_activated_at": "2024-01-01T00:05:00Z"
  }
]
```

**Zdroj**: `backend/app/api/devices/crud.py:get_devices()`

#### POST /api/devices/{device_id}/lock

Zamknutí zařízení (instant action).

**Headers**: `Authorization: Bearer <token>`

**Response** (200 OK):
```json
{
  "status": "success",
  "message": "Lock command sent to device"
}
```

**Chování**:
- Vytvoří `lock_device` pravidlo v databázi
- Odešle WebSocket příkaz `LOCK_NOW` na zařízení

**Zdroj**: `backend/app/api/devices/actions.py:lock_device()`

#### POST /api/devices/{device_id}/unlock

Odemknutí zařízení.

**Headers**: `Authorization: Bearer <token>`

**Response** (200 OK):
```json
{
  "status": "success",
  "message": "Unlock command sent to device"
}
```

**Zdroj**: `backend/app/api/devices/actions.py:unlock_device()`

#### POST /api/devices/{device_id}/pause-internet

Pozastavení internetu na X minut.

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**:
- `duration_minutes` (default: 60, min: 1, max: 1440)

**Response** (200 OK):
```json
{
  "status": "success",
  "message": "Internet paused for 60 minutes",
  "duration_minutes": 60
}
```

**Zdroj**: `backend/app/api/devices/actions.py:pause_internet()`

#### POST /api/devices/{device_id}/resume-internet

Obnovení internetu.

**Headers**: `Authorization: Bearer <token>`

**Response** (200 OK):
```json
{
  "status": "success",
  "message": "Internet access resumed",
  "rules_removed": 1
}
```

**Zdroj**: `backend/app/api/devices/actions.py:resume_internet()`

### Pravidla

#### POST /api/rules/

Vytvoření pravidla.

**Headers**: `Authorization: Bearer <token>`

**Request Body**:
```json
{
  "device_id": 1,
  "rule_type": "app_block",
  "app_name": "steam",
  "enabled": true
}
```

**Typy pravidel**:
- `app_block` - Blokování aplikace
- `time_limit` - Časový limit (vyžaduje `time_limit` v minutách)
- `daily_limit` - Denní limit (vyžaduje `time_limit` v minutách)
- `schedule` - Časové okno (vyžaduje `schedule_start_time`, `schedule_end_time`, `schedule_days`)
- `lock_device` - Zamknutí zařízení
- `network_block` - Blokování sítě
- `website_block` - Blokování webu (vyžaduje `website_url`)

**Response** (201 Created):
```json
{
  "id": 1,
  "device_id": 1,
  "rule_type": "app_block",
  "app_name": "steam",
  "enabled": true,
  "created_at": "2024-01-01T00:00:00Z"
}
```

**Overwrite Logic**:
- App/Web rules: Přepíše existující pravidlo stejného typu pro stejnou aplikaci
- Device Schedules: Povoluje více pravidel
- Device Limits/Lock: Singleton (přepíše existující)

**Zdroj**: `backend/app/api/rules.py:create_rule()`

#### GET /api/rules/device/{device_id}

Seznam pravidel pro zařízení.

**Headers**: `Authorization: Bearer <token>`

**Response** (200 OK):
```json
[
  {
    "id": 1,
    "device_id": 1,
    "rule_type": "app_block",
    "app_name": "steam",
    "enabled": true,
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

**Filtrování**: Vrací pouze `enabled == true` pravidla

**Zdroj**: `backend/app/api/rules.py:get_device_rules()`

#### POST /api/rules/agent/fetch

Agent endpoint pro načtení pravidel.

**Request Body**:
```json
{
  "device_id": "550e8400-e29b-41d4-a716-446655440001",
  "api_key": "550e8400-e29b-41d4-a716-446655440002"
}
```

**Response** (200 OK):
```json
{
  "rules": [...],
  "daily_usage": 3600,
  "usage_by_app": {
    "chrome": 1800,
    "steam": 1800
  },
  "server_time": "2024-01-01T12:00:00Z",
  "settings_protection": "full",
  "settings_exceptions": null
}
```

**Výpočet daily_usage**: Počítá se jako COUNT unikátních MINUT (ne celkový počet logů)

**Zdroj**: `backend/app/api/rules.py:agent_fetch_rules()`

### Smart Shield

#### GET /api/shield/keywords/{device_id}

Seznam klíčových slov pro zařízení.

**Headers**: `Authorization: Bearer <token>`

**Response** (200 OK):
```json
[
  {
    "id": 1,
    "device_id": 1,
    "keyword": "drogy",
    "category": "drugs",
    "severity": "high",
    "enabled": true,
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

**Zdroj**: `backend/app/api/shield.py:get_keywords()`

#### POST /api/shield/keywords

Přidání klíčového slova.

**Headers**: `Authorization: Bearer <token>`

**Request Body**:
```json
{
  "device_id": 1,
  "keyword": "drogy",
  "category": "drugs",
  "severity": "high"
}
```

**Response** (200 OK):
```json
{
  "id": 1,
  "device_id": 1,
  "keyword": "drogy",
  "category": "drugs",
  "severity": "high",
  "enabled": true,
  "created_at": "2024-01-01T00:00:00Z"
}
```

**Normalizace**: Keyword je automaticky převeden na lowercase

**Zdroj**: `backend/app/api/shield.py:add_keyword()`

#### POST /api/shield/alert

Report alertu z agenta (detekce klíčového slova).

**Request Body**:
```json
{
  "device_id": "550e8400-e29b-41d4-a716-446655440001",
  "api_key": "550e8400-e29b-41d4-a716-446655440002",
  "keyword": "drogy",
  "app_name": "com.android.chrome",
  "detected_text": "Kde sehnat drogy levně",
  "screenshot_url": "screenshots/device_id/screenshot_20240101_120000.jpg",
  "severity": "high"
}
```

**Response** (201 Created):
```json
{
  "status": "alert_recorded"
}
```

**Spam Prevention**:
- **Instant deduplication**: Blokuje duplikáty do 5 sekund
- **Burst Logic**: Pokud byly předchozí 2 alerty blízko sebe (<2 minuty), vynucuje 5minutový cooldown

**WebSocket Notification**: Automaticky odešle notifikaci rodiči přes WebSocket

**Zdroj**: `backend/app/api/shield.py:report_alert()`

#### GET /api/shield/alerts/{device_id}

Seznam alertů pro zařízení.

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**:
- `limit` (default: 50, max: 100)

**Response** (200 OK):
```json
[
  {
    "id": 1,
    "device_id": 1,
    "keyword": "drogy",
    "app_name": "com.android.chrome",
    "detected_text": "Kde sehnat drogy levně",
    "screenshot_url": "https://backend/api/files/screenshots/device_id/screenshot.jpg",
    "severity": "high",
    "is_read": false,
    "timestamp": "2024-01-01T12:00:00Z"
  }
]
```

**Řazení**: Podle `timestamp DESC` (nejnovější první)

**Zdroj**: `backend/app/api/shield.py:get_alerts()`

#### POST /api/shield/alerts/batch-delete

Hromadné mazání alertů.

**Headers**: `Authorization: Bearer <token>`

**Request Body**:
```json
{
  "alert_ids": [1, 2, 3]
}
```

**Response** (200 OK):
```json
{
  "status": "deleted",
  "count": 3
}
```

**Chování**: Automaticky smaže i screenshoty z disku

**Zdroj**: `backend/app/api/shield.py:batch_delete_alerts()`

### Reporty

#### POST /api/reports/agent/report

Agent endpoint pro odeslání statistik.

**Request Body**:
```json
{
  "device_id": "550e8400-e29b-41d4-a716-446655440001",
  "api_key": "550e8400-e29b-41d4-a716-446655440002",
  "usage_logs": [
    {
      "app_name": "chrome",
      "duration": 60,
      "timestamp": "2024-01-01T12:00:00Z"
    }
  ],
  "running_processes": ["chrome", "steam"]
}
```

**Response** (200 OK):
```json
{
  "status": "success",
  "logs_received": 10,
  "last_seen": "2024-01-01T12:00:00Z"
}
```

**Zdroj**: `backend/app/api/reports/agent_endpoints.py:agent_report()`

#### GET /api/reports/device/{device_id}/summary

Souhrn statistik zařízení (main dashboard data).

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**:
- `date` (optional) - Datum ve formátu YYYY-MM-DD (default: dnes)

**Response** (200 OK):
```json
{
  "device_id": 1,
  "device_name": "Dětský telefon",
  "today_usage_seconds": 7200,
  "today_usage_hours": 2.0,
  "yesterday_usage_seconds": 5400,
  "week_avg_seconds": 6000,
  "apps_used_today": 5,
  "top_apps": [
    {"app_name": "chrome", "duration_seconds": 3600}
  ],
  "active_rules": 3,
  "apps_with_limits": [...],
  "daily_limit": {...},
  "running_processes": ["chrome", "steam"],
  "smart_insights": {
    "focus_score": 75,
    "wellness_score": 80,
    "anomalies": []
  }
}
```

**Zdroj**: `backend/app/api/reports/summary_endpoint.py:get_device_summary()`

#### GET /api/reports/device/{device_id}/usage-by-hour

Použití po hodinách (heatmap data).

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**:
- `days` (default: 7, max: 14)

**Response** (200 OK):
```json
[
  {
    "date": "2024-01-01",
    "hour": 14,
    "duration_seconds": 3600,
    "duration_minutes": 60.0,
    "apps_count": 3,
    "sessions_count": 10
  }
]
```

**Zdroj**: `backend/app/api/reports/stats_endpoints.py:get_usage_by_hour()`

## Error Codes

Viz [Error Codes](error-codes.md) pro kompletní seznam chybových kódů.

## WebSocket

Real-time komunikace probíhá přes WebSocket na endpointu `/ws/{device_id}`.

**Příkazy odesílané na zařízení**:
- `LOCK_NOW` - Zamknutí zařízení
- `UNLOCK_NOW` - Odemknutí zařízení
- `REFRESH_RULES` - Obnovení pravidel
- `SCREENSHOT_NOW` - Pořízení screenshotu
- `DEACTIVATE_DEVICE_OWNER` - Deaktivace Device Owner
- `REACTIVATE_DEVICE_OWNER` - Reaktivace Device Owner

**Notifikace odesílané rodiči**:
- `shield_alert` - Detekce klíčového slova
- `device_status` - Změna stavu zařízení

**Zdroj**: `backend/app/api/websocket.py`
