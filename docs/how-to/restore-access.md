# Restore Access - Jak vrátit dítěti přístup

Průvodce pro obnovení přístupu dítěte k zařízení po dočasném zamčení nebo blokování.

## Odemknutí zařízení

### Z webového rozhraní

1. Přihlaste se do webového rozhraní Smart Shield
2. Vyberte zařízení dítěte
3. Klepněte na **"Odemknout zařízení"**
4. Zařízení je okamžitě odemčeno

**Co se stane:**
- Všechna `lock_device` pravidla jsou smazána z databáze
- WebSocket příkaz `UNLOCK_NOW` je odeslán na zařízení
- Android aplikace odemkne zařízení

**API**: `POST /api/devices/{device_id}/unlock`

### Z Android aplikace (s PINem)

1. Na telefonu otevřete aplikaci Smart Shield
2. Zadejte **PIN pro admin přístup**
3. Přejděte na **Nastavení**
4. Klepněte na **"Odemknout zařízení"**

## Odblokování aplikace

### Dočasné odblokování

1. V webovém rozhraní přejděte na **Pravidla**
2. Najděte pravidlo blokující aplikaci
3. Klepněte na **"Dočasně povolit"**
4. Nastavte dobu (např. 30 minut)
5. Uložte

**Co se stane:**
- Pravidlo je dočasně deaktivováno
- Po uplynutí doby se automaticky znovu aktivuje

### Trvalé odblokování

1. V webovém rozhraní přejděte na **Pravidla**
2. Najděte pravidlo blokující aplikaci
3. Klepněte na **"Smazat"**
4. Potvrďte smazání

**Co se stane:**
- Pravidlo je trvale smazáno z databáze
- Aplikace je okamžitě odblokována

## Obnovení internetu

### Z webového rozhraní

1. Vyberte zařízení
2. Klepněte na **"Obnovit internet"**
3. Internet je okamžitě obnoven

**Co se stane:**
- Všechna `network_block` pravidla jsou smazána
- WebSocket příkaz `REFRESH_RULES` je odeslán
- Internet je okamžitě dostupný

**API**: `POST /api/devices/{device_id}/resume-internet`

## Odstranění časového limitu

1. V webovém rozhraní přejděte na **Pravidla**
2. Najděte pravidlo s časovým limitem
3. Klepněte na **"Smazat"** nebo **"Upravit"** (změnit limit)
4. Uložte změny

**Co se stane:**
- Pravidlo je smazáno/upraveno
- Aplikace může být používána bez limitu (nebo s novým limitem)

## Deaktivace Device Owner (pouze pro rodiče)

!!! danger "Varování"
    Deaktivace Device Owner **odstraní všechny ochrany** a umožní odinstalaci aplikace. Použijte pouze pokud chcete aplikaci zcela odebrat.

### Postup

1. Přihlaste se do webového rozhraní
2. Vyberte zařízení
3. Přejděte na **Nastavení zařízení**
4. Najděte **"Deaktivovat Device Owner"**
5. Zadejte **heslo** (pro bezpečnost)
6. Potvrďte deaktivaci

**Co se stane:**
- Všechny Device Owner restrikce jsou odstraněny
- `setUninstallBlocked(false)` - Aplikace může být odinstalována
- `clearBaselineRestrictions()` - Všechny restrikce jsou zrušeny
- `clearDeviceOwnerApp()` - Device Owner status je odstraněn

**API**: `POST /api/devices/{device_id}/deactivate-device-owner`

### Reaktivace Device Owner

Pokud chcete znovu aktivovat Device Owner ochranu:

1. V webovém rozhraní přejděte na **Nastavení zařízení**
2. Najděte **"Reaktivovat Device Owner"**
3. Zadejte **heslo**
4. Potvrďte reaktivaci

**Poznámka**: Zařízení musí stále být Device Owner na Android úrovni (pokud jste ho neodstranili factory resetem).

**API**: `POST /api/devices/{device_id}/reactivate-device-owner`

## Technické detaily

### Unlock proces

```kotlin
// Android aplikace
fun unlockDevice() {
    val lockRules = db.query(Rule).filter(
        Rule.rule_type == "lock_device"
    ).all()
    
    for (rule in lockRules) {
        db.delete(rule)
    }
    
    // Device is now unlocked
}
```

**Zdroj**: `clients/android/app/src/main/java/com/familyeye/agent/enforcement/EnforcementService.kt`

### WebSocket příkazy

Při obnovení přístupu se odesílají následující WebSocket příkazy:

- `UNLOCK_NOW` - Odemknutí zařízení
- `REFRESH_RULES` - Obnovení pravidel (odblokování aplikací)

**Zdroj**: `backend/app/api/websocket.py:send_command_to_device()`
