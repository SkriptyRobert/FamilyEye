# Change PIN - Jak změnit PIN

Průvodce pro změnu PINu v Android aplikaci Smart Shield.

## Změna PINu z Android aplikace

1. Na telefonu otevřete aplikaci Smart Shield
2. Zadejte **aktuální PIN**
3. Přejděte na **Nastavení**
4. Najděte **"Změnit PIN"**
5. Zadejte **nový PIN** (4-6 číslic)
6. Potvrďte nový PIN
7. PIN je změněn

## Změna PINu z webového rozhraní (vzdáleně)

1. Přihlaste se do webového rozhraní
2. Vyberte zařízení
3. Přejděte na **Nastavení zařízení**
4. Najděte **"Resetovat PIN"**
5. Zadejte **nový PIN** (4-6 číslic)
6. Potvrďte změnu

**Co se stane:**
- WebSocket příkaz `RESET_PIN:{new_pin}` je odeslán na zařízení
- Android aplikace nastaví nový PIN
- Nový PIN je okamžitě aktivní

**API**: `POST /api/devices/{device_id}/reset-pin`

**Request Body**:
```json
{
  "new_pin": "1234"
}
```

## Požadavky na PIN

- **Délka**: 4-6 číslic
- **Formát**: Pouze číslice (0-9)
- **Validace**: Backend validuje formát před odesláním

## Zapomenutý PIN

Pokud jste zapomněli PIN:

1. **Z webového rozhraní**: Použijte funkci "Resetovat PIN" (vyžaduje přihlášení)
2. **Factory reset**: Vymaže všechna data včetně PINu (extrémní řešení)

!!! warning "Důležité"
    Pokud zapomenete PIN a nemáte přístup k webovému rozhraní, jediným řešením je factory reset, který vymaže všechna data.

## Technické detaily

### Ukládání PINu

PIN je uložen lokálně v Android aplikaci pomocí `SharedPreferences` s šifrováním.

**Zdroj**: Android aplikace - PIN management

### WebSocket příkaz

```
RESET_PIN:1234
```

Android aplikace parsuje tento příkaz a nastaví nový PIN.

**Zdroj**: `backend/app/api/devices/actions.py:reset_pin()`
