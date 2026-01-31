# FamilyEye Server - Docker a Kubernetes

## Jak to funguje

- **Jeden kontejner** = backend (FastAPI) + zbuildovaný frontend (statické soubory). Backend servíruje API i SPA z jedné image.
- **PostgreSQL** se používá jen v Docker/Kubernetes;  env `DATABASE_URL=postgresql://...` a driver v `docker/server/requirements-docker.txt`.
- **CI/CD**: při push do main/master (nebo android-fix-process) se spouští buildy (Android APK, Windows installer, Docker image). Release se vytvoří při push tagu `v*`.

---

## Spuštění lokálně (Docker Compose)

Potřebujete: Docker a Docker Compose.

### **1. Připravit `.env` Jinak nebude správně načtena URL pro registraci, QR párování a bude použita IP z Docker-network!**

```bash
cd docker/server
cp .env.example .env
# upravte alespoň BACKEND_URL (veřejná URL serveru)
# BACKEND_URL=https://<YOUR_SERVER_IP>:8443
```

### 2. Stáhnout image a spustit server + PostgreSQL

```bash
cd docker/server
docker compose pull
docker compose up -d
```

### 3. Otevřít v prohlížeči

- Dashboard: https://localhost:8443
- API docs: https://localhost:8443/docs

První přihlášení: zaregistrujte se v UI (nebo vytvořte admina přes `backend/init_admin.py` jinde a pak se přihlaste).

### 4. Zastavení

```bash
cd docker/server
docker compose down
```

Data PostgreSQL zůstávají v Docker volume `postgres_data`; při `docker compose down -v` se volume smaže.

---

## Otestování CI/CD (GitHub Actions)

### Kdy se co spustí

| Workflow | Kdy se spustí | Co dělá |
|----------|----------------|---------|
| Backend Tests | Změny v `backend/**` | pytest |
| Frontend Tests | Změny v `frontend/**` | npm test |
| Android Tests | Změny v `clients/android/**` | unit testy + build APK (artefakt `android-apk`) |
| Build Windows Agent | Změny v `installer/agent/**` nebo `clients/windows/**` | PyInstaller + Inno Setup, artefakt `windows-agent-installer` |
| Build Server (Docker) | Změny v `backend/**`, `frontend/**`, `docker/**` | build frontendu, Docker image, push do GHCR |
| Create Release | Push tagu `v*` (např. `v2.4.0`) | Vytvoří GitHub Release; binárky zatím přikládáte ručně |

### Jak otestovat

1. **Lokálně bez pushu**  
   - Docker: viz výše (`docker compose up --build` v `docker/server`).  
   - Ostatní (backend, frontend, agent) – beze změn, podle stávající dokumentace (README, docs).

2. **Spuštění workflow na GitHubu**  
   - Push do větve `main`, `master` nebo `android-fix-process`: podle změněných cest se spustí příslušné workflow (Backend/Frontend/Android Tests, Build Windows Agent, Build Server).  
   - Artefakty: v runu workflow záložka „Summary“ / „Artifacts“ – stáhnete APK nebo Windows .exe.  
   - Docker image: po úspěšném Build Server je image v GHCR: `ghcr.io/<owner>/<repo>/familyeye-server:latest` (a podle SHA).

3. **Vytvoření release**  
   - Vytvořte a pushněte tag, např.:  
     `git tag v2.4.0`  
     `git push origin v2.4.0`  
   - Workflow „Create Release“ vytvoří release s názvem podle tagu.  
   - APK a Windows installer zatím přidejte k release ručně (stáhnout z artefaktů příslušných workflow a nahrát do release).

---

## Kubernetes (volitelné)

Soubory v `kubernetes/` slouží k nasazení už zbuildované image do clusteru.

1. **PostgreSQL**  
   V deploymentu je `DATABASE_URL` ze Secretu; musíte mít v clusteru běžící PostgreSQL (vlastní Deployment nebo managed služba) a v Secretu správnou URL (např. služba `postgres-service:5432`).

2. **Image**  
   V `kubernetes/deployment.yaml` je uvedená image `ghcr.io/SkriptyRobert/FamilyEye/familyeye-server:latest`. Po prvním úspěšném Build Server workflow bude image k dispozici; pro privátní image nastavte imagePullSecrets.

3. **Spuštění**  
   ```bash
   kubectl apply -f kubernetes/deployment.yaml
   kubectl apply -f kubernetes/service.yaml
   kubectl apply -f kubernetes/ingress.yaml
   ```  
   Předtím upravte `kubernetes/deployment.yaml` (Secret, image) a `kubernetes/ingress.yaml` (host, TLS dle potřeby).

Ingress je napsaný pro **nginx ingress controller**; pro jiný controller je potřeba upravit anotace a spec.
