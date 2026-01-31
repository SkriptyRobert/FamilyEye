# 📦 FamilyEye - Instalační balíčky

## 🎯 Přehled

Projekt obsahuje dva oddělené instalátory:

| Instalátor | Účel | Cílový počítač |
|------------|------|----------------|
| **FamilyEye Server** | Ovládací panel pro rodiče | Rodičovský PC |
| **FamilyEye Agent** | Monitorování a ochrana | Dětský PC |

---

## 🖥️ Server Instalátor (v2.4.0)

### Co dělá:
1. **Root CA integrace**: Při instalaci vygeneruje vlastní CA a server certifikát, uloží je do `ProgramData\FamilyEye\Server\certs` a přidá `FamilyEye Root CA` do důvěryhodných kořenových autorit.
2. **Backend + Frontend**: Nainstaluje backend API i zbuildovaný React dashboard.
3. **Windows služba**:
   - Zaregistruje službu `FamilyEyeServer`, která běží na pozadí po startu Windows.
   - Přidá firewall pravidlo pro zvolený port.
4. **Zástupce na dashboard**: Vytvoří zástupce, který spustí `FamilyEyeServer.exe --launch-browser-only` a otevře ovládací panel v prohlížeči.

### Průvodce instalací:
- **Port serveru** – výchozí: 8443 (HTTPS na lokální síti).
- **Admin účet** – po instalaci se administrátor vytvoří přes webové rozhraní (registrace/přihlášení), ne v samotném instalátoru.

### Build instrukce:
```bash
# 1. Build frontendu (z kořene repozitáře)
cd frontend
npm ci
npm run build
cd ..

# 2. Sestavit serverový EXE (PyInstaller)
cd backend
python "..\installer\server\build_server_exe.py"
cd ..

# 3. Zkompilovat Inno Setup instalátor
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer/server/setup_server.iss

# Výstup: installer/server/output/ParentalControlServer_Setup_2.4.0.exe
```

### Struktura po instalaci:
- `{app}\FamilyEyeServer.exe` – hlavní binárka serveru (PyInstaller).
- `{commonappdata}\FamilyEye\Server\parental_control.db` – databáze.
- `{commonappdata}\FamilyEye\Server\logs\` – logy backendu a služby.
- `{commonappdata}\FamilyEye\Server\uploads\` – uploady a screenshoty.
- `{commonappdata}\FamilyEye\Server\certs\` – vygenerované certifikáty (CA + server).

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
│   ├── setup_agent_2.4.0.iss   # Inno Setup skript
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

### Python
Serverový instalátor používá samostatný EXE (`FamilyEyeServer.exe`) vytvořený přes PyInstaller, takže cílový počítač **nepotřebuje předinstalovaný Python**.

---



---





