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
python run_server.py
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
python run_agent.py
```

## Struktura projektu

```
Parental-Control_Enterprise/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── api/         # API endpointy
│   │   ├── services/    # Business logika
│   │   └── ...
│   ├── requirements.txt
│   └── run_server.py
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

## Přidávání funkcí

### Nový API endpoint

1. **Vytvořit nebo upravit router** v `backend/app/api/`:

```python
from fastapi import APIRouter, Depends
from ..api.auth import get_current_parent

router = APIRouter()

@router.get("/new-endpoint")
async def new_endpoint(current_user: User = Depends(get_current_parent)):
    return {"message": "Hello"}
```

2. **Zaregistrovat router** v `backend/app/main.py`:

```python
from .api import new_module

app.include_router(new_module.router, prefix="/api/new", tags=["new"])
```

3. **Aktualizovat dokumentaci** v `docs/API.md`

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

2. **Přidat do agenta** (`clients/windows/agent/enforcer.py`):
   - Logika v `_update_blocked_apps()`
   - Vynucování v `update()`

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
python verify_api.py
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
python run_agent.py

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

