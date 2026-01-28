# API dokumentace

## Přehled

REST API pro komunikaci mezi frontendem, backendem a agenty. Používá JWT autentizaci pro rodiče a API Key pro agenty.

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

**Platnost**: 24 hodin

### Agenti

**Metoda**: API Key + Device ID

**Request body**:
```json
{
  "device_id": "uuid",
  "api_key": "uuid"
}
```

**Získání**: Při párování zařízení

## Přehled endpointů

**Skupiny endpointů**:

| Skupina | Prefix | Popis |
|--------|--------|--------|
| Autentizace | `/api/auth` | Registrace, login, `/me` |
| Zařízení | `/api/devices` | CRUD, párování (token, qr, pair), akce (lock, unlock, pause-internet, atd.) |
| Pravidla | `/api/rules` | CRUD pravidel, agent fetch |
| Reporty | `/api/reports` | Agent report/critical-event, device usage/summary/trends, cleanup |
| WebSocket | `/api/ws` | Real-time zprávy pro frontend |
| Trust | `/api/trust` | CA certifikát, info, QR, status |
| Soubory | `/api/files` | Screenshot upload, servírování a mazání |
| Smart Shield | `/api/shield` | Klíčová slova, alerty, agent endpoints |

Doplňující technické detaily a zdrojové soubory: [reference/api-docs.md](reference/api-docs.md).

---

## Endpointy

### Autentizace

#### POST /api/auth/register

Registrace nového uživatele.

**Request**:
```json
{
  "email": "parent@example.com",
  "password": "secure_password",
  "role": "parent"
}
```

**Response** (201):
```json
{
  "access_token": "jwt_token",
  "token_type": "bearer"
}
```

**Chyby**: 400 (email již existuje), 429 (rate limit).

#### POST /api/auth/login

Přihlášení uživatele.

**Request**:
```json
{
  "email": "parent@example.com",
  "password": "secure_password"
}
```

**Response** (200):
```json
{
  "access_token": "jwt_token",
  "token_type": "bearer"
}
```

**Chyby**: 401 (neplatné údaje), 429 (rate limit).

#### GET /api/auth/me

Informace o přihlášeném uživateli. **Headers**: `Authorization: Bearer <token>`

**Response** (200):
```json
{
  "id": 1,
  "email": "parent@example.com",
  "role": "parent",
  "created_at": "2024-01-01T00:00:00Z"
}
```

### Zařízení

#### POST /api/devices/pairing/token

Vytvoření pairing tokenu. **Headers**: `Authorization: Bearer <token>`

**Response** (200):
```json
{
  "token": "uuid-token",
  "expires_at": "2024-01-01T00:05:00Z",
  "pairing_url": "parental-control://pair?token=...&backend=..."
}
```

Platnost tokenu: 5 minut.

#### GET /api/devices/pairing/qr/{token}

QR kód pro párování. **Headers**: `Authorization: Bearer <token>`

**Response** (200): JSON s `qr_code` (base64 PNG) a `token`.

#### POST /api/devices/pairing/pair

Párování zařízení (volá agent).

**Request**:
```json
{
  "token": "uuid-token",
  "device_name": "Dětský telefon",
  "device_type": "android",
  "mac_address": "AA:BB:CC:DD:EE:FF",
  "device_id": "uuid-device-id"
}
```

**Response** (200):
```json
{
  "device_id": "uuid-device-id",
  "api_key": "uuid-api-key",
  "backend_url": "https://192.168.1.100:8000"
}
```

#### GET /api/devices/

Seznam zařízení rodiče. **Headers**: `Authorization: Bearer <token>`

**Response** (200): Pole objektů zařízení (`id`, `name`, `device_type`, `is_online`, `has_lock_rule`, `has_network_block`, `is_device_owner`, …).

#### GET /api/devices/{device_id}, PUT /api/devices/{device_id}, DELETE /api/devices/{device_id}

Detail, aktualizace (např. `name`), smazání zařízení. Vše vyžaduje Bearer token.

#### POST /api/devices/{device_id}/lock

Zamknutí zařízení. Vytvoří pravidlo `lock_device` a odešle WebSocket příkaz.

**Response** (200): `{"status": "success", "message": "Lock command sent to device"}`

#### POST /api/devices/{device_id}/unlock

Odemknutí zařízení.

**Response** (200): `{"status": "success", "message": "Unlock command sent to device"}`

#### POST /api/devices/{device_id}/pause-internet

Pozastavení internetu. **Query**: `duration_minutes` (default 60, max 1440).

**Response** (200): `{"status": "success", "message": "Internet paused for X minutes", "duration_minutes": X}`

#### POST /api/devices/{device_id}/resume-internet

Obnovení internetu.

**Response** (200): `{"status": "success", "message": "Internet access resumed", "rules_removed": N}`

### Pravidla

#### POST /api/rules/

Vytvoření pravidla. **Headers**: `Authorization: Bearer <token>`

**Request** (příklad):
```json
{
  "device_id": 1,
  "rule_type": "app_block",
  "app_name": "steam",
  "enabled": true
}
```

**Typy pravidel**: `app_block`, `time_limit`, `daily_limit`, `schedule`, `lock_device`, `network_block`, `website_block`. U `time_limit`/`daily_limit` uvádět `time_limit` (minuty), u `schedule` uvádět `schedule_start_time`, `schedule_end_time`, `schedule_days`, u `website_block` uvádět `website_url`.

**Response** (201): Objekt pravidla včetně `id`, `created_at`.

#### GET /api/rules/device/{device_id}

Seznam pravidel pro zařízení. **Headers**: `Authorization: Bearer <token>`

**Response** (200): Pole pravidel (pouze `enabled == true`).

#### GET /api/rules/{rule_id}, PUT /api/rules/{rule_id}, DELETE /api/rules/{rule_id}

Detail, aktualizace a smazání pravidla. Vše vyžaduje Bearer token.

#### POST /api/rules/agent/fetch

Načtení pravidel agentem.

**Request**:
```json
{
  "device_id": "uuid",
  "api_key": "uuid"
}
```

**Response** (200):
```json
{
  "rules": [...],
  "daily_usage": 3600,
  "usage_by_app": {"chrome": 1800, "steam": 1800},
  "server_time": "2024-01-01T12:00:00Z",
  "settings_protection": "full",
  "settings_exceptions": null
}
```

### Reporty

#### POST /api/reports/agent/report

Odeslání statistik agentem.

**Request**:
```json
{
  "device_id": "uuid",
  "api_key": "uuid",
  "usage_logs": [{"app_name": "chrome", "duration": 60, "timestamp": "2024-01-01T12:00:00Z"}],
  "running_processes": ["chrome", "steam"]
}
```

**Response** (200): `{"status": "success", "logs_received": N, "last_seen": "..."}`

#### GET /api/reports/device/{device_id}/summary

Souhrn pro dashboard. **Headers**: `Authorization: Bearer <token>`. **Query**: `date` (YYYY-MM-DD, volitelné).

**Response** (200): Objekt s `today_usage_seconds`, `today_usage_hours`, `top_apps`, `apps_with_limits`, `daily_limit`, `running_processes`, `smart_insights` (focus_score, wellness_score, anomalies), apod.

#### GET /api/reports/device/{device_id}/usage-by-hour

Použití po hodinách (heatmap). **Query**: `days` (default 7, max 14).

**Response** (200): Pole objektů `{date, hour, duration_seconds, duration_minutes, apps_count, sessions_count}`.

Další report endpointy: `usage`, `usage-trends`, `weekly-pattern`, `app-details`, `app-trends`, `cleanup` – viz [reference/api-docs.md](reference/api-docs.md).

### WebSocket

**Endpoint**: `/ws/{user_id}` (resp. podle implementace v backendu).

**Příkazy na zařízení**: `LOCK_NOW`, `UNLOCK_NOW`, `REFRESH_RULES`, `SCREENSHOT_NOW`, `DEACTIVATE_DEVICE_OWNER`, `REACTIVATE_DEVICE_OWNER`.

**Notifikace rodiči**: `shield_alert`, `device_status`.

### Trust (SSL)

- `GET /api/trust/ca.crt` – stažení CA certifikátu (PEM).
- `GET /api/trust/info` – informace o SSL (`ca_subject`, `download_url`, `qr_url`).
- `GET /api/trust/qr.png` – QR kód pro certifikát.
- `GET /api/trust/status` – stav SSL.

### Soubory (screenshots)

- `GET /api/files/screenshots/{device_id}/{filename}` – zobrazení screenshotu (Bearer token nebo query `token`).
- `POST /api/files/upload/screenshot` – nahrání screenshotu agentem (headers `X-Device-ID`, `X-API-Key` nebo ekvivalent).
- `DELETE /api/files/screenshots/{device_id}/{filename}` – smazání screenshotu.

### Smart Shield

#### GET /api/shield/keywords/{device_id}

Seznam klíčových slov. **Headers**: `Authorization: Bearer <token>`

**Response** (200): Pole `{id, device_id, keyword, category, severity, enabled, created_at}`.

#### POST /api/shield/keywords

Přidání klíčového slova. **Request**: `{device_id, keyword, category, severity}`.

#### POST /api/shield/alert

Report alertu z agenta.

**Request**:
```json
{
  "device_id": "uuid",
  "api_key": "uuid",
  "keyword": "drogy",
  "app_name": "com.android.chrome",
  "detected_text": "úryvek textu",
  "screenshot_url": "screenshots/...",
  "severity": "high"
}
```

**Response** (201): `{"status": "alert_recorded"}`. Platí spam prevention (deduplikace, cooldown).

#### GET /api/shield/alerts/{device_id}

Seznam alertů. **Query**: `limit` (default 50, max 100).

#### POST /api/shield/alerts/batch-delete

Hromadné mazání. **Request**: `{"alert_ids": [1, 2, 3]}`.

#### POST /api/shield/agent/keywords

Načtení klíčových slov agentem. **Request**: `{device_id, api_key}`. **Response**: pole klíčových slov.

---

## Error responses

### 400 Bad Request

```json
{
  "detail": "Error message"
}
```

### 401 Unauthorized

```json
{
  "detail": "Could not validate credentials"
}
```

### 403 Forbidden

```json
{
  "detail": "Only parents can access this resource"
}
```

### 404 Not Found

```json
{
  "detail": "Resource not found"
}
```

### 500 Internal Server Error

```json
{
  "detail": "Internal server error"
}
```

## Rate limiting

Aktuálně není implementováno. Doporučeno pro produkci.

## Verze API

Aktuální verze: **1.0.0**

Verze je v hlavičce FastAPI aplikace (`main.py`).

## Swagger/OpenAPI

Automatická dokumentace dostupná na:
- `/docs` - Swagger UI
- `/redoc` - ReDoc

## Příklady

### cURL

```bash
# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"parent@example.com","password":"password"}'

# Get devices
curl -X GET http://localhost:8000/api/devices/ \
  -H "Authorization: Bearer <token>"
```

### Python

```python
import requests

# Login
response = requests.post(
    "http://localhost:8000/api/auth/login",
    json={"email": "parent@example.com", "password": "password"}
)
token = response.json()["access_token"]

# Get devices
response = requests.get(
    "http://localhost:8000/api/devices/",
    headers={"Authorization": f"Bearer {token}"}
)
devices = response.json()
```

