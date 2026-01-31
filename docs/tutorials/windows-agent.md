# Instalace Windows Agenta

Kompletní průvodce instalací FamilyEye Agenta na počítače s Windows 10/11.

## Metody instalace

1. **Instalátor (Doporučeno)** - Grafický průvodce (`.exe`), který provede veškerým nastavením včetně zabezpečení účtů.
2. **Manuální instalace** - Pro pokročilé správce nebo hromadné nasazení přes skripty.

---

## Metoda 1: Instalátor (Doporučeno)

Stáhněte nejnovější verzi instalátoru `FamilyEyeAgent_Setup_2.4.0.exe` z dashboardu serveru.

### Průběh instalace

#### 1. Konfigurace Serveru
Instalátor se nejprve zeptá na adresu vašeho FamilyEye serveru.
- **Server URL**: Zadejte celou adresu (např. `https://192.168.1.50:8443`)
- Klikněte na **Ověřit dostupnost** (Test Connection) pro potvrzení, že server odpovídá.

#### 2. Párování
Na této obrazovce zadáváte identitu počítače.
- **Párovací kód (Token)**: Získáte v dashboardu v sekci "Zařízení" -> "Přidat zařízení".
- **Název zařízení**: Pojmenujte počítač (např. "Karlův Notebook").
- Token je jednorázový a má omezenou platnost (5 minut).

#### 3. Nastavení účtů (Důležité)
Pro maximální ochranu agent vyžaduje specifické nastavení uživatelských účtů.

- **Dětský účet**: Zvolte účet, který bude dítě používat.
  - Pokud účet neexistuje, instalátor ho vytvoří.
  - Pokud je účet Administrátor, instalátor navrhne odebrání práv (dítě by nemělo mít admin práva).
- **Rodičovský (Admin) účet**:
  - Pokud degradujete dětský účet na "Standardní uživatel", systém musí mít alespoň jednoho admina.
  - Instalátor vás vyzve k vytvoření/ověření záložního rodičovského účtu.

#### 4. Bezpečnostní politiky
Vyberte úroveň zabezpečení systému. Doporučujeme aktivovat všechny možnosti:
- **FamilyEye Firewall**: Blokuje odchozí komunikaci pro neznámé aplikace.
- **Chránit proces agenta**: Skryje procesy ve Správci úloh.
- **Omezit Ovládací panely**: Zabrání odinstalaci nebo změně IP adresy.
- **Blokovat Registry**: Zabrání pokročilému obcházení.

### Dokončení
Po dokončení instalace:
1. Služba `FamilyEyeAgent` se automaticky spustí.
2. Agent se zaregistruje na serveru.
3. Počítač můžete vidět v dashboardu jako "Online".

---

## Metoda 2: Manuální instalace (Pro experty)

Pokud potřebujete agenta nasadit bez GUI nebo přes příkazovou řádku.

### Požadavky
- Python 3.9+
- Administrátorská práva
- Přístup k souborům instalace (`dist/` složka)

### Postup

1. **Kopírování souborů**:
   Umístěte aplikaci do `C:\Program Files\FamilyEye\Agent`.

2. **Generování konfigurace**:
   Vytvořte soubor `C:\ProgramData\FamilyEye\Agent\config.json`:
   ```json
   {
     "backend_url": "https://vas-server:8443",
     "device_id": "win-manual-001",
     "api_key": "VÁŠ_API_KLÍČ_Z_PÁROVÁNÍ",
     "polling_interval": 30,
     "ssl_verify": false
   }
   ```
   *Poznámka: API klíč musíte získat manuálním voláním API endpointu `/api/devices/pairing/pair`.*

3. **Registrace služby**:
   Použijte `sc` příkaz pro vytvoření Windows Service:
   ```cmd
   sc create FamilyEyeAgent binPath= "C:\Program Files\FamilyEye\Agent\agent_service.exe" start= auto
   sc failure FamilyEyeAgent reset= 60 actions= restart/5000
   net start FamilyEyeAgent
   ```

4. **Nastavení ACL (Oprávnění)**:
   Je kritické nastavit oprávnění tak, aby uživatel (dítě) nemohl modifikovat config nebo zastavit službu.
   - `config.json`: Read-only pro Users (zápis jen SYSTEM/Admin).
   - `Logs/`: Write pro Users.

---

## Řešení problémů

### Chyba připojení v instalátoru
- Zkontrolujte, zda na serveru běží firewall (port 8443).
- Zkuste v prohlížeči počítače otevřít `https://IP-SERVERU:8443/api/health`.
- Pokud používáte Self-Signed certifikát, instalátor ho automaticky akceptuje, ale antivir může blokovat spojení.

### Agent se nezobrazuje v dashboardu
- Zkontrolujte logy v `C:\ProgramData\FamilyEye\Agent\Logs\agent_service.log`.
- Ověřte, že běží služba "FamilyEye Agent" (`services.msc`).

### Nelze nainstalovat (Chyba práv)
- Instalátor musíte spouštět jako Administrátor ("Spustit jako správce").
