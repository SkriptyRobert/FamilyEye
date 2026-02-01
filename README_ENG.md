# FamilyEye 🛡️

> **Kompletní řešení rodičovské kontroly**

[![License: GPLv3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Images: CC BY-NC-SA 4.0](https://img.shields.io/badge/Images-CC%20BY--NC--SA%204.0-lightgrey.svg)](LICENSE_IMAGES)
[![Status: Open Source](https://img.shields.io/badge/Status-Open%20Source-green)](README_CZ.md)
[![Language: English](https://img.shields.io/badge/Lang-English-blue)](README.md)
[![Device Owner: Supported](https://img.shields.io/badge/🤖_Device%20Owner-Supported-purple)](docs/AGENT.md)

**FamilyEye je open-source projekt pro osobní nekomerční použití.**
Komunitní příspěvky (opravy chyb, nové funkce) jsou vřele vítány! Podívejte se do [CONTRIBUTING_CZ.md](CONTRIBUTING_CZ.md).

---

## ✨ Funkce

- **📱 Multi-Platformní Agenti** - Monitorovací klienti pro Windows a Android
- **🛡️ Smart Shield (Game-Changer)** - Pokročilá analýza obsahu na obrazovce v reálném čase. Jde nad rámec běžného blokování webů – detekuje škodlivý text i vizuály v jakékoli aplikaci.
- **⏰ Správa Času** - Denní limity, limity aplikací a rozvrhy
- **📊 Analýza Používání** - Detailní reporty s přehledy a trendy
- **🌐 Webový Dashboard** - Moderní rodičovské rozhraní (React)
- **🔐 Offline-First** - Agenti fungují bez internetu, synchronizují se po připojení

## 🏗️ Architektura

```
┌─────────────────────────────────────────────────────────────┐
│                      Rodičovský Dashboard                    │
│                    (React + Vite + CSS)                      │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTPS
┌─────────────────────────▼───────────────────────────────────┐
│                    Backend API                               │
│              (FastAPI + SQLite + WebSocket)                  │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTPS
          ┌───────────────┴───────────────┐
          ▼                               ▼
┌─────────────────────┐       ┌─────────────────────┐
│   Windows Agent     │       │   Android Agent     │
│  (Python + PyQt5)   │       │ (Kotlin + Compose)  │
└─────────────────────┘       └─────────────────────┘
```

## 🚀 Rychlý Start

### Prerekvizity

- Python 3.10+
- Node.js 18+
- (Pro Android) Android Studio + JDK 17

### 1. Klonování & Nastavení Backendu

```bash
git clone https://github.com/SkriptyRobert/FamilyEye.git
cd FamilyEye

# Vytvoření virtuálního prostředí
cd backend
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Instalace závislostí
pip install -r requirements.txt

# Spuštění backendu
python run_https.py
```

### 2. Nastavení Frontendu

```bash
cd frontend
npm install
npm run dev
```

### 3. Přístup k Dashboardu

Otevřete `https://localhost:8000` ve svém prohlížeči.

Výchozí přihlašovací údaje budou vytvořeny při prvním spuštění.

## 📁 Struktura Projektu

```
FamilyEye/
├── backend/           # FastAPI backend server
│   ├── app/           # Kód aplikace
│   │   ├── api/       # REST endpointy
│   │   ├── models/    # SQLAlchemy modely
│   │   └── services/  # Byznys logika
│   └── requirements.txt
├── frontend/          # React dashboard
│   └── src/
│       ├── components/
│       └── services/
├── clients/
│   ├── android/       # Android agent (Kotlin)
│   └── windows/       # Windows agent (Python)
├── installer/         # Inno Setup instalátory
├── docs/              # Dokumentace
└── certs/             # SSL certifikáty
```

## 📚 Dokumentace

| Dokument | Popis |
|----------|-------|
| [Architektura](docs/ARCHITECTURE.md) | Přehled architektury systému |
| [Backend API](docs/API.md) | Dokumentace REST API |
| [Frontend](docs/FRONTEND.md) | Průvodce vývojem dashboardu |
| [Agent](docs/AGENT.md) | Dokumentace Windows & Android agenta |
| [Nasazení](docs/DEPLOYMENT.md) | Průvodce produkčním nasazením |
| [Vývoj](docs/DEVELOPMENT.md) | Průvodce nastavením vývojového prostředí |
| [Systémový design](docs/architecture/system-design.md) | Detailní systémový design |
| [Bezpečnostní model](docs/architecture/security-model.md) | Bezpečnostní architektura |
| [Feature Matrix](docs/reference/feature-matrix.md) | Kompletní reference funkcí |

## 🤝 Jak přispět

Příspěvky jsou vítány! Prosím podívejte se do [CONTRIBUTING_CZ.md](CONTRIBUTING_CZ.md) pro instrukce.

### Rychlý průvodce přispíváním

1. Forkněte repozitář
2. Vytvořte feature branch (`git checkout -b feature/uzasna-funkce`)
3. Commitněte změny (`git commit -m 'Pridana uzasna funkce'`)
4. Pushněte do branche (`git push origin feature/uzasna-funkce`)
5. Otevřete Pull Request

## 🔐 Bezpečnost

Pro bezpečnostní zranitelnosti viz [SECURITY_CZ.md](SECURITY_CZ.md) nebo napište na **robert.pesout@gmail.com** (neotvírejte veřejné issues).

## 📄 Licence

### Licence kódu
Zdrojový kód tohoto projektu je licencován pod **GNU General Public License v3.0 (GPLv3)**.
Viz soubor [LICENSE](LICENSE) pro detaily.

### Licence obrázků
Všechny obrázky, grafiky a vizuální materiály v tomto repozitáři jsou licencovány pod **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)**.
Viz soubor [LICENSE_IMAGES](LICENSE_IMAGES) pro detaily.

**Autor:** Róbert Pešout (BertSoftware) - robert.pesout@gmail.com

**Poznámka:** Obrázky jsou pouze pro nekomerční použití. Pro komerční použití obrázků kontaktujte autora.

---

<p align="center">
  Vyrobeno s ❤️ pro rodiny všude na světě
</p>
