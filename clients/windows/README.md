# FamilyEye Windows Agent

Windows agent pro rodičovskou kontrolu FamilyEye. Monitoruje aktivitu dítěte, vynucuje pravidla a odesílá data na rodičovský server.

## 📋 Požadavky

- **Windows 10/11** (64-bit)
- **Python 3.10+** (pouze pro vývoj, release verze je kompilovaný .exe)
- **Administrátorská práva** (pro instalaci a provoz)

## 🚀 Instalace

### Automatická instalace (doporučeno)

1. Stáhněte `FamilyEyeAgent_Setup_X.X.X.exe` z releases
2. Spusťte instalační soubor jako administrátor
3. Postupujte podle instalačního průvodce:
   - Zadejte URL backend serveru
   - Zadejte párovací token z rodičovského panelu
   - Vytvořte nebo vyberte dětský účet
   - Nastavte bezpečnostní opatření

### Manuální instalace (pro vývojáře)

```bash
# 1. Klonujte repozitář
git clone https://github.com/SkriptyRobert/FamilyEye.git
cd FamilyEye/clients/windows

# 2. Nainstalujte závislosti
pip install -r requirements.txt

# 3. Vytvořte config.json
# Zkopírujte config.json z párování nebo vytvořte ručně:
{
  "backend_url": "https://192.168.0.100:8000",
  "device_id": "windows-COMPUTERNAME-xxxx",
  "api_key": "your-api-key-here",
  "polling_interval": 30,
  "reporting_interval": 300,
  "ssl_verify": false
}

# 4. Spusťte agenta
python -m agent.main
```

## 🏗️ Build

Pro vytvoření .exe souborů:

```bash
cd installer/agent
python build_agent.py
```

Výstup:
- `dist/agent_service.exe` - Windows Service
- `dist/FamilyEyeAgent.exe` - User Session UI

## 📁 Struktura projektu

```
clients/windows/
├── agent/                 # Hlavní agent kód
│   ├── main.py           # Entry point
│   ├── monitor/          # Sledování aplikací
│   ├── enforcer/         # Vynucování pravidel
│   ├── websocket/        # Real-time komunikace
│   └── ...
├── child_agent.py        # UI agent (user session)
└── requirements.txt      # Python závislosti
```

## ⚙️ Konfigurace

### Config.json umístění

- **Kompilovaná verze:** `C:\ProgramData\FamilyEye\Agent\config.json`
- **Vývojová verze:** `clients/windows/config.json`

### Konfigurační parametry

```json
{
  "backend_url": "https://192.168.0.100:8000",  // URL backend serveru
  "device_id": "windows-COMPUTERNAME-xxxx",     // Unikátní ID zařízení
  "api_key": "uuid-api-key",                    // API klíč pro autentizaci
  "polling_interval": 30,                       // Interval načítání pravidel (sekundy)
  "reporting_interval": 300,                    // Interval odesílání dat (sekundy)
  "cache_duration": 300,                        // Doba platnosti cache (sekundy)
  "ssl_verify": false,                          // Ověřování SSL certifikátů
  "monitor_interval": 5                         // Interval monitorování (sekundy)
}
```

### Environment variables

Můžete také použít environment variables:

```bash
set BACKEND_URL=https://192.168.0.100:8000
set DEVICE_ID=windows-COMPUTERNAME-xxxx
set API_KEY=your-api-key
set AGENT_POLLING_INTERVAL=30
set AGENT_REPORTING_INTERVAL=300
set AGENT_SSL_VERIFY=false
```

## 🔧 Funkce

### Monitoring
- ✅ Real-time sledování aplikací
- ✅ Sledování času použití (per app, daily totals)
- ✅ Detekce oken a titulků
- ✅ Session tracking

### Enforcement
- ✅ Blokování aplikací
- ✅ Časové limity (app limits, daily device limit)
- ✅ Časová okna (schedules)
- ✅ Blokování internetu (firewall-based)
- ✅ Blokování webů (hosts file)
- ✅ Lock device
- ✅ VPN/Proxy detekce

### Real-time komunikace
- ✅ WebSocket client (auto-reconnect)
- ✅ Instant commands (lock, unlock, screenshot)
- ✅ Push notifications

### Zabezpečení
- ✅ Boot protection (Safe Mode detekce)
- ✅ Anti-tampering (time sync)
- ✅ Process monitoring
- ✅ IPC security

## 🐛 Troubleshooting

### Agent se nespustí

1. **Zkontrolujte config.json**
   ```bash
   # Ověřte, že soubor existuje a obsahuje správné hodnoty
   type C:\ProgramData\FamilyEye\Agent\config.json
   ```

2. **Zkontrolujte logy**
   ```bash
   # Logy jsou v:
   C:\ProgramData\FamilyEye\Agent\Logs\service_core.log
   ```

3. **Ověřte službu**
   ```bash
   sc query FamilyEyeAgent
   net start FamilyEyeAgent
   ```

### Agent se nepřipojuje k backendu

1. **Zkontrolujte síťové připojení**
   ```bash
   ping <backend-ip>
   ```

2. **Ověřte SSL certifikát**
   - Pokud používáte self-signed cert, nastavte `"ssl_verify": false`

3. **Zkontrolujte firewall**
   ```bash
   # Agent potřebuje povolený outbound traffic
   netsh advfirewall firewall show rule name="FamilyEyeAgent_Allow"
   ```

### Pravidla se neaplikují

1. **Zkontrolujte, zda jsou pravidla načtena**
   - Podívejte se do logů: `service_core.log`
   - Hledejte: "Rules updated: X rules"

2. **Ověřte cache**
   - Cache je v: `C:\ProgramData\FamilyEye\Agent\rules_cache.json`
   - Můžete smazat pro vynucení nového načtení

3. **Zkontrolujte čas synchronizaci**
   - Agent potřebuje správný systémový čas
   - Podívejte se do logů pro "Time sync" zprávy

### Blokování internetu nefunguje

1. **Zkontrolujte firewall rules**
   ```bash
   netsh advfirewall firewall show rule name="FamilyEye_BlockAll"
   ```

2. **Ověřte, zda je firewall zapnutý**
   ```bash
   netsh advfirewall show allprofiles state
   ```

3. **Zkontrolujte logy**
   - Hledejte: "BLOCKING INTERNET" nebo "Network block"

### ChildAgent (UI) se nespustí

1. **Zkontrolujte Scheduled Task**
   ```bash
   schtasks /query /tn "FamilyEye\FamilyEyeAgent"
   ```

2. **Zkontrolujte Registry**
   ```bash
   reg query "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" /v FamilyEyeAgent
   ```

3. **Spusťte manuálně**
   ```bash
   "C:\Program Files\FamilyEye\Agent\FamilyEyeAgent.exe"
   ```

## 📊 Logy

### Umístění logů

- **Service log:** `C:\ProgramData\FamilyEye\Agent\Logs\service_core.log`
- **ChildAgent log:** `C:\ProgramData\FamilyEye\Agent\Logs\child_agent.log`
- **Boot protection log:** `C:\ProgramData\FamilyEye\Agent\Logs\boot_protection.log`

### Log levels

- **DEBUG:** Detailní informace (vývoj)
- **INFO:** Normální operace
- **WARNING:** Varování
- **ERROR:** Chyby
- **CRITICAL:** Kritické chyby

### Čtení logů

```bash
# Posledních 50 řádků
powershell "Get-Content C:\ProgramData\FamilyEye\Agent\Logs\service_core.log -Tail 50"

# Hledání chyb
findstr /i "error critical" C:\ProgramData\FamilyEye\Agent\Logs\service_core.log
```

## 🔒 Bezpečnost

### Důležité poznámky

1. **Self-signed certificates**
   - Agent defaultně akceptuje self-signed certifikáty (`ssl_verify: false`)
   - Pro domácí nasazení je to OK
   - Pro produkci zvažte použití validních certifikátů

2. **Config.json permissions**
   - Config soubor obsahuje `device_id` a `api_key`
   - Soubor je v ProgramData (čitelné pro všechny uživatele)
   - Pro domácí nasazení je to přijatelné

3. **Boot protection**
   - Agent detekuje boot do Safe Mode, ale neblokuje ho
   - Reportuje událost na backend
   - Pro preventivní ochranu zvažte BIOS heslo

### Best practices

- ✅ Používejte silné API klíče
- ✅ Pravidelně aktualizujte agenta
- ✅ Monitorujte logy pro podezřelé aktivity
- ✅ Používejte HTTPS pro backend komunikaci

## 🧪 Vývoj

### Spuštění v debug módu

```bash
# Service agent
python -m agent.main --console

# ChildAgent (UI)
python child_agent.py --debug
```

### Testování

```bash
# Spuštění testů (když budou implementovány)
pytest tests/
```

### Code style

- Používejte type hints kde je to možné
- Dodržujte PEP 8
- Přidávejte docstrings k funkcím

## 📝 Changelog

### Verze 2.2.0
- ✅ Oprava blokace internetu (pause-internet endpoint)
- ✅ Refaktoring devices API
- ✅ Vylepšené error handling
- ✅ Boot protection vylepšení

### Verze 2.1.5
- ✅ WebSocket auto-reconnect
- ✅ IPC komunikace
- ✅ Time synchronization

## 🤝 Přispívání

Vítány jsou příspěvky! Prosím:
1. Forkněte repozitář
2. Vytvořte feature branch
3. Commitněte změny
4. Pushněte a vytvořte Pull Request

Více v [CONTRIBUTING.md](../../CONTRIBUTING.md)

## 📄 License

CC BY-NC-SA 4.0 - viz [LICENSE](../../LICENSE)

## 🆘 Podpora

- **Issues:** [GitHub Issues](https://github.com/SkriptyRobert/FamilyEye/issues)
- **Discussions:** [GitHub Discussions](https://github.com/SkriptyRobert/FamilyEye/discussions)

---

**FamilyEye Windows Agent** - Open-source rodičovská kontrola pro Windows
