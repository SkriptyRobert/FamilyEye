# FamilyEye <img src="docs/assets/logo.png" height="32" alt="FamilyEye Logo" style="vertical-align: bottom;" />

<div align="center">

  <img src="docs/assets/hero-family.jpg" alt="FamilyEye - Secure Your Family's Digital Future" width="100%" style="border-radius: 10px;" />
  <br><br>
  
  > **Ochrana pro Vaši rodinu v digitálním světě**

  [![License: GPLv3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
  [![Images: Public Domain](https://img.shields.io/badge/Images-Public%20Domain-lightgrey.svg)](LICENSE_IMAGES)
  [![Status: Open Source](https://img.shields.io/badge/Status-Open%20Source-green)](README.md)
  [![Language: Czech](https://img.shields.io/badge/Lang-Česky-red)](README_CZ.md)
  [![Device Owner: Supported](https://img.shields.io/badge/🤖_Device%20Owner-Supported-purple)](docs/AGENT.md)
</div>

---

## ⚡ Blesková Instalace & Nastavení
**Vše je připraveno pro okamžité použití.** Veškerý provoz je **šifrovaný by default**.

- 🐳 **Server (Docker):** Jediný příkaz `docker-compose up` a váš server běží.
- 🏢 **Server (Windows):** One-click instalátor pro domácí PC. Může běžet samostatně nebo spolu s agentem.
- 💻 **Agent Windows:** Jednoduchý instalátor, který za vás nastaví účet, oprávnění i služby.
- 📱 **Agent Android:** Apk instalace bez nutnosti továrního nastavení a jakékoliv ztráty dat. Stačí na chvílí odhlásit google účet aktivovat Device Owner a následně účet zpět.
- **Snadné párování:** Stačí naskenovat QR kód.
- **Plná ochrana (Device Owner):** Nastavení na 3 kliknutí přes **WebUSB/WebADB**. Připojíte kabel, kliknete a máte hotovo.

---

## Proč FamilyEye? Game Changer Features!

### 🛡️ Smart Shield / Detekce Slov (včetně Vlastních!)
**Nečekejte na problém, předcházejte mu.**
- **Smart Shield** neblokuje jen domény. Analyzuje obsah obrazovky v reálném čase:
- **Detekce nebezpečných slov** (včetně vašich **vlastních v kategoriích**!).
- **AI analýza vizuálů** a okamžité pořízení důkazního snímku.
- Funguje v jakékoliv aplikaci, nejen v prohlížeči.

### 🌐 Žádné Zbytečné Aplikace pro Rodiče
**Váš telefon zůstane čistý.**
Pro správu rodiny nepotřebujete instalovat žádnou další aplikaci.
- **Plně responzivní Web:** Dashboard funguje perfektně na mobilu, tabletu i počítači.
- **Kdekoliv a kdykoliv:** Stačí otevřít prohlížeč. Žádné otravné aktualizace "Rodičovské aplikace".

### 🔒 Data v Bezpečí (Ani Čína, ani Amerika)
- **Self-hosted:** Celý systém běží na vašem vlastním železe.
- **Žádné sledování:** Data neputují na cizí servery v Číně ani v USA. Vše zůstává u vás doma.

### 🎮 Kompletní Kontrola a Agenti
**To není jen o blokování. Je to o zdravých návycích.**

#### ⏰ Pánem Času (Limity a Rozvrhy)
- **Flexibilní Rozvrhy:** Nastavte přesně, kdy se co smí hrát a kdy se spí ("Večerka").
- **Dávkování Zábavy:** Určete denní limity pro konkrétní aplikace/zařízení.

#### 🔒 Vzdálená Správa v Reálném Čase
- **Uzamčení!** Uzamkněte zařízení dítěte na jedno kliknutí z vašeho mobilu.
- **Vypnutí internetu** Možnost vypnutí internetu zařízení dítěte na jedno kliknutí z vašeho mobilu.
- **Blokace webových stránek** Možnost blokování webových stránek zařízení dítěte na jedno kliknutí z vašeho mobilu.
- **Blokování Instalací:** Na Androidu a Windows zabráníte instalaci nežádoucích programů.
- **Webový Filtr:** Blokování webových stránek dle vlastního seznamu.

#### 🕵️‍♂️ Co se děje, když se nedíváte?
- **Detailní Reporting:** Přesné grafy používání aplikací.
- **Offline? Nevadí:** Agenti si fungují i offline a po připojení vše synchronizují. Chytře rozpoznává mezi výpadkem sítě a bootem zařízení. 
- **Anti-Tamper Ochrana:** Dítě nemůže agenta jen tak odinstalovat nebo vypnout (Device Admin/Owner mód). 

---

## 🚀 Chcete FamilyEye vylepšit? Nebo jste našli chybu?

**Tak to jednoduše udělejte!**

Projekt je navržen tak, aby se do něj mohl zapojit každý – klidně s pomocí **AI**.
- **Pro AI Agenty:** V kořenu projektu najdete soubor [`llms.txt`](llms.txt).
- **Jak na to:** Jednoduše načtěte `llms.txt` svému AI agentovi (Claude, ChatGPT, codex,...). Soubor obsahuje kompletní kontext, architekturu a instrukce, takže AI okamžitě pochopí, co a jak upravit a sestavit.

*Vytvářejte, upravujte a pomozte nám dělat digitální svět bezpečnějším!*

---

## 🛠️ Technická Dokumentace

**Video návody (instalace, párování):** [Dokumentace → Video návody](https://skriptyrobert.github.io/FamilyEye/docs/tutorials/videos/) – pro videa z YouTube - to-do.

*Níže naleznete technické detaily, strukturu projektu a návody na instalaci.*

## 📁 Project Structure

```
FamilyEye/
├── backend/           # FastAPI backend server
│   ├── app/           # Application code
│   │   ├── api/       # REST endpoints
│   │   ├── models/    # SQLAlchemy models
│   │   └── services/  # Business logic
│   └── requirements.txt
├── frontend/          # React dashboard
│   └── src/
│       ├── components/
│       └── services/
├── clients/
│   ├── android/       # Android agent (Kotlin)
│   └── windows/       # Windows agent (Python)
├── installer/         # Inno Setup installers
├── docs/              # Documentation
└── certs/             # SSL certificates
```

## 📚 Dokumentace

Kompletní dokumentace je organizována v adresáři `/docs`.

### 🧭 Hlavní Přehled
| Dokument | Popis |
|----------|-------------|
| **[INDEX](docs/INDEX.md)** | **Hlavní rozcestník dokumentace** |
| [Architecture](docs/ARCHITECTURE.md) | Přehled architektury systému |
| [Deployment](docs/DEPLOYMENT.md) | Příručka pro nasazení do produkce |
| [Development](docs/DEVELOPMENT.md) | Návod pro nastavení vývojového prostředí |

### 🧩 Komponenty
| Dokument | Popis |
|----------|-------------|
| [Backend Guide](docs/BACKEND.md) | Detailní popis backendu a služeb |
| [Frontend Guide](docs/FRONTEND.md) | Vývoj webového dashboardu |
| [Agents Guide](docs/AGENT.md) | Dokumentace pro Windows a Android agenty |
| [Database](docs/DATABASE.md) | Databázové schéma a správa dat |
| [API Reference](docs/API.md) | Specifikace REST API endpointů |

### 🔬 Deep Dives & Reference
- **Architektura:** [System Design](docs/architecture/system-design.md), [Security Model](docs/architecture/security-model.md)
- **Reference:** [Feature Matrix](docs/reference/feature-matrix.md), [Error Codes](docs/reference/error-codes.md), [Testing Guide](docs/reference/testing.md)
- **Diagramy:** [Synchronizace času](docs/TIME_SYNC_DIAGRAM.md)

### 🎓 Návody a Tutoriály
- **Začínáme:** [Prvotní nastavení](docs/tutorials/first-setup.md), [Průvodce startem](docs/tutorials/getting-started.md)
- **Řešení problémů:** [USB Debugging](docs/how-to/troubleshoot-usb.md), [Obnovení přístupu](docs/how-to/restore-access.md)
- **Běžné úkony:** [Změna PINu](docs/how-to/change-pin.md), [Odblokování aplikace](docs/how-to/unblock-app.md)

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Quick Contribution Guide

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 🔐 Security

For security vulnerabilities, please see [SECURITY.md](SECURITY.md) or email robert.pesout@gmail.com.

## 📄 License

### Code License
This project's **source code** is licensed under **GNU General Public License v3.0 (GPLv3)**.
See [LICENSE](LICENSE) file for details.

### Images License
Grafický obsah v tomto projektu byl vygenerován pomocí umělé inteligence (Nanobanana/Google Cloud). Tyto obrázky jsou poskytovány jako **volné dílo (Public Domain)**.

Prosba: Ačkoliv to zákon nevyžaduje, ocením, pokud při dalším šíření těchto obrázků uvedete odkaz na tento projekt.
See [LICENSE_IMAGES](LICENSE_IMAGES) file for details.

**Author:** Róbert Pešout (BertSoftware) - robert.pesout@gmail.com

---

<p align="center">
  Made with ❤️ for families everywhere<br>
  <small>Obrázky generovány pomocí AI. Určeno pro nekomerční využití v rámci tohoto projektu.</small>
</p>
