# 📦 FamilyEye - Instalační balíčky

## 🎯 Přehled

Projekt obsahuje dva oddělené instalátory:

| Instalátor | Účel | Cílový počítač |
|------------|------|----------------|
| **FamilyEye Server** | Ovládací panel pro rodiče | Rodičovský PC |
| **FamilyEye Agent** | Monitorování a ochrana | Dětský PC |

---

## 🖥️ Server Instalátor

### Co dělá:
1. Nainstaluje backend API (Python)
2. Nainstaluje webový dashboard
3. Vytvoří administrátorský účet
4. Nastaví Windows službu
5. Přidá firewall pravidlo

### Průvodce instalací:
- **Port serveru** – na jakém portu poběží webové rozhraní (výchozí: 8000)
- **E-mail a heslo** – pro přihlášení do rodičovské administrace

### Build:
```
1. Nainstalujte Inno Setup 6
2. Otevřete installer/server/setup_server.iss
3. Build → Compile
4. Výstup: `installer/server/output/FamilyEyeServer_Setup_2.1.5.exe`
```

---

## 📱 Agent Instalátor

### Co dělá:
1. Nainstaluje monitorovacího agenta
2. Průvodce napomáhá s párováním
3. Registruje Windows službu
4. Skryje se z ovládacích panelů (dítě nemůže odinstalovat)
5. Vyžaduje heslo pro odinstalaci

### Průvodce instalací:
- **Adresa serveru** – URL adresa, kde běží rodičovský server
- **Párovací kód (token)** – bezpečnostní kód z rodičovského ovládacího panelu
- **Název zařízení** – jak se bude počítač zobrazovat v přehledu

### Build:
```
1. Nainstalujte Inno Setup 6
2. Otevřete installer/agent/setup_agent_2.4.0.iss
3. Build → Compile
4. Výstup: `installer/agent/output/FamilyEyeAgent_Setup_2.4.0.exe`
```

---

## 📁 Struktura

```
installer/
├── README.md                    # Tento soubor
│
├── agent/                       # Agent instalátor
│   ├── setup_agent_2.3.0.iss  # Inno Setup skript
│   ├── assets/                 # Ikony, obrázky
│   │   ├── setup_icon.ico
│   │   ├── wizard_side.bmp
│   │   └── wizard_top.bmp
│   └── output/                 # Zkompilované EXE
│
└── server/                     # Server instalátor
    ├── setup_server.iss        # Inno Setup skript
    ├── assets/                 # Ikony, obrázky
    │   ├── server_icon.ico
    │   ├── wizard_image.bmp
    │   └── wizard_small.bmp
    └── output/                 # Zkompilované EXE
```

---

## 🛠️ Požadavky pro build

### Software
- [Inno Setup 6.2+](https://jrsoftware.org/isdl.php)
- Windows 10/11

### Assets (vytvořit)
Pro build instalátoru je potřeba vytvořit:

| Soubor | Rozměry | Popis |
|--------|---------|-------|
| `setup_icon.ico` | 256x256 | Hlavní ikona aplikace |
| `wizard_side.bmp` | 164x314 | Obrázek vlevo v průvodci (Agent) |
| `wizard_top.bmp` | 55x55 | Malá ikona vpravo nahoře (Agent) |
| `wizard_image.bmp` | 164x314 | Obrázek vlevo v průvodci (Server) |
| `wizard_small.bmp` | 55x55 | Malá ikona vpravo nahoře (Server) |

### Python Embedded
Pro standalone instalátor je potřeba přidat:
- `python-embed/` - [Python embeddable package](https://www.python.org/downloads/windows/)

---

## 🔐 Code Signing (produkce)

Pro distribuci je NUTNÉ podepsat instalátor:

```bash
# Windows SDK signtool
signtool sign /f certificate.pfx /p heslo /tr http://timestamp.digicert.com /td sha256 ParentalControlAgent_Setup_2.0.0.exe
```

Bez podpisu:
- Windows Defender může blokovat
- Uživatelé uvidí varování "Neznámý vydavatel"

---

## 🧪 Testování

### Checklist před release:

- [ ] Čistá instalace Windows 10 VM
- [ ] Instalace bez Python/Node.js
- [ ] Agent se spáruje během instalace
- [ ] Agent přežije restart
- [ ] Agent reportuje na dashboard
- [ ] Uninstaller vyžaduje heslo
- [ ] Blokování aplikací funguje
- [ ] Časové limity fungují

---

## 🔄 Aktualizace

### Strategie:
1. Agent kontroluje verzi při startu
2. Pokud je k dispozici nová verze:
   - Stáhne nový instalátor
   - Spustí silent upgrade
   - Zachová konfiguraci

*TODO: Implementovat auto-update mechanismus*
