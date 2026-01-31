# Nasazení a instalace

## Přehled

Návod na instalaci a nasazení systému Parental Control Enterprise.

## Systémové požadavky

### Server

- **OS**: Windows 10/11 (nebo Linux/Docker)
- **RAM**: 4 GB minimálně
- **Disk**: 500 MB volného místa
- **Síť**: Síťové připojení
- **Python**: 3.9+ (pro manuální instalaci)

### Agent

- **OS**: Windows 10/11
- **RAM**: 2 GB minimálně
- **Disk**: 100 MB volného místa
- **Síť**: Připojení k serveru

---

## Instalace komponent

Detailní instalační příručky pro každou komponentu:

### 1. Server
- **[Instalace Serveru](../tutorials/server-installation.md)**
  - Windows Instalátor (služba)
  - Docker / Kubernetes
  - Manuální nasazení

### 2. Agenti
- **[Windows Agent](../tutorials/windows-agent.md)**
  - Instalátor (Inno Setup)
  - Bezobslužná instalace
- **[Android Agent](../tutorials/android-agent.md)**
  - Instalace APK
  - Aktivace Device Owner

---

## Konfigurace prostředí

### Backend

**Soubor**: `backend/app/config.py`

**Proměnné prostředí**:
- `SECRET_KEY`: Kryptografický klíč (změnit v produkci!)
- `DATABASE_URL`: Připojení k DB (`sqlite:///parental_control.db` nebo PostgreSQL)
- `BACKEND_HOST`: IP adresa pro bind (0.0.0.0)
- `BACKEND_PORT`: Port (výchozí 8000/8443)

### Frontend

**Soubor**: `.env` (build time)

- `VITE_API_URL`: URL backendu

## Bezpečnostní doporučení

1. **SSL/TLS**: Pro produkci vždy používejte HTTPS (Instalátor serveru generuje certifikáty automaticky).
2. **Firewall**: Povolte port 8443 (Server) a blokujte nepotřebné porty na klientech.
3. **Admin účet**: Používejte silná hesla pro rodičovský účet.
