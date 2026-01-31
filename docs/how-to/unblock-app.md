# Unblock App - Jak odblokovat aplikaci

Průvodce pro odblokování aplikace, která byla zablokována pravidlem.

## Dočasné odblokování

### Z webového rozhraní

1. Přihlaste se do webového rozhraní
2. Vyberte zařízení
3. Přejděte na **Pravidla**
4. Najděte pravidlo blokující aplikaci
5. Klepněte na **"Dočasně povolit"**
6. Nastavte dobu (např. 30 minut, 1 hodina)
7. Uložte

**Co se stane:**
- Pravidlo je dočasně deaktivováno (`enabled = false`)
- Po uplynutí doby se automaticky znovu aktivuje
- Aplikace může být používána po dobu povolení

### Z Android aplikace (s PINem)

1. Na telefonu otevřete aplikaci Smart Shield
2. Zadejte **PIN pro admin přístup**
3. Přejděte na **Pravidla**
4. Najděte pravidlo blokující aplikaci
5. Klepněte na **"Dočasně povolit"**
6. Nastavte dobu
7. Uložte

## Trvalé odblokování

### Smazání pravidla

1. V webovém rozhraní přejděte na **Pravidla**
2. Najděte pravidlo blokující aplikaci
3. Klepněte na **"Smazat"**
4. Potvrďte smazání

**Co se stane:**
- Pravidlo je trvale smazáno z databáze
- Aplikace je okamžitě odblokována
- WebSocket příkaz `REFRESH_RULES` je odeslán na zařízení

**API**: `DELETE /api/rules/{rule_id}`

### Deaktivace pravidla (bez smazání)

1. V webovém rozhraní přejděte na **Pravidla**
2. Najděte pravidlo blokující aplikaci
3. Klepněte na **"Vypnout"** (toggle enabled)
4. Pravidlo je deaktivováno, ale zachováno v databázi

**Co se stane:**
- `enabled = false` v databázi
- Aplikace je odblokována
- Pravidlo může být později znovu aktivováno

**API**: `PUT /api/rules/{rule_id}` - nastavit `enabled: false`

## Typy blokování a jejich odblokování

### App Block (Blokování aplikace)

**Odblokování**: Smazání nebo deaktivace pravidla typu `app_block`

**Co se stane po odblokování:**
- Overlay s blokací zmizí
- Aplikace může být spuštěna normálně

### Time Limit (Časový limit)

**Odblokování**: 
- Smazání pravidla
- Nebo zvýšení limitu (upravit `time_limit`)

**Co se stane po odblokování:**
- Aplikace může být používána bez limitu (nebo s novým limitem)
- Limit se resetuje o půlnoci

### Schedule (Časové okno)

**Odblokování**: 
- Smazání pravidla
- Nebo úprava časového okna (změnit `schedule_start_time` / `schedule_end_time`)

**Co se stane po odblokování:**
- Aplikace může být používána v jakoukoliv dobu

## Technické detaily

### Enforcement proces

Když je aplikace blokována:

1. `AppDetectorService` detekuje spuštění aplikace
2. `EnforcementService` zkontroluje pravidla
3. Pokud je aplikace blokována, zobrazí se `BlockOverlay`
4. Aplikace je pozastavena (`ActivityManager.moveTaskToBack()`)

**Zdroj**: `clients/android/app/src/main/java/com/familyeye/agent/enforcement/EnforcementService.kt`

### Odblokování proces

Když je pravidlo smazáno nebo deaktivováno:

1. Backend smaže/deaktivuje pravidlo v databázi
2. WebSocket příkaz `REFRESH_RULES` je odeslán
3. Android aplikace stáhne aktualizovaná pravidla
4. Při příštím pokusu o spuštění aplikace není blokována

**Zdroj**: `backend/app/api/rules.py:delete_rule()`
