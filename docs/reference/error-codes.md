# Error Codes - Seznam chybových kódů

Kompletní seznam všech chybových kódů Smart Shield API s vysvětlením a řešením.

## HTTP Status Codes

### 200 OK
**Význam**: Požadavek byl úspěšně zpracován

**Příklady**:
- `GET /api/devices/` - Seznam zařízení
- `POST /api/devices/{device_id}/lock` - Zamknutí zařízení

### 201 Created
**Význam**: Nový zdroj byl úspěšně vytvořen

**Příklady**:
- `POST /api/auth/register` - Registrace uživatele
- `POST /api/rules/` - Vytvoření pravidla
- `POST /api/shield/alert` - Report alertu

### 400 Bad Request
**Význam**: Neplatný požadavek (chybné parametry)

**Příklady**:
- Neplatný email při registraci
- Chybějící povinná pole
- Neplatný PIN (méně než 4 číslice)

**Řešení**: Zkontrolujte request body podle API dokumentace

### 401 Unauthorized
**Význam**: Neplatná autentizace

**Příklady**:
- Neplatný JWT token
- Expirovaný token
- Neplatný API key (agent)

**Řešení**: 
- Pro rodiče: Přihlaste se znovu (`POST /api/auth/login`)
- Pro agenty: Zkontrolujte `api_key` v request body

### 403 Forbidden
**Význam**: Přístup odepřen (autorizace)

**Příklady**:
- Pokus o přístup k zařízení jiného rodiče
- Pokus o smazání alertu jiného zařízení

**Řešení**: Zkontrolujte, zda máte oprávnění k danému zdroji

### 404 Not Found
**Význam**: Zdroj nenalezen

**Příklady**:
- Neexistující `device_id`
- Neexistující `rule_id`
- Neexistující pairing token

**Řešení**: Zkontrolujte, zda ID existuje v databázi

### 422 Unprocessable Entity
**Význam**: Neplatná data (validace)

**Příklady**:
- Chybný JSON formát
- Neplatný email formát
- Neplatný datový typ (např. string místo number)

**Řešení**: Zkontrolujte request body podle Pydantic schémat

### 429 Too Many Requests
**Význam**: Příliš mnoho požadavků (rate limit)

**Příklady**:
- Více než 3 registrace za minutu
- Více než 5 login pokusů za minutu

**Řešení**: Počkejte a zkuste znovu po uplynutí rate limit okna

### 500 Internal Server Error
**Význam**: Chyba na serveru

**Příklady**:
- Chyba databáze
- Neočekávaná výjimka

**Řešení**: Kontaktujte podporu nebo zkontrolujte server logy

## Device Owner Specifické chyby

### "Device owner is already set"
**Význam**: Device Owner již byl nastaven na zařízení

**Řešení**: 
- Pokud je to Smart Shield, můžete pokračovat
- Pokud je to jiná aplikace, musíte ji nejprve odebrat (factory reset)

### "Not allowed to set device owner"
**Význam**: Device Owner nelze nastavit

**Možné příčiny**:
1. **Na zařízení jsou účty** - Odeberte všechny účty
2. **Zařízení již má Device Owner** - Odeberte existující Device Owner
3. **Zařízení není prázdné** - Factory reset

**Řešení**: Viz [Getting Started](tutorials/getting-started.md) - Krok 1

### "SecurityException" nebo "Permission denied" (Xiaomi)
**Význam**: Xiaomi/HyperOS vyžaduje dodatečné nastavení

**Řešení**: 
1. V **Možnostech pro vývojáře** zapněte **"Ladění USB (Bezpečnostní nastavení)"**
2. Zkuste znovu aktivaci

**Zdroj**: [Troubleshoot USB](how-to/troubleshoot-usb.md)

## WebADB chyby

### "WebUSB není v tomto prohlížeči podporováno"
**Význam**: Prohlížeč nepodporuje WebUSB API

**Řešení**: Použijte Chrome nebo Edge (Firefox nepodporuje WebUSB)

### "Nebylo vybráno žádné zařízení"
**Význam**: Uživatel nezvolil zařízení v dialogu

**Řešení**: Zkuste znovu a vyberte zařízení v dialogu

### "Zařízení je používáno jiným programem"
**Význam**: ADB server běží na PC

**Řešení**: 
1. Zavřete všechny ADB terminály
2. Spusťte: `adb kill-server`
3. Zkuste znovu

### "Timeout: Zařízení neodpovídá"
**Význam**: Zařízení neodpovídá na ADB příkaz do 10 sekund

**Řešení**:
1. Zkontrolujte telefon (může být dialog k potvrzení)
2. Odemkněte telefon
3. Zkuste znovu

## Smart Shield chyby

### "alert_deduplicated_instant"
**Význam**: Alert byl zablokován (duplikát do 5 sekund)

**Chování**: Alert se neuloží do databáze (spam prevention)

### "alert_deduplicated_cooldown"
**Význam**: Alert byl zablokován (5minutový cooldown po burst)

**Chování**: Alert se neuloží do databáze (burst prevention)

**Zdroj**: `backend/app/api/shield.py:report_alert()` - Spam prevention logic

## API Error Responses

### Formát chybové odpovědi

```json
{
  "detail": "Error message here"
}
```

### Příklady

**401 Unauthorized**:
```json
{
  "detail": "Could not validate credentials"
}
```

**404 Not Found**:
```json
{
  "detail": "Device not found"
}
```

**422 Unprocessable Entity**:
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

## Technické reference

- Backend error handling: `backend/app/api/*.py` - HTTPException
- WebADB error handling: `frontend/src/components/DeviceOwnerSetup.jsx`
- Rate limiting: `backend/app/rate_limiter.py`
