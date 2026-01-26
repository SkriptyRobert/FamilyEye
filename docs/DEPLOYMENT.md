# Nasazení a instalace

## Přehled

Návod na instalaci a nasazení systému Parental Control Enterprise.

## Systémové požadavky

### Server

- **OS**: Windows 10/11
- **RAM**: 4 GB minimálně
- **Disk**: 500 MB volného místa
- **Síť**: Síťové připojení
- **Python**: 3.8+ (pro manuální instalaci)

### Agent

- **OS**: Windows 10/11
- **RAM**: 2 GB minimálně
- **Disk**: 100 MB volného místa
- **Síť**: Připojení k serveru
- **Python**: 3.8+ (pro manuální instalaci)

## Instalace serveru

### Automatická instalace (doporučeno)

1. Stáhněte `ParentalControlServer_Setup_2.0.0.exe`
2. Spusťte instalátor
3. Postupujte podle průvodce:
   - Výběr portu (výchozí: 8000)
   - Vytvoření účtu (e-mail + heslo)
4. Po instalaci se otevře dashboard v prohlížeči

### Manuální instalace

#### 1. Příprava prostředí

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

#### 2. Konfigurace

Vytvořte `.env` soubor nebo nastavte proměnné prostředí:

```env
SECRET_KEY=your-secret-key-change-in-production
DATABASE_URL=sqlite:///parental_control.db
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
```

#### 3. Inicializace databáze

Databáze se vytvoří automaticky při prvním spuštění.

#### 4. Spuštění

**HTTP (vývoj)**:
```bash
python run_https.py
```

**HTTPS (produkce)**:
```bash
python run_https.py
```

**Windows služba**:
```bash
python service_wrapper.py install
python service_wrapper.py start
```

#### 5. Ověření

Otevřete prohlížeč: `http://localhost:8000`

## Instalace agentu

### Automatická instalace (doporučeno)

1. Stáhněte `ParentalControlAgent_Setup_2.0.0.exe`
2. Spusťte instalátor
3. Postupujte podle průvodce:
   - Zadání adresy serveru (z dashboardu)
   - Zadání párovacího tokenu (z dashboardu)
   - Pojmenování zařízení
4. Agent se automaticky spustí

### Manuální instalace

#### 1. Příprava prostředí

```bash
cd clients/windows
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

#### 2. Párování zařízení

Párování se provádí přes frontend dashboard nebo přímo přes API endpoint `/api/devices/pairing/pair`. 

Pro manuální párování použijte:
- Frontend: Otevřete dashboard a použijte QR kód nebo manuální token
- API: POST request na `/api/devices/pairing/pair` s pairing tokenem

#### 3. Spuštění

```bash
python -m agent.main
```

#### 4. Windows služba

```bash
python service_wrapper.py install
python service_wrapper.py start
```

## Konfigurace

### Backend

**Soubor**: `backend/app/config.py`

**Proměnné prostředí**:
- `SECRET_KEY` - JWT secret key (změnit v produkci!)
- `DATABASE_URL` - Databázové připojení
- `BACKEND_HOST` - Host (0.0.0.0 pro všechny rozhraní)
- `BACKEND_PORT` - Port (výchozí: 8000)
- `BACKEND_URL` - URL backendu

### Agent

**Soubor**: `clients/windows/config.json`

**Struktura**:
```json
{
  "backend_url": "https://192.168.1.100:8000",
  "device_id": "uuid",
  "api_key": "uuid",
  "polling_interval": 30,
  "reporting_interval": 300,
  "ssl_verify": false
}
```

## SSL/TLS

### Automatická generace

Certifikáty se generují automaticky při prvním spuštění.

**Umístění**: `certs/`

### Instalace CA certifikátu

1. Otevřete `https://your-server:8000/api/trust/ca.crt`
2. Stáhněte certifikát
3. Nainstalujte do "Trusted Root Certification Authorities"

**Nebo**:
1. Otevřete `https://your-server:8000/api/trust/qr.png`
2. Naskenujte QR kód
3. Nainstalujte certifikát

## Firewall

### Server

Otevřete porty:
- **8000** (HTTP/HTTPS) - Pro frontend a API
- **8001** (volitelně) - Pro alternativní port

### Agent

Povolte odchozí připojení na port 8000 serveru.

## Produkční nasazení

### Doporučení

1. **Změnit SECRET_KEY** - Použít silný náhodný klíč
2. **Použít HTTPS** - Spustit `run_https.py`
3. **Změnit CORS** - Omezit `allow_origins` v `main.py`
4. **Zálohování databáze** - Pravidelné zálohy `parental_control.db`
5. **Logování** - Kontrola `app.log`
6. **Windows služba** - Spustit jako služba pro automatický start

### Windows služba

**Backend**:
```bash
cd backend
python service_wrapper.py install
python service_wrapper.py start
```

**Agent**:
```bash
cd clients/windows
python service_wrapper.py install
python service_wrapper.py start
```

### Monitoring

- **Logy**: `backend/app.log`, `clients/windows/agent.log`
- **Health check**: `GET /api/health`
- **Status**: Dashboard zobrazuje status zařízení

## Troubleshooting

### Server se nespustí

1. Zkontrolujte port (není obsazený)
2. Zkontrolujte logy (`app.log`)
3. Zkontrolujte firewall
4. Zkontrolujte Python verzi (3.8+)

### Agent se nepřipojí

1. Zkontrolujte `config.json`
2. Zkontrolujte backend URL (dostupnost)
3. Zkontrolujte SSL certifikát (pokud HTTPS)
4. Zkontrolujte firewall
5. Zkontrolujte logy (`agent.log`)

### Párování selže

1. Zkontrolujte platnost pairing tokenu (5 minut)
2. Zkontrolujte backend dostupnost
3. Zkontrolujte SSL certifikát
4. Zkontrolujte logy na serveru

### Pravidla se nevynucují

1. Zkontrolujte, že agent běží
2. Zkontrolujte, že pravidla jsou aktivní
3. Zkontrolujte logy agenta
4. Zkontrolujte oprávnění agenta (admin)

## Aktualizace

### Backend

1. Zastavte službu
2. Zálohujte databázi
3. Aktualizujte kód
4. Aktualizujte závislosti: `pip install -r requirements.txt`
5. Spusťte službu

### Agent

1. Zastavte službu
2. Aktualizujte kód
3. Aktualizujte závislosti: `pip install -r requirements.txt`
4. Spusťte službu

### Frontend

1. Build: `cd frontend && npm run build`
2. Kopírovat `dist/` do `backend/frontend/dist/`
3. Restartovat backend

## Zálohování

### Databáze

```bash
# SQLite
copy parental_control.db parental_control.db.backup
```

### Konfigurace

Zálohujte:
- `backend/app/config.py` (nebo .env)
- `clients/windows/config.json`
- `certs/` (certifikáty)

## Odinstalace

### Server

1. Zastavte službu: `python service_wrapper.py stop`
2. Odinstalujte službu: `python service_wrapper.py remove`
3. Smazat adresář `backend/`
4. Smazat databázi (volitelně)

### Agent

1. Zastavte službu: `python service_wrapper.py stop`
2. Odinstalujte službu: `python service_wrapper.py remove`
3. Smazat adresář `clients/windows/`
4. Odstranit zařízení z dashboardu

## Podpora

Pro další pomoc viz README.md nebo kontaktujte podporu.

