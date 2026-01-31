# Vývojová dokumentace

## Přehled

Návod pro vývojáře na práci s projektem, přidávání funkcí a úpravy kódu.

## Vývojové prostředí

### Požadavky

- **Python**: 3.8+
- **Node.js**: 18+
- **Git**: Pro verzování
- **IDE**: VS Code, PyCharm, nebo jiný

### Setup

#### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python run_https.py
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

#### Agent

```bash
cd clients/windows
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m agent.main
```

### Vývojové skripty

V adresáři **`dev/`** jsou batch skripty pro rychlé spuštění a zastavení celého vývojového prostředí na Windows.

- **`dev/start.bat`** – Spustí backend a frontend najednou. Nejprve uvolní porty 8000 a 5173 (ukončí procesy, které je používají), zjistí lokální IP (např. 192.168.x.x), spustí backend jako `python run_https.py` v `backend/` a frontend jako `npm run dev -- --host <IP> --port 5173` v `frontend/`. Po spuštění jsou dostupné: Dashboard UI na `http://<IP>:5173`, Backend API na `https://localhost:8000`. Skript neukončuje běh po stisku klávesy – procesy zastavíte pomocí `dev/STOP.bat`.
- **`dev/STOP.bat`** – Zastaví vývojové prostředí: ukončí procesy `python.exe` a `node.exe` (backend a frontend). Spusťte ho v samostatném okně nebo až po ukončení `start.bat`.

**Použití**: Z kořene projektu spusťte `dev\start.bat`. Pro zastavení všech služeb spusťte `dev\STOP.bat`.

## Struktura projektu

```
Parental-Control_Enterprise/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── api/         # API endpointy
│   │   ├── services/    # Business logika
│   │   └── ...
│   ├── requirements.txt
│   └── run_https.py
├── frontend/            # React frontend
│   ├── src/
│   │   ├── components/  # React komponenty
│   │   ├── services/   # API klient
│   │   └── ...
│   ├── package.json
│   └── vite.config.js
├── clients/windows/     # Windows agent
│   ├── agent/
│   │   ├── main.py
│   │   └── ...
│   └── requirements.txt
└── docs/                # Dokumentace
```

## CI/CD – GitHub Actions

Workflow jsou v [.github/workflows/](../.github/workflows/). Spouštějí se na push a pull request do větví `main`, `master`, `android-fix-process` při změnách v příslušných cestách.

| Workflow | Soubor | Kdy se spustí | Co dělá |
|----------|--------|----------------|---------|
| **Backend Tests** | [backend.yml](../.github/workflows/backend.yml) | Změny v `backend/**` | Python 3.11, `pip install`, `pytest tests/` s coverage, upload do Codecov |
| **Frontend Tests** | [frontend.yml](../.github/workflows/frontend.yml) | Změny v `frontend/**` | Node 18, `npm ci`, `npm test -- --run --coverage` |
| **Android Tests** | [android.yml](../.github/workflows/android.yml) | Změny v `clients/android/**` | JDK 17, `./gradlew test`, upload artifactů s test výsledky |
| **Create Release** | [release.yml](../.github/workflows/release.yml) | Po úspěšném dokončení workflow „Run Tests” na `main`/`master` | Vytvoření GitHub Release s tagem odvozeným od `versionName` z Android `build.gradle.kts` |

**Poznámka**: Release workflow předpokládá workflow s názvem „Run Tests”; pokud máte jeden složený workflow, který volá backend/frontend/android testy, pojmenujte ho takto. V opačném případě upravte `workflow_run.workflows` v `release.yml` podle skutečných názvů workflow.

## Přidávání funkcí

### Nový API endpoint

1. **Vytvořit nebo upravit modul** v `backend/app/api/` (soubor, např. `api/foo.py`, nebo podmodul v balíčku `api/devices/`, `api/reports/`):

```python
from fastapi import APIRouter, Depends
from ..api.auth import get_current_parent

router = APIRouter()

@router.get("/new-endpoint")
async def new_endpoint(current_user: User = Depends(get_current_parent)):
    return {"message": "Hello"}
```

2. **Zaregistrovat router** v `backend/app/main.py`. U balíčků (např. `api.devices`) se importuje router z `__init__.py`:

```python
from .api import auth, devices, rules, reports, ...
app.include_router(devices.router, prefix="/api/devices", tags=["devices"])
```

3. **Aktualizovat dokumentaci** v [API.md](API.md) a [reference/api-docs.md](reference/api-docs.md)

### Nová frontend komponenta

1. **Vytvořit komponentu** v `frontend/src/components/`:

```jsx
import React from 'react'
import './NewComponent.css'

export default function NewComponent() {
  return <div>New Component</div>
}
```

2. **Přidat do routing** v `frontend/src/App.jsx`:

```jsx
import NewComponent from './components/NewComponent'

<Route path="/new" element={<NewComponent />} />
```

3. **Aktualizovat dokumentaci** v `docs/FRONTEND.md`

### Nový typ pravidla

1. **Přidat do backendu** (`backend/app/api/rules.py`):
   - Validace v `RuleCreate` schématu
   - Logika v endpointu

2. **Přidat do agenta** (`clients/windows/agent/enforcer/core.py`):
   - Logika v `_update_blocked_apps()` v `enforcer/app_blocking.py`
   - Vynucování v `update()` v `enforcer/core.py`

3. **Přidat do frontendu** (`frontend/src/components/RuleEditor.jsx`):
   - UI pro vytvoření pravidla
   - Zobrazení pravidla

4. **Aktualizovat dokumentaci**:
   - `docs/API.md` - Nový typ pravidla
   - `docs/AGENT.md` - Vynucování
   - `docs/FRONTEND.md` - UI

### Nová databázová tabulka

1. **Vytvořit model** v `backend/app/models.py`:

```python
class NewModel(Base):
    __tablename__ = "new_table"
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    # ...
```

2. **Vytvořit schéma** v `backend/app/schemas.py`:

```python
class NewModelCreate(BaseModel):
    name: str

class NewModelResponse(BaseModel):
    id: int
    name: str
    # ...
```

3. **Tabulka se vytvoří automaticky** při startu (`init_db()`)

4. **Aktualizovat dokumentaci** v `docs/DATABASE.md`

## Testování

### Backend

```bash
# Spuštění testů (pokud existují)
pytest tests/

# Manuální testování API
# Použijte curl, Postman nebo frontend pro testování API endpointů
```

### Frontend

```bash
# Spuštění dev serveru
npm run dev

# Build test
npm run build
```

### Agent

```bash
# Spuštění agenta
python -m agent.main

# Testování s backendem
# Spustit backend a agent, ověřit komunikaci
```

## Code style

### Python

- **PEP 8** - Standardní Python style
- **Type hints** - Použití type hints kde je to možné
- **Docstrings** - Dokumentace funkcí a tříd

### JavaScript/React

- **ES6+** - Moderní JavaScript
- **Functional components** - Preferovat funkční komponenty
- **Hooks** - Použití React hooks
- **CSS Modules** - Pro styling komponent

## Git workflow

### Branching

- `main` - Produkční kód
- `develop` - Vývojová větev
- `feature/xxx` - Nové funkce
- `fix/xxx` - Opravy chyb

### Commits

- **Popisné zprávy** - Co a proč
- **Malé commity** - Jedna změna = jeden commit
- **Conventional commits** (volitelně):
  - `feat:` - Nová funkce
  - `fix:` - Oprava chyby
  - `docs:` - Dokumentace
  - `refactor:` - Refaktoring

## Debugging

### Backend

```python
# Logging
import logging
logger = logging.getLogger(__name__)
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
```

**Logy**: `backend/app.log`

### Frontend

```javascript
// Console logging
console.log("Debug message")
console.error("Error message")

// React DevTools
// Použít React DevTools pro debugging komponent
```

### Agent

```python
# Logging
from .logger import get_logger
logger = get_logger('MODULE')
logger.info("Info message")
```

**Logy**: `clients/windows/agent.log`

## Performance

### Backend

- **Cache** - Použití cache pro statistiky
- **Indexy** - Databázové indexy pro rychlé dotazy
- **Agregace** - Agregace na databázové úrovni

### Frontend

- **Code splitting** - Lazy loading komponent
- **Memoization** - React.memo pro těžké komponenty
- **Virtual scrolling** - Pro dlouhé seznamy

### Agent

- **Threading** - Asynchronní operace
- **Caching** - Cache pravidel a statistik
- **Optimální intervaly** - Vyvážení mezi rychlostí a zátěží

## Bezpečnost

### Best practices

- **Hesla** - bcrypt hash, nikdy plaintext
- **JWT** - Krátká platnost, refresh tokeny
- **API Key** - Unikátní pro každé zařízení
- **HTTPS** - V produkci vždy HTTPS
- **Input validation** - Validace všech vstupů
- **SQL injection** - Použití ORM (SQLAlchemy)

### Audit

- **Pravidelné kontroly** - Kontrola závislostí
- **Security updates** - Aktualizace knihoven
- **Log monitoring** - Sledování podezřelé aktivity

## Dokumentace

### Aktualizace dokumentace

Při přidávání funkcí aktualizujte:

1. **Příslušný modul** (BACKEND.md, FRONTEND.md, atd.)
2. **API.md** - Pro nové endpointy
3. **DATABASE.md** - Pro nové tabulky
4. **INDEX.md** - Pro nové sekce

### Formátování

- **Markdown** - Standardní Markdown syntax
- **Code blocks** - Syntax highlighting
- **Stručnost** - Stručné a jasné
- **Příklady** - Praktické příklady kódu

## Build a distribuce

### Backend

```bash
# Build instalátoru (Inno Setup)
# Viz installer/server/setup_server.iss
```

### Frontend

```bash
cd frontend
npm run build
# Výstup: frontend/dist/
```

### Agent

```bash
# Build instalátoru (Inno Setup)
# Viz installer/agent/setup_agent.iss
```

## Kontribuce

### Pull requests

1. **Fork** projektu
2. **Vytvořit branch** pro funkci
3. **Commit** změn
4. **Push** do forku
5. **Otevřít Pull Request**

### Code review

- **Kontrola kódu** - Kontrola kvality a stylu
- **Testování** - Ověření funkcionality
- **Dokumentace** - Aktualizace dokumentace

## Podpora

Pro dotazy a pomoc:
- **Issues** - GitHub Issues
- **Dokumentace** - Tato dokumentace
- **README** - Hlavní README.md

