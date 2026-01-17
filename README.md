# FamilyEye 🛡️

> **Complete parental control solution for families**

[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](LICENSE)
[![Status: Open Source (Non-Commercial)](https://img.shields.io/badge/Status-Open%20Source%20(Non--Commercial)-orange)](README.md)
[![Language: Czech](https://img.shields.io/badge/Lang-Česky-red)](README_CZ.md)

**FamilyEye je open-source projekt pro osobní nekomerční použití.**
Komunitní příspěvky (bug fixy, nové funkce) jsou vřele vítány! Podívejte se do [CONTRIBUTING.md](CONTRIBUTING.md).

---

## ✨ Features

- **📱 Multi-Platform Agents** - Windows & Android monitoring clients
- **🛡️ Smart Shield (Game-Changer)** - Advanced real-time on-screen content analysis. Goes beyond simple DNS blocking to detect harmful visuals and text in any app.
- **⏰ Screen Time Management** - Daily limits, app limits, and schedules
- **📊 Usage Analytics** - Detailed reports with insights and trends
- **🌐 Web Dashboard** - Modern React-based parent dashboard
- **🔐 Offline-First** - Agents work without internet, sync when connected

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Parent Dashboard                        │
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

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- (For Android) Android Studio + JDK 17

### 1. Clone & Setup Backend

```bash
git clone https://github.com/SkriptyRobert/Parential-Control-Enterprise.git
cd Parential-Control-Enterprise

# Create virtual environment
cd backend
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Run backend
python run_https.py
```

### 2. Setup Frontend

```bash
cd frontend
npm install
npm run dev
```

### 3. Access Dashboard

Open `https://localhost:8000` in your browser.

Default credentials will be created on first run.

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

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/ARCHITECTURE.md) | System architecture overview |
| [Backend API](docs/API.md) | REST API documentation |
| [Frontend](docs/FRONTEND.md) | Dashboard development guide |
| [Deployment](docs/DEPLOYMENT.md) | Production deployment guide |
| [Development](docs/DEVELOPMENT.md) | Developer setup guide |

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Quick Contribution Guide

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 🔐 Security

For security vulnerabilities, please see [SECURITY.md](SECURITY.md) or email security@familyeye.app (do not open public issues).

## 📄 License (Non-Commercial)

This project is licensed under **CC BY-NC-SA 4.0** (Attribution-NonCommercial-ShareAlike).
See [LICENSE](LICENSE) file for details.

**Author:** Róbert Pešout (BertSoftware) - robert.pesout@gmail.com

**For commercial use (companies, paid services), please contact us for an exception.**

---

<p align="center">
  Made with ❤️ for families everywhere
</p>
