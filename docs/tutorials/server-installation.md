# Instalace Serveru

Průvodce nasazením centrálního serveru FamilyEye. Server můžete provozovat na Windows (jako nativní službu) nebo v Docker kontejneru.

## Přehled metod

1. **Windows Instalátor (Doporučeno pro domácnosti)** - Snadná instalace na rodičovský notebook/PC.
2. **Docker / Kubernetes (Pro pokročilé)** - Pro běh na NAS (Synology, unRAID) nebo Linux serveru.
3. **Manuální Python spuštění** - Pro vývoj a testování.

---

## Metoda 1: Windows Instalátor (Doporučeno)

Stáhněte `FamilyEyeServer_Setup_*.exe` z GitHub releases.

### Průběh instalace

1. **Konfigurace Portu**
   - Výchozí port je **8443** (HTTPS).
   - Můžete změnit, pokud je port obsazen.

2. **Certifikáty a SSL**
   - Instalátor **automaticky vygeneruje** SSL certifikáty pro HTTPS.
   - nainstaluje **FamilyEye Root CA** do důvěryhodných kořenových certifikátů Windows na serveru (aby prohlížeč nehlásil chybu).
   - Pro ostatní zařízení (telefony, dětský PC) si můžete certifikát stáhnout později z dashboardu.

3. **Dokončení**
   - Instalátor zaregistruje službu `FamilyEyeServer`.
   - Startovací typ je "Automaticky" (spustí se po startu PC).
   - Otevře se dashboard v prohlížeči (např. `https://localhost:8443`).

### První přihlášení
Při prvním přístupu na dashboard budete vyzváni k vytvoření **Administrátorského účtu** (e-mail a heslo). Tento účet slouží k přihlášení do rodičovké aplikace.

---

## Metoda 2: Docker (Pro NAS/Linux)

Pokud máte NAS (Synology, QNAP) nebo domácí server s Dockerem.

### Požadavky
- Docker Engine & Docker Compose

### docker-compose.yml

```yaml
version: '3.8'

services:
  familyeye-server:
    image: ghcr.io/skriptyrobert/familyeye-server:latest
    container_name: familyeye_server
    restart: unless-stopped
    ports:
      - "8443:8443"
    volumes:
      - ./data:/app/data       # Databáze a logy
      - ./certs:/app/certs     # Certifikáty
    environment:
      - BACKEND_PORT=8443
      - SECRET_KEY=zmente_na_nahodny_retezec
```

### Spuštění

```bash
docker-compose up -d
```

Po spuštění je server dostupný na `https://IP-VAS-SERVERU:8443`.

---

## Metoda 3: Manuální instalace (Python)

Vyžaduje nainstalovaný Python 3.9+.

1. Stáhněte zdrojové kódy (backend).
2. Nainstalujte závislosti:
   ```bash
   pip install -r requirements.txt
   ```
3. Spuštění serveru:
   ```bash
   python run_https.py
   ```
4. Pro instalaci jako služby použijte `service_wrapper.py`:
   ```bash
   python service_wrapper.py install
   python service_wrapper.py start
   ```

---

## Konfigurace Firewallu

Pro správnou funkci musí být server dostupný pro agenty v lokální síti.

- **Windows**: Instalátor automaticky přidá pravidlo pro příchozí spojení na portu 8443 (`Parental Control Server`).
- **Linux/Docker**: Ujistěte se, že port 8443 je otevřený (ufw, iptables).

### Ověření dostupnosti
Z jiného zařízení v síti (např. z telefonu) zkuste otevřít v prohlížeči:
`https://IP-SERVERU:8443`

Pokud se načte dashboard (i s varováním o certifikátu), server je dostupný.
