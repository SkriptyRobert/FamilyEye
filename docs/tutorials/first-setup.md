# First Setup - Prvotní nastavení

Průvodce prvotním nastavením Smart Shield po úspěšné aktivaci Device Owner.

## Krok 1: Prvotní přihlášení

1. Otevřete webové rozhraní Smart Shield v prohlížeči
2. Pokud ještě nemáte účet, [zaregistrujte se](../reference/api-docs.md#post-apiauthregister)
3. Přihlaste se pomocí emailu a hesla

## Krok 2: Přidání prvního zařízení

Po přihlášení se zobrazí prázdný dashboard.

1. Klepněte na **"Přidat zařízení"**
2. Vygenerujte **Pairing Token**
3. Na telefonu:
   - Otevřete aplikaci Smart Shield
   - Přejděte na **Pairing Screen**
   - Naskenujte **QR kód** nebo zadejte token ručně
4. Telefon se automaticky připojí k backendu

**Co se stane na pozadí:**
- Android aplikace volá `POST /api/devices/pairing/pair`
- Backend vytvoří zařízení v databázi
- Vrátí `api_key` pro budoucí komunikaci
- Výchozí klíčová slova Smart Shield jsou automaticky přidána

## Krok 3: Základní konfigurace Smart Shield

### 3.1 Přehled klíčových slov

Výchozí klíčová slova jsou automaticky přidána při párování:

**Self-harm (critical)**:
- sebevražda
- zabít se
- podřezat

**Drugs (high)**:
- drogy
- pervitin
- kokain
- tráva (medium)

**Bullying (high)**:
- šikana
- chcípni
- jsi nula (medium)
- nenávidím tě (medium)

**Adult (high)**:
- porno
- xxx
- onlyfans (medium)

### 3.2 Přidání vlastních klíčových slov

1. V webovém rozhraní přejděte na **Smart Shield → Nastavení slov**
2. V sekci **"Rychlé přidání"**:
   - Zadejte klíčové slovo (např. "gambling")
   - Vyberte kategorii
   - Klepněte na **Přidat**
3. Klíčové slovo je okamžitě odesláno na zařízení

**Technický detail:**
- Klíčové slovo je normalizováno na lowercase
- Android aplikace automaticky stáhne nová klíčová slova při příštím připojení

## Krok 4: Nastavení prvních pravidel

### 4.1 Časový limit pro aplikaci

1. V dashboardu vyberte zařízení
2. Přejděte na **Pravidla**
3. Klepněte na **"Přidat pravidlo"**
4. Vyberte **"Časový limit"**
5. Vyberte aplikaci (např. "Steam")
6. Nastavte limit (např. 60 minut denně)
7. Uložte

**Co se stane:**
- Pravidlo je uloženo do databáze
- WebSocket příkaz `REFRESH_RULES` je odeslán na zařízení
- Android aplikace stáhne nová pravidla
- Po dosažení limitu je aplikace automaticky blokována

### 4.2 Blokování aplikace

1. V **Pravidla** klepněte na **"Přidat pravidlo"**
2. Vyberte **"Blokování aplikace"**
3. Vyberte aplikaci (např. "TikTok")
4. Uložte

**Co se stane:**
- Aplikace je okamžitě blokována
- Při pokusu o spuštění se zobrazí overlay s vysvětlením

### 4.3 Denní limit

1. V **Pravidla** klepněte na **"Přidat pravidlo"**
2. Vyberte **"Denní limit"**
3. Nastavte limit (např. 2 hodiny denně pro celé zařízení)
4. Uložte

**Co se stane:**
- Po dosažení denního limitu jsou všechny aplikace blokovány
- Limit se resetuje o půlnoci (podle časového pásma zařízení)

## Krok 5: Nastavení PINu

1. Na telefonu otevřete aplikaci Smart Shield
2. Přejděte na **Nastavení**
3. Nastavte **PIN pro admin přístup**
4. Potvrďte PIN

**Použití PINu:**
- Změna nastavení aplikace
- Deaktivace ochran
- Odstranění Device Owner

!!! warning "Důležité"
    PIN si zapamatujte nebo zapište na bezpečné místo. Bez PINu nelze změnit nastavení aplikace.

## Co dál?

- [How-To Guides](../how-to/) - Řešení konkrétních úkolů
- [Feature Matrix](../reference/feature-matrix.md) - Kompletní přehled funkcí
- [API Documentation](../reference/api-docs.md) - Technická dokumentace

## Technické detaily

### Automatické přidání výchozích klíčových slov

Při párování zařízení backend automaticky:

1. Načte výchozí klíčová slova z `backend/app/config/smart_shield_defaults.json`
2. Vytvoří `ShieldKeyword` záznamy v databázi pro nové zařízení
3. Android aplikace je stáhne při příštím připojení

**Zdroj**: `backend/app/services/pairing_service.py`

### WebSocket notifikace

Při přidání nového pravidla nebo klíčového slova:

1. Backend uloží změnu do databáze
2. Odešle WebSocket příkaz `REFRESH_RULES` na zařízení
3. Android aplikace stáhne aktualizovaná pravidla/klíčová slova
4. Změny jsou okamžitě aktivní

**Zdroj**: `backend/app/api/rules.py:create_rule()`
