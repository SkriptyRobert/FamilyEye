# Frontend dokumentace

## Přehled

React dashboard pro správu rodičovské kontroly. Single Page Application (SPA) s moderním UI.

## Struktura

```
frontend/src/
├── main.jsx              # Entry point
├── App.jsx               # Hlavní routing
├── App.css                # Globální styly
├── index.css              # Base styly
├── components/            # React komponenty
│   ├── Dashboard.jsx      # Hlavní dashboard
│   ├── DeviceList.jsx    # Seznam zařízení
│   ├── DevicePairing.jsx # Párování zařízení
│   ├── RuleEditor.jsx    # Editor pravidel
│   ├── Reports.jsx       # Statistiky
│   ├── Overview.jsx      # Přehled
│   ├── Login.jsx         # Přihlášení
│   ├── InitialSetup.jsx  # Prvotní nastavení
│   └── charts/           # Grafické komponenty
├── services/
│   └── api.js            # API klient
└── utils/
    ├── auth.js           # Autentizace
    ├── date.js           # Formátování datumů
    └── formatting.js     # Formátování
```

## Spuštění

### Vývoj

```bash
cd frontend
npm install
npm run dev
```

Server běží na `http://localhost:5173`

### Build

```bash
npm run build
```

Výstup: `frontend/dist/`

## Komponenty

### App.jsx

**Funkce**:
- Routing (React Router)
- Autentizace
- Dark mode toggle
- Initial setup flow

**Routes**:
- `/` - Dashboard (vyžaduje auth)
- `/login` - Přihlášení
- `*` - Initial setup (pokud není konfigurováno)

### Dashboard.jsx

**Funkce**:
- Hlavní navigace
- Přepínání mezi sekcemi
- Real-time aktualizace
- WebSocket připojení

**Sekce**:
- Overview - Přehled zařízení
- Devices - Seznam zařízení
- Rules - Pravidla
- Reports - Statistiky

### DeviceList.jsx

**Funkce**:
- Zobrazení všech zařízení
- Status (online/offline)
- Rychlé akce (lock, unlock, pause internet)
- Smazání zařízení

**Stavy**:
- `is_online` - Online (last_seen < 5 min)
- `has_lock_rule` - Zamčeno
- `has_network_block` - Internet zablokován

### DevicePairing.jsx

**Funkce**:
- Generování pairing tokenu
- Zobrazení QR kódu
- Zobrazení tokenu pro manuální zadání
- Instrukce pro párování

### RuleEditor.jsx

**Funkce**:
- Vytváření pravidel
- Úprava pravidel
- Smazání pravidel
- Typy pravidel:
  - Blokování aplikace
  - Časový limit
  - Denní limit
  - Časové okno
  - Blokování webu

### Reports.jsx

**Funkce**:
- Zobrazení statistik
- Grafy použití
- Filtrování podle období
- Export dat (případně)

**Grafy**:
- Activity Heatmap - Použití po hodinách
- Usage Trend Chart - Trendy v čase
- Weekly Bar Chart - Týdenní přehled
- Weekly Pattern Chart - Vzory podle dne

### Charts komponenty

**ActivityHeatmap.jsx**:
- Heatmap použití po hodinách a dnech
- Barvy podle intenzity

**UsageTrendChart.jsx**:
- Čárový graf trendů
- Filtrování podle období

**WeeklyBarChart.jsx**:
- Sloupcový graf týdenního použití

**WeeklyPatternChart.jsx**:
- Průměrné použití podle dne v týdnu

**AppDetailsModal.jsx**:
- Detail aplikace
- Statistiky použití
- Trendy

## Služby

### API (`services/api.js`)

**Funkce**:
- HTTP klient (Axios)
- Automatické přidání JWT tokenu
- Error handling
- Base URL konfigurace

**Metody**:
- `get()`, `post()`, `put()`, `delete()`
- Automatická autentizace
- Refresh token (případně)

### Auth (`utils/auth.js`)

**Funkce**:
- `getToken()` - Získání JWT tokenu
- `setToken()` - Uložení tokenu
- `removeToken()` - Odstranění tokenu
- `isAuthenticated()` - Kontrola autentizace

**Storage**: `localStorage`

## Konfigurace

### app-config.json

**Umístění**: `backend/app/config/app-config.json`

**Struktura**:
```json
{
  "backend_url": "http://localhost:8000",
  "api_version": "1.0.0"
}
```

**Načítání**: Backend servuje konfiguraci přes API endpoint

## Styling

### CSS architektura

- **Globální**: `App.css`, `index.css`
- **Komponenty**: `ComponentName.css`
- **Dark mode**: CSS třída `.dark`

### Dark mode

**Toggle**: Tlačítko v Dashboard
**Storage**: `localStorage.darkMode`
**Aplikace**: CSS třída na `document.documentElement`

## Routing

**Knihovna**: React Router 6.20.0

**Struktura**:
- `/` - Dashboard (protected)
- `/login` - Přihlášení
- `*` - Initial setup nebo redirect

**Protected routes**: Kontrola `isAuthenticated`

## Real-time aktualizace

**WebSocket**: Připojení v Dashboard komponentě

**Použití**:
- Aktualizace statusu zařízení
- Real-time notifikace
- Synchronizace dat

## Optimalizace

### Performance

- **Code splitting**: Lazy loading komponent
- **Memoization**: React.memo pro těžké komponenty
- **Virtual scrolling**: Pro dlouhé seznamy (případně)

### Build

- **Vite**: Rychlý build tool
- **Tree shaking**: Odstranění nepoužívaného kódu
- **Minifikace**: CSS a JS

## Rozšíření

### Přidání nové komponenty

1. Vytvořit soubor v `components/`
2. Exportovat jako default
3. Přidat do routing v `App.jsx` nebo použít v existující komponentě
4. Přidat CSS soubor

### Přidání nového API endpointu

1. Přidat metodu do `services/api.js`
2. Použít v komponentě
3. Přidat error handling

### Přidání nového grafu

1. Vytvořit komponentu v `components/charts/`
2. Použít Recharts knihovnu
3. Přidat do Reports komponenty
4. Přidat CSS styling

## Testování

```bash
# Spuštění dev serveru
npm run dev

# Build pro produkci
npm run build

# Preview produkčního buildu
npm run preview
```

## Produkční nasazení

1. Build: `npm run build`
2. Kopírovat `dist/` do backend `frontend/dist/`
3. Backend automaticky servuje statické soubory

Viz [DEPLOYMENT.md](./DEPLOYMENT.md) pro detailní návod.

