# Getting Started - Instalace Smart Shield

Tento průvodce vás provede kompletním procesem instalace a aktivace Smart Shield na Android zařízení vašeho dítěte. Celý proces trvá přibližně 10-15 minut.

!!! warning "Důležité: Device Owner vyžaduje prázdné zařízení"
    Pro aktivaci Device Owner ochrany **musíte odebrat všechny účty** (Google, Xiaomi, Samsung atd.) z telefonu. Toto je bezpečnostní požadavek Androidu - Device Owner může být aktivován pouze na zařízení bez uživatelských účtů.

## Krok 1: Příprava telefonu

### 1.1 Odebrání účtů

!!! tip "Proč je to potřeba?"
    Android Device Owner API vyžaduje, aby zařízení bylo "prázdné" - bez jakýchkoliv uživatelských účtů. Toto je bezpečnostní opatření, které zajišťuje, že Device Owner aplikace má plnou kontrolu nad zařízením.

**Postup:**

1. Otevřete **Nastavení** na telefonu
2. Přejděte na **Účty** (nebo **Účty a synchronizace**)
3. Odstraňte **všechny účty**:
   - Google účet
   - Xiaomi účet (pokud máte Xiaomi/HyperOS)
   - Samsung účet (pokud máte Samsung)
   - Jakékoliv jiné účty

4. Potvrďte odebrání účtů

!!! danger "Pozor na zálohování"
    Před odebráním účtů si zálohujte důležitá data (fotky, kontakty). Po aktivaci Device Owner můžete účty znovu přidat, ale některá data mohou být ztracena.

### 1.2 Zapnutí USB debuggingu

1. Otevřete **Nastavení**
2. Přejděte na **O telefonu** (nebo **O zařízení**)
3. Najděte **Číslo sestavení** a klepněte na něj **7x** (zobrazí se zpráva "Jste nyní vývojář")
4. Vraťte se do **Nastavení** a otevřete **Možnosti pro vývojáře**
5. Zapněte **Ladění USB**

!!! info "Xiaomi/HyperOS speciální nastavení"
    Na zařízeních Xiaomi nebo HyperOS musíte navíc zapnout:
    - **Ladění USB (Bezpečnostní nastavení)** - Toto je kritické! Bez tohoto nastavení nebude WebADB fungovat.

### 1.3 OEM Unlock (volitelné)

OEM Unlock je potřeba pouze pokud:
- Chcete odemknout bootloader (většinou není potřeba)
- Zařízení vyžaduje odemknutí pro Device Owner

**Postup:**
1. V **Možnostech pro vývojáře** najděte **OEM odemknutí**
2. Zapněte ho (pokud je k dispozici)

## Krok 2: WebADB připojení

### 2.1 Co je WebADB?

WebADB je technologie, která umožňuje komunikaci s Android zařízením přímo z webového prohlížeče pomocí **WebUSB API**. 

!!! tip "Výhody WebADB"
    - **Nic se neinstaluje do PC** - vše běží v prohlížeči
    - **Bezpečné** - komunikace probíhá přes USB kabel
    - **Jednoduché** - není potřeba instalovat ADB nástroje

**Jak to funguje:**
1. Prohlížeč požádá o přístup k USB zařízení
2. Uživatel vybere telefon v dialogu
3. Prohlížeč komunikuje s telefonem pomocí ADB protokolu přes USB
4. Frontend komponenta `DeviceOwnerSetup.jsx` spustí ADB příkaz

### 2.2 Připojení kabelu a výběr zařízení

1. Připojte telefon k počítači pomocí **USB kabelu**
2. Na telefonu se zobrazí dialog **"Povolit ladění USB?"**
3. Zaškrtněte **"Vždy povolit z tohoto počítače"** a klepněte na **Povolit**
4. V prohlížeči otevřete webové rozhraní Smart Shield
5. Přejděte na **Device Owner Setup**
6. Klepněte na **"Připojit zařízení"**
7. V dialogu vyberte váš telefon

!!! warning "Chyba: Zařízení je používáno jiným programem"
    Pokud se zobrazí tato chyba:
    1. Zavřete všechny ADB terminály na PC
    2. Spusťte v terminálu: `adb kill-server`
    3. Zkuste znovu připojit

## Krok 3: Aktivace Device Owner

### 3.1 ADB příkaz `dpm set-device-owner`

Po úspěšném připojení WebADB spustí frontend komponenta následující ADB příkaz:

```bash
dpm set-device-owner com.familyeye.agent/.receiver.FamilyEyeDeviceAdmin
```

**Co tento příkaz dělá:**
- `dpm` = Device Policy Manager (systémový nástroj Androidu)
- `set-device-owner` = Nastaví aplikaci jako Device Owner
- `com.familyeye.agent` = Package name aplikace Smart Shield
- `.receiver.FamilyEyeDeviceAdmin` = Device Admin Receiver třída

**Co se stane po aktivaci:**
1. Android systém zavolá callback `onProfileProvisioningComplete()` v `FamilyEyeDeviceAdmin.kt`
2. Aplikace aktivuje Device Owner oprávnění:
   - `setUninstallBlocked(true)` - Blokování odinstalace
   - `applyBaselineRestrictions()` - Aplikace základních restrikcí
   - `setPackagesSuspended()` - Ochrana Settings aplikací

### 3.2 Proces aktivace

1. Po připojení zařízení klepněte na **"Aktivovat Device Owner"**
2. Frontend spustí ADB příkaz a zobrazí výstup v terminálu
3. Pokud je vše v pořádku, zobrazí se zpráva **"Success"** nebo prázdný výstup
4. Pokud se zobrazí chyba, viz [Troubleshooting USB](how-to/troubleshoot-usb.md)

!!! success "Úspěšná aktivace"
    Po úspěšné aktivaci:
    - Aplikace Smart Shield se stane Device Owner
    - Nelze ji odinstalovat bez deaktivace Device Owner
    - Aplikace má plnou kontrolu nad zařízením

## Krok 4: Prvotní nastavení

### 4.1 Párování zařízení s backendem

1. Po aktivaci Device Owner se otevře **Pairing Screen** na telefonu
2. V webovém rozhraní vygenerujte **Pairing Token**
3. Naskenujte **QR kód** nebo zadejte token ručně
4. Telefon se připojí k backendu a získá `api_key`

**Co se děje na pozadí:**
- Frontend volá `POST /api/devices/pairing/token` - vytvoří pairing token (expirace 5 minut)
- Android aplikace volá `POST /api/devices/pairing/pair` - páruje zařízení
- Backend vrací `api_key` pro budoucí komunikaci

### 4.2 Nastavení PINu

1. V aplikaci na telefonu nastavte **PIN pro admin přístup**
2. Tento PIN je potřeba pro:
   - Změnu nastavení
   - Deaktivaci ochran
   - Odstranění Device Owner

### 4.3 Základní konfigurace Smart Shield

1. V webovém rozhraní přejděte na **Smart Shield**
2. Přidejte klíčová slova pro monitoring (výchozí jsou již nastavena)
3. Nastavte kategorie:
   - **Self-harm** (critical) - sebevražda, zabít se
   - **Drugs** (high) - drogy, pervitin
   - **Bullying** (high) - šikana, chcípni
   - **Adult** (high) - porno, xxx

## Co dál?

- [First Setup](first-setup.md) - Prvotní konfigurace aplikace
- [Troubleshoot USB](how-to/troubleshoot-usb.md) - Řešení problémů s připojením
- [Feature Matrix](reference/feature-matrix.md) - Kompletní přehled funkcí

## Technické detaily

### Frontend komponenta: DeviceOwnerSetup.jsx

Komponenta `frontend/src/components/DeviceOwnerSetup.jsx` implementuje celý WebADB flow:

1. **handleConnect()** - Připojení pomocí `AdbDaemonWebUsbDeviceManager`
2. **handleActivate()** - Spuštění ADB příkazu `dpm set-device-owner`
3. **Error handling** - Lokalizace chybových hlášek (Xiaomi, Account errors)

### Android callback: FamilyEyeDeviceAdmin.kt

Po úspěšné aktivaci se zavolá:

```kotlin
override fun onProfileProvisioningComplete(context: Context, intent: Intent) {
    val enforcer = DeviceOwnerPolicyEnforcer.create(context)
    enforcer.onDeviceOwnerActivated()
    // Aktivuje všechny ochrany
}
```

Viz [Security Model](architecture/security-model.md) pro detailní popis ochran.
