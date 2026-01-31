# Troubleshoot USB - Řešení problémů s připojením

Průvodce řešením problémů s WebADB připojením při aktivaci Device Owner.

## Zařízení není vidět v prohlížeči

### Příčina
Prohlížeč nemůže detekovat zařízení přes WebUSB API.

### Řešení

1. **Zkontrolujte USB kabel**
   - Použijte **datový kabel** (ne pouze nabíjecí)
   - Zkuste jiný kabel

2. **Zkontrolujte USB debugging**
   - V **Možnostech pro vývojáře** musí být zapnuto **Ladění USB**
   - Na telefonu se musí zobrazit dialog **"Povolit ladění USB?"**

3. **Zkontrolujte prohlížeč**
   - Použijte **Chrome** nebo **Edge** (WebUSB API podporu)
   - Firefox WebUSB nepodporuje

4. **Zkuste jiný USB port**
   - Některé USB porty nemusí podporovat WebUSB

## Chyba: "Access denied" nebo "Přístup odepřen"

### Příčina
Uživatel nepotvrdil dialog "Povolit ladění USB" na telefonu.

### Řešení

1. **Na telefonu:**
   - Zkontrolujte, zda se zobrazil dialog **"Povolit ladění USB?"**
   - Zaškrtněte **"Vždy povolit z tohoto počítače"**
   - Klepněte na **Povolit**

2. **Zkuste znovu:**
   - Odpojte a znovu připojte kabel
   - V prohlížeči zkuste znovu připojit zařízení

## Chyba: "Zařízení je používáno jiným programem"

### Příčina
ADB server běží na PC a blokuje WebUSB přístup.

### Řešení

1. **Zavřete všechny ADB terminály**
   - Zavřete všechny okna terminálu s ADB příkazy

2. **Zastavte ADB server:**
   ```bash
   adb kill-server
   ```

3. **Zkuste znovu připojit** v prohlížeči

!!! tip "Poznámka"
    WebADB a ADB server na PC se vzájemně vylučují. Použijte buď WebADB (v prohlížeči) nebo ADB na PC, ne obojí současně.

## Xiaomi/HyperOS: "SecurityException" nebo "Permission denied"

### Příčina
Xiaomi a HyperOS mají dodatečné bezpečnostní nastavení pro USB debugging.

### Řešení

1. **V Možnostech pro vývojáře:**
   - Zapněte **Ladění USB**
   - **KRITICKÉ**: Zapněte **Ladění USB (Bezpečnostní nastavení)**
   - Toto je **jiné** nastavení než běžné "Ladění USB"

2. **Cesta k nastavení:**
   - Nastavení → O telefonu → Číslo sestavení (7x klepnutí)
   - Nastavení → Možnosti pro vývojáře
   - Najděte **"Ladění USB (Bezpečnostní nastavení)"**
   - Zapněte ho

3. **Zkuste znovu** aktivaci Device Owner

!!! warning "Důležité"
    Bez zapnutí "Ladění USB (Bezpečnostní nastavení)" WebADB **nebude fungovat** na Xiaomi/HyperOS zařízeních.

## Chyba: "Timeout: Zařízení neodpovídá"

### Příčina
Zařízení neodpovídá na ADB příkaz do 10 sekund.

### Řešení

1. **Zkontrolujte telefon:**
   - Může se zobrazit dialog, který je potřeba potvrdit
   - Odemkněte telefon (pokud je zamčený)

2. **Zkuste znovu:**
   - Odpojte a znovu připojte kabel
   - Zkuste aktivaci znovu

3. **Zkontrolujte USB debugging:**
   - Ujistěte se, že je stále zapnuto
   - Na některých zařízeních se může automaticky vypnout

## Chyba: "Na zařízení jsou stále přihlášené účty"

### Příčina
Device Owner vyžaduje prázdné zařízení bez účtů.

### Řešení

1. **Odeberte všechny účty:**
   - Nastavení → Účty
   - Odstraňte **všechny účty** (Google, Xiaomi, Samsung, atd.)

2. **Zkontrolujte znovu:**
   - Ujistěte se, že žádný účet nezůstal

3. **Zkuste znovu** aktivaci Device Owner

!!! danger "Pozor"
    Před odebráním účtů si zálohujte důležitá data (fotky, kontakty).

## Chyba: "ADB subprocess protocol not supported"

### Příčina
Zařízení nepodporuje ADB shell protokol používaný WebADB.

### Řešení

1. **Zkuste jiný prohlížeč:**
   - Chrome nebo Edge
   - Firefox nepodporuje WebUSB

2. **Zkontrolujte Android verzi:**
   - WebADB vyžaduje Android 5.0+
   - Starší verze nemusí být podporovány

3. **Zkuste aktualizovat prohlížeč:**
   - Použijte nejnovější verzi Chrome/Edge

## Obecné tipy

1. **Restart zařízení:**
   - Někdy pomůže restart telefonu před připojením

2. **Restart prohlížeče:**
   - Zavřete a znovu otevřete prohlížeč

3. **Zkuste jiný počítač:**
   - Některé počítače mohou mít problémy s WebUSB

4. **Kontrola kabelu:**
   - Použijte originální kabel
   - Zkuste jiný kabel

## Technické detaily

### WebUSB API

WebADB používá **WebUSB API** pro komunikaci s Android zařízením:

1. Prohlížeč požádá o přístup k USB zařízení
2. Uživatel vybere zařízení v dialogu
3. Prohlížeč komunikuje s ADB daemonem přes USB
4. ADB příkazy se spouštějí přímo z prohlížeče

**Zdroj**: `frontend/src/components/DeviceOwnerSetup.jsx:handleConnect()`

### ADB kill-server

Pokud ADB server běží na PC, blokuje WebUSB přístup. Příkaz `adb kill-server` zastaví ADB server a uvolní USB zařízení pro WebUSB.

**Zdroj**: `frontend/src/components/DeviceOwnerSetup.jsx` - Error handling
