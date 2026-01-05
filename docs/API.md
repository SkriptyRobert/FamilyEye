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

**Response**:
```json
{
  "access_token": "jwt_token",
  "token_type": "bearer"
}
```

#### POST /api/auth/login

Přihlášení uživatele.

**Request**:
```json
{
  "email": "parent@example.com",
  "password": "secure_password"
}
```

**Response**:
```json
{
  "access_token": "jwt_token",
  "token_type": "bearer"
}
```

#### GET /api/auth/me

Informace o přihlášeném uživateli.

**Headers**: `Authorization: Bearer <token>`

**Response**:
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

Vytvoření pairing tokenu pro párování zařízení.

**Headers**: `Authorization: Bearer <token>`

**Response**:
```json
{
  "token": "uuid-token",
  "expires_at": "2024-01-01T00:05:00Z",
  "pairing_url": "parental-control://pair?token=..."
}
```

#### GET /api/devices/pairing/qr/{token}

QR kód pro párování.

**Headers**: `Authorization: Bearer <token>`

**Response**: Base64 encoded PNG image

#### POST /api/devices/pairing/pair

Párování zařízení (voláno agentem).

**Request**:
```json
{
  "token": "uuid-token",
  "device_name": "Dětský počítač",
  "device_type": "windows",
  "mac_address": "AA:BB:CC:DD:EE:FF",
  "device_id": "uuid-device-id"
}
```

**Response**:
```json
{
  "device_id": "uuid-device-id",
  "api_key": "uuid-api-key",
  "backend_url": "https://192.168.1.100:8000"
}
```

#### GET /api/devices/

Seznam všech zařízení rodiče.

**Headers**: `Authorization: Bearer <token>`

**Response**:
```json
[
  {
    "id": 1,
    "name": "Dětský počítač",
    "device_type": "windows",
    "mac_address": "AA:BB:CC:DD:EE:FF",
    "device_id": "uuid",
    "parent_id": 1,
    "child_id": null,
    "api_key": "uuid",
    "paired_at": "2024-01-01T00:00:00Z",
    "last_seen": "2024-01-01T12:00:00Z",
    "is_active": true,
    "is_online": true,
    "has_lock_rule": false,
    "has_network_block": false
  }
]
```

#### GET /api/devices/{device_id}

Detail zařízení.

**Headers**: `Authorization: Bearer <token>`

**Response**: Stejné jako v seznamu

#### PUT /api/devices/{device_id}

Aktualizace zařízení (např. název).

**Headers**: `Authorization: Bearer <token>`

**Request**:
```json
{
  "name": "Nový název"
}
```

#### DELETE /api/devices/{device_id}

Smazání zařízení a všech jeho dat.

**Headers**: `Authorization: Bearer <token>`

**Response**: 204 No Content

#### POST /api/devices/{device_id}/lock

Zamknutí zařízení.

**Headers**: `Authorization: Bearer <token>`

**Response**:
```json
{
  "status": "success",
  "message": "Lock command sent to device"
}
```

#### POST /api/devices/{device_id}/unlock

Odemknutí zařízení.

**Headers**: `Authorization: Bearer <token>`

#### POST /api/devices/{device_id}/pause-internet

Pozastavení internetu na X minut.

**Headers**: `Authorization: Bearer <token>`

**Query params**: `duration_minutes` (default: 60)

#### POST /api/devices/{device_id}/resume-internet

Obnovení internetu.

**Headers**: `Authorization: Bearer <token>`

### Pravidla

#### POST /api/rules/

Vytvoření pravidla.

**Headers**: `Authorization: Bearer <token>`

**Request**:
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

**Response**: RuleResponse

#### GET /api/rules/device/{device_id}

Seznam pravidel pro zařízení.

**Headers**: `Authorization: Bearer <token>`

**Response**:
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

#### GET /api/rules/{rule_id}

Detail pravidla.

**Headers**: `Authorization: Bearer <token>`

#### PUT /api/rules/{rule_id}

Aktualizace pravidla.

**Headers**: `Authorization: Bearer <token>`

**Request**: Stejné jako POST /api/rules/

#### DELETE /api/rules/{rule_id}

Smazání pravidla.

**Headers**: `Authorization: Bearer <token>`

**Response**: 204 No Content

#### POST /api/rules/agent/fetch

Agent endpoint pro načtení pravidel.

**Request**:
```json
{
  "device_id": "uuid",
  "api_key": "uuid"
}
```

**Response**:
```json
{
  "rules": [...],
  "daily_usage": 3600,
  "usage_by_app": {
    "chrome": 1800,
    "steam": 1800
  }
}
```

### Reporty

#### POST /api/reports/agent/report

Agent endpoint pro odeslání statistik.

**Request**:
```json
{
  "device_id": "uuid",
  "api_key": "uuid",
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

**Response**:
```json
{
  "status": "success",
  "logs_received": 10,
  "last_seen": "2024-01-01T12:00:00Z"
}
```

#### POST /api/reports/agent/critical-event

Kritické události (limit exceeded, atd.).

**Request**:
```json
{
  "device_id": "uuid",
  "api_key": "uuid",
  "event_type": "limit_exceeded",
  "app_name": "steam",
  "used_seconds": 3600,
  "limit_seconds": 1800
}
```

#### GET /api/reports/device/{device_id}/summary

Souhrn statistik zařízení.

**Headers**: `Authorization: Bearer <token>`

**Response**:
```json
{
  "device_id": 1,
  "device_name": "Dětský počítač",
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
  "running_processes": ["chrome", "steam"]
}
```

#### GET /api/reports/device/{device_id}/usage-by-hour

Použití po hodinách (heatmap data).

**Headers**: `Authorization: Bearer <token>`

**Query params**: `days` (default: 7, max: 14)

**Response**:
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

#### GET /api/reports/device/{device_id}/usage-trends

Trendy použití.

**Headers**: `Authorization: Bearer <token>`

**Query params**: `period` ("week" nebo "month")

#### GET /api/reports/device/{device_id}/weekly-pattern

Týdenní vzory použití.

**Headers**: `Authorization: Bearer <token>`

**Query params**: `weeks` (default: 4, max: 8)

#### GET /api/reports/device/{device_id}/app-details

Detail aplikace.

**Headers**: `Authorization: Bearer <token>`

**Query params**: `app_name`, `days` (default: 7, max: 30)

### WebSocket

#### WS /api/ws/{user_id}

WebSocket připojení pro real-time aktualizace.

**Autentizace**: JWT token v query string nebo header

**Zprávy**:
- Příchozí: JSON zprávy
- Odchozí: Broadcast aktualizací

### Trust (SSL)

#### GET /api/trust/ca.crt

Stažení CA certifikátu.

**Response**: PEM certifikát

#### GET /api/trust/info

Informace o SSL konfiguraci.

**Response**:
```json
{
  "ca_subject": "...",
  "download_url": "https://.../api/trust/ca.crt",
  "qr_url": "https://.../api/trust/qr.png"
}
```

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

