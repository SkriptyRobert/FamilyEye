# Databázové schéma

## Přehled

Systém používá SQLite jako výchozí databázi. Schéma je definováno pomocí SQLAlchemy ORM.

## Tabulky

### users

Uživatelé systému (rodiče a děti).

**Sloupce**:
- `id` (Integer, PK) - Primární klíč
- `email` (String, UNIQUE, INDEX) - E-mailová adresa
- `password_hash` (String) - Hash hesla (bcrypt/pbkdf2)
- `role` (String) - Role: "parent" nebo "child"
- `created_at` (DateTime) - Datum vytvoření

**Vztahy**:
- `parent_devices` - Zařízení, kde je uživatel rodič
- `child_devices` - Zařízení, kde je uživatel dítě

**Indexy**:
- `email` - Pro rychlé vyhledávání

### devices

Spravovaná zařízení.

**Sloupce**:
- `id` (Integer, PK) - Primární klíč
- `name` (String) - Název zařízení
- `device_type` (String) - Typ: "windows", "android", atd.
- `mac_address` (String, UNIQUE, INDEX) - MAC adresa
- `device_id` (String, UNIQUE, INDEX) - Unikátní ID zařízení (UUID)
- `parent_id` (Integer, FK → users.id) - ID rodiče
- `child_id` (Integer, FK → users.id, NULL) - ID dítěte (volitelné)
- `api_key` (String, UNIQUE, INDEX) - API klíč pro autentizaci agenta
- `paired_at` (DateTime) - Datum párování
- `last_seen` (DateTime, NULL) - Poslední aktivita
- `is_active` (Boolean) - Aktivní zařízení
- `current_processes` (Text, NULL) - JSON seznam běžících procesů

**Vztahy**:
- `parent` - Rodič (User)
- `child` - Dítě (User, volitelné)
- `rules` - Pravidla pro zařízení
- `usage_logs` - Logy použití

**Indexy**:
- `mac_address` - Pro rychlé vyhledávání
- `device_id` - Pro autentizaci agenta
- `api_key` - Pro autentizaci agenta

**Properties**:
- `is_online` - Online pokud `last_seen` < 5 minut
- `has_lock_rule` - Má aktivní pravidlo zamknutí
- `has_network_block` - Má aktivní blokování sítě

### rules

Pravidla pro zařízení.

**Sloupce**:
- `id` (Integer, PK) - Primární klíč
- `device_id` (Integer, FK → devices.id) - ID zařízení
- `rule_type` (String) - Typ pravidla
- `app_name` (String, NULL) - Název aplikace (pro app_block, time_limit)
- `website_url` (String, NULL) - URL webu (pro website_block)
- `time_limit` (Integer, NULL) - Časový limit v minutách
- `enabled` (Boolean) - Aktivní pravidlo
- `schedule_start_time` (String, NULL) - Čas začátku (HH:MM)
- `schedule_end_time` (String, NULL) - Čas konce (HH:MM)
- `schedule_days` (String, NULL) - Dny v týdnu (0,1,2,3,4,5,6)
- `block_network` (Boolean) - Blokovat síť pro aplikaci
- `created_at` (DateTime) - Datum vytvoření
- `updated_at` (DateTime, NULL) - Datum aktualizace

**Vztahy**:
- `device` - Zařízení

**Typy pravidel**:
- `app_block` - Blokování aplikace
- `time_limit` - Časový limit pro aplikaci
- `daily_limit` - Denní limit pro celé zařízení
- `schedule` - Časové okno
- `lock_device` - Zamknutí zařízení
- `network_block` - Blokování sítě
- `website_block` - Blokování webu

### usage_logs

Logy použití zařízení.

**Sloupce**:
- `id` (Integer, PK) - Primární klíč
- `device_id` (Integer, FK → devices.id) - ID zařízení
- `app_name` (String) - Název aplikace
- `duration` (Integer) - Délka použití v sekundách
- `timestamp` (DateTime, INDEX) - Časová značka

**Vztahy**:
- `device` - Zařízení

**Indexy**:
- `timestamp` - Pro rychlé dotazy podle času
- `idx_usage_device_timestamp` - Kompozitní index (device_id, timestamp)
- `idx_usage_device_app` - Kompozitní index (device_id, app_name)

**Optimalizace**:
- Agregace na databázové úrovni
- Indexy pro rychlé dotazy
- Pravidelné čištění starých logů

### pairing_tokens

Dočasné tokeny pro párování zařízení.

**Sloupce**:
- `id` (Integer, PK) - Primární klíč
- `token` (String, UNIQUE, INDEX) - Pairing token (UUID)
- `parent_id` (Integer, FK → users.id) - ID rodiče
- `device_id` (Integer, FK → devices.id, NULL) - ID zařízení (po párování)
- `expires_at` (DateTime) - Datum expirace
- `used` (Boolean) - Použitý token
- `created_at` (DateTime) - Datum vytvoření

**Vztahy**:
- `parent` - Rodič
- `device` - Zařízení (po párování)

**Indexy**:
- `token` - Pro rychlé vyhledávání

**Platnost**: 5 minut (konfigurovatelné)

## Vztahy

```
users (parent)
  └── devices (parent_id)
       ├── rules (device_id)
       └── usage_logs (device_id)

users (child)
  └── devices (child_id)

pairing_tokens
  ├── users (parent_id)
  └── devices (device_id)
```

## Migrace

Aktuálně není použito Alembic. Tabulky se vytváří automaticky při startu (`init_db()`).

**Pro produkci**: Doporučeno použít Alembic pro migrace.

## Optimalizace

### Indexy

- Unikátní indexy na `email`, `mac_address`, `device_id`, `api_key`
- Kompozitní indexy na `usage_logs` pro rychlé dotazy
- Indexy na `timestamp` pro časové dotazy

### Dotazy

- Agregace na databázové úrovni (SUM, COUNT, GROUP BY)
- Limitování výsledků
- Použití LIKE pro datumové dotazy (SQLite)

### Cache

- Statistiky jsou cachovány (5-10 minut)
- Pravidla jsou cachovány (30 sekund)

### Údržba

- Pravidelné čištění starých logů (90+ dní)
- Pravidelné čištění expirovaných pairing tokenů

## Backup

**SQLite**: Zkopírovat soubor `parental_control.db`

**Doporučení**:
- Pravidelné zálohování
- Automatické zálohy před migracemi
- Offsite zálohy

## Produkční databáze

Pro produkci doporučeno použít:
- **PostgreSQL** - Pro větší zátěž
- **MySQL** - Alternativa
- **SQLite** - Pouze pro malé nasazení

**Migrace**:
1. Změnit `DATABASE_URL` v `config.py`
2. Aktualizovat connection string
3. Spustit migrace (Alembic)

## Příklady dotazů

### SQL

```sql
-- Použití zařízení dnes
SELECT app_name, SUM(duration) as total
FROM usage_logs
WHERE device_id = 1
  AND DATE(timestamp) = DATE('now')
GROUP BY app_name;

-- Aktivní pravidla
SELECT * FROM rules
WHERE device_id = 1 AND enabled = 1;

-- Online zařízení
SELECT * FROM devices
WHERE last_seen > datetime('now', '-5 minutes');
```

### SQLAlchemy

```python
from app.database import get_db
from app.models import UsageLog, Device

# Použití zařízení dnes
db = next(get_db())
today_usage = db.query(UsageLog).filter(
    UsageLog.device_id == 1,
    func.date(UsageLog.timestamp) == date.today()
).all()
```

