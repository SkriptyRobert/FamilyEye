# Windows Agent dokumentace

## Přehled

Agent běží na Windows zařízení a monitoruje použití, vynucuje pravidla a odesílá statistiky na backend.

## Struktura

```
clients/windows/agent/
├── main.py              # Hlavní agent, orchestrace
├── config.py            # Konfigurace
├── monitor/             # Monitorování aplikací
│   ├── core.py
│   ├── process_tracking.py
│   └── ...
├── enforcer/            # Vynucování pravidel
│   ├── core.py
│   ├── app_blocking.py
│   └── ...
├── reporter.py          # Odesílání statistik
├── network_control.py   # Kontrola sítě
├── notifications.py     # Windows notifikace
├── boot_protection.py   # Ochrana při startu
└── logger.py            # Logging
```

## Instalace

### Manuální

```bash
cd clients/windows
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m agent.main
```

### Párování

Párování se provádí přes frontend dashboard nebo přímo přes API endpoint `/api/devices/pairing/pair`.

Pro manuální párování použijte:
- Frontend: Otevřete dashboard a použijte QR kód nebo manuální token
- API: POST request na `/api/devices/pairing/pair` s pairing tokenem, device_name, device_type, mac_address a device_id

Párování vytvoří zařízení v databázi a vrátí `device_id` a `api_key`, které se uloží do `config.json`.

## Konfigurace

**Soubor**: `clients/windows/config.json`

**Struktura**:
```json
{
  "backend_url": "https://192.168.1.100:8000",
  "device_id": "uuid-device-id",
  "api_key": "uuid-api-key",
  "polling_interval": 30,
  "reporting_interval": 300,
  "ssl_verify": false
}
```

**Proměnné prostředí**:
- `BACKEND_URL` - URL backendu
- `DEVICE_ID` - ID zařízení
- `API_KEY` - API klíč
- `AGENT_POLLING_INTERVAL` - Interval kontroly (sekundy)
- `AGENT_REPORTING_INTERVAL` - Interval reportování (sekundy)
- `AGENT_SSL_VERIFY` - Ověřování SSL certifikátů

## Moduly

### Main (`main.py`)

**Třída**: `ParentalControlAgent`

**Funkce**:
- Orchestrace všech modulů
- Spuštění/zastavení agenta
- Validace přihlašovacích údajů
- Thread management

**Thready**:
- `monitor_thread` - Monitorování aplikací
- `enforcer_thread` - Vynucování pravidel
- `reporter_thread` - Odesílání statistik

**Lifecycle**:
1. `start()` - Validace, spuštění threadů
2. `run()` - Hlavní smyčka
3. `stop()` - Zastavení všech threadů

### Monitor (`monitor/`)

**Hlavní modul**: `monitor/core.py`

**Třída**: `AppMonitor`

**Funkce**:
- Detekce spuštěných aplikací
- Sledování aktivních oken
- Měření času použití
- Konsolidace helper procesů

**Strategie detekce**:
1. **Viditelná okna** - Procesy s viditelnými okny
2. **CLI nástroje** - Cmd, PowerShell, Python, atd.
3. **Filtrování** - Ignorování systémových procesů
4. **Konsolidace** - Helper procesy → hlavní aplikace

**Ignorované procesy**:
- Systémové procesy (svchost, winlogon, atd.)
- Background služby
- Systémové UI (explorer, taskmgr, atd.)

**Helper mapping**:
- `steamwebhelper` → `steam`
- `discordptb` → `discord`
- `chrome_crashpad` → `chrome`
- atd.

### Enforcer (`enforcer/`)

**Hlavní modul**: `enforcer/core.py`

**Třída**: `RuleEnforcer`

**Funkce**:
- Načítání pravidel z backendu
- Vynucování blokování aplikací
- Kontrola časových limitů
- Kontrola denních limitů
- Kontrola časových oken
- Zamknutí zařízení
- Blokování sítě

**Typy pravidel**:
- `app_block` - Okamžité ukončení aplikace
- `time_limit` - Kontrola denního limitu pro aplikaci
- `daily_limit` - Kontrola celkového denního limitu
- `schedule` - Kontrola časového okna
- `lock_device` - Zamknutí zařízení
- `network_block` - Blokování internetu

**Vynucování**:
- **Blokování aplikací**: `taskkill` nebo `psutil.kill()`
- **Časové limity**: Kontrola použití vs. limit
- **Denní limit**: Kontrola celkového použití
- **Zamknutí**: `LockWorkStation()` nebo `WTSDisconnectSession()`
- **Blokování sítě**: Windows Firewall rules

**Notifikace**:
- Varování při 70% limitu
- Upozornění při překročení limitu
- Upozornění při blokování aplikace

### Reporter (`reporter.py`)

**Třída**: `UsageReporter`

**Funkce**:
- Shromažďování statistik z monitoru
- Odesílání reportů na backend
- Resetování denních statistik
- Error handling a retry

**Reportování**:
- Interval: 60 sekund (konfigurovatelné)
- Formát: JSON s usage_logs
- Endpoint: `POST /api/reports/agent/report`

**Data**:
- `app_name` - Název aplikace
- `duration` - Délka použití (sekundy)
- `timestamp` - Časová značka

### Network Control (`network_control.py`)

**Třída**: `NetworkController`

**Funkce**:
- Blokování webových stránek (hosts file)
- Blokování všech odchozích připojení
- Whitelist pro backend komunikaci
- Detekce VPN/proxy

**Metody**:
- `block_website()` - Blokování domény
- `unblock_website()` - Odblokování domény
- `block_all_outbound()` - Blokování všeho kromě whitelistu
- `unblock_all_outbound()` - Odstranění blokování
- `detect_vpn()` - Detekce VPN
- `detect_proxy()` - Detekce proxy

### Notifications (`notifications.py`)

**Třída**: `NotificationManager`

**Funkce**:
- Windows toast notifikace
- Popup okna
- Zvukové upozornění (případně)

**Typy notifikací**:
- `show_limit_warning()` - Varování před limitem
- `show_limit_exceeded()` - Limit překročen
- `show_daily_limit_warning()` - Varování denního limitu
- `show_daily_limit_exceeded()` - Denní limit překročen
- `show_app_blocked()` - Aplikace zablokována
- `show_outside_schedule()` - Mimo časové okno

### Boot Protection (`boot_protection.py`)

**Třída**: `BootProtection`

**Funkce**:
- Ochrana před odinstalací
- Automatické spuštění při bootu
- Kontrola integrity agenta

**Metody**:
- `start()` - Spuštění monitoru
- `stop()` - Zastavení monitoru
- `check_integrity()` - Kontrola integrity

## Lifecycle

### Start

1. Načtení konfigurace
2. Validace přihlašovacích údajů
3. Spuštění threadů:
   - Monitor (každých 5s)
   - Enforcer (každých 2s)
   - Reporter (každých 60s)
4. Spuštění boot protection

### Běh

- **Monitor**: Sleduje aplikace, aktualizuje statistiky
- **Enforcer**: Kontroluje pravidla, vynucuje akce
- **Reporter**: Odesílá statistiky na backend

### Stop

1. Zastavení všech threadů
2. Odeslání finálního reportu (případně)
3. Zastavení boot protection

## Komunikace s backendem

### Fetch Rules

**Endpoint**: `POST /api/rules/agent/fetch`

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

### Report Usage

**Endpoint**: `POST /api/reports/agent/report`

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

### Critical Event

**Endpoint**: `POST /api/reports/agent/critical-event`

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

## Error handling

### Network errors

- Retry s exponenciálním backoffem
- Offline režim (pravidla fungují i bez sítě)
- Logování chyb

### Authentication errors

- 401 → Zastavení agenta
- Požadavek na re-párování

### Process errors

- Ignorování přístupových chyb
- Logování chyb
- Pokračování v běhu

## Logging

**Soubor**: `agent.log`

**Úrovně**:
- INFO - Obecné informace
- WARNING - Varování
- ERROR - Chyby
- DEBUG - Ladění (pouze v dev módu)

**Formát**: Strukturované logy s kontextem

## Rozšíření

### Přidání nového typu pravidla

1. Přidat logiku do `enforcer/core.py`
2. Přidat do `_update_blocked_apps()` v `enforcer/app_blocking.py`
3. Přidat do `update()` smyčky v `enforcer/core.py`
4. Aktualizovat backend API

### Přidání nové detekce

1. Přidat do `monitor/core.py` nebo `monitor/process_tracking.py`
2. Aktualizovat `update()` metodu
3. Přidat do helper mapping (pokud potřeba)

### Přidání nové notifikace

1. Přidat metodu do `notifications.py`
2. Zavolat z `enforcer.py`
3. Přidat styling (případně)

## Produkční nasazení

Viz [DEPLOYMENT.md](./DEPLOYMENT.md) pro detailní návod na instalaci jako Windows služby.

