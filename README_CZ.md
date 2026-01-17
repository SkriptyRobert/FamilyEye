# FamilyEye 🛡️

> **Kompletní řešení rodičovské kontroly** - Monitorujte, chraňte a veďte své děti digitálním světem.

[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](LICENSE_CZ)
[![Status: Open Source (Non-Commercial)](https://img.shields.io/badge/Status-Open%20Source%20(Non--Commercial)-orange)](README_CZ.md)

**FamilyEye je open-source projekt pro osobní nekomerční použití.**
Komunitní příspěvky (opravy chyb, nové funkce) jsou vřele vítány! Podívejte se do [CONTRIBUTING_CZ.md](CONTRIBUTING_CZ.md).

---

## ✨ Funkce

### 🖥️ Windows Agent
- **Sledování v reálném čase**: Monitoruje aktivní okna a využití aplikací.
- **Inteligentní limity**: Nastavte denní limity pro konkrétní aplikace nebo kategorie.
- **Blokování obsahu**: Blokuje nevhodné weby a aplikace (Smart Shield).
- **Screenshoty na vyžádání**: Vzdálený pohled na obrazovku dítěte.
- **Offline Mode**: Funguje i bez internetu (data se synchronizují po připojení).

### 📱 Android Agent
- **Detekce aplikací**: Sleduje používání mobilních aplikací.
- **Vynucení pravidel**: Blokuje aplikace po překročení limitu (překryvnou obrazovkou).
- **Bezpečná odinstalace**: Ochrana proti smazání dítětem.

### 🌐 Dashboard (Rodičovská část)
- **Přehledné statistiky**: Grafy používání (denní/týdenní).
- **Správa pravidel**: Jednoduché rozhraní pro nastavení limitů a povolených časů.
- **Vzdálené ovládání**: Zamykání zařízení, reset PINu (v přípravě).

---

## 🚀 Rychlý Start

### Prerekvizity
- Python 3.11+
- Node.js 18+
- (Volitelně) Docker

### Instalace (Vývojová verze)

1.  **Klonování repozitáře**
    ```bash
    git clone https://github.com/SkriptyRobert/FamilyEye.git
    cd FamilyEye
    ```

2.  **Nastavení Backend**
    ```bash
    cd backend
    python -m venv venv
    .\venv\Scripts\activate
    pip install -r requirements.txt
    python run_https.py
    ```

3.  **Nastavení Frontend**
    ```bash
    cd frontend
    npm install
    npm run dev
    ```

4.  **Otevřete v prohlížeči**: `https://localhost:5173` (nebo dle výstupu konzole)

---

## 🏗️ Architektura

Projekt se skládá ze tří hlavních částí:

1.  **Backend (FastAPI)**: Centrální mozek, REST API, databáze (SQLite/PostgreSQL).
2.  **Frontend (React/Vite)**: Moderní webové rozhraní pro rodiče.
3.  **Agenti (Windows/Android)**: Klientské aplikace běžící na zařízeních dětí.

---

## 🤝 Jak přispět

Chcete pomoci? Skvělé! Přečtěte si prosím [CONTRIBUTING_CZ.md](CONTRIBUTING_CZ.md) pro detaily o našem procesu a pravidlech.

---

## 🔒 Bezpečnost

Naše politika zabezpečení je popsána v [SECURITY_CZ.md](SECURITY_CZ.md).
Pokud najdete zranitelnost, **nehlaste ji veřejně**, ale napište na **robert.pesout@gmail.com**.

---

## 📄 Licence (Nekomerční)

Tento projekt je licencován pod **CC BY-NC-SA 4.0** (Uveďte autora-Neužívejte komerčně-Zachovejte licenci).
Viz soubor [LICENSE_CZ](LICENSE_CZ) pro detaily.

**Autor:** Róbert Pešout (BertSoftware) - robert.pesout@gmail.com

**Pro komerční použití (firmy, placené služby) nás kontaktujte pro udělení výjimky.**
