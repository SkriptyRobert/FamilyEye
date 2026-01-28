# Frontend dokumentace

## Přehled

React dashboard pro správu rodičovské kontroly. Single Page Application (SPA) s moderním UI.

## Struktura

```
frontend/src/
├── main.jsx              # Entry point
├── App.jsx                # Hlavní routing
├── App.css                # Globální styly
├── index.css              # Base styly
├── components/            # React komponenty
│   ├── auth/
│   │   ├── Login.jsx      # Přihlášení
│   │   └── Login.css
│   ├── Dashboard.jsx      # Hlavní dashboard
│   ├── DeviceList.jsx     # Seznam zařízení
│   ├── DevicePairing.jsx  # Párování zařízení
│   ├── QRPairing.jsx      # Párování přes QR kód
│   ├── DeviceOwnerSetup.jsx  # Nastavení Android Device Owner
│   ├── RuleEditor.jsx     # Editor pravidel (kontejner)
│   ├── RuleEditor/        # Podkomponenty editoru pravidel
│   │   ├── RuleCards.css
│   │   └── RuleForms.css
│   ├── rules/             # Komponenty pro pravidla
│   │   ├── AppPicker.jsx, RuleCard.jsx, ScheduleForm.jsx
│   │   ├── HiddenAppsSection.jsx, constants.js, index.js
│   ├── devices/           # Karty a akce zařízení
│   │   ├── DeviceCard.jsx, QuickActionsBar.jsx
│   │   ├── platforms/AndroidDeviceCard.jsx, WindowsDeviceCard.jsx
│   │   └── index.js
│   ├── modals/
│   │   ├── AllAppsModal.jsx   # Výběr aplikací
│   │   ├── ScreenshotModal.jsx # Náhled screenshotu
│   │   └── index.js
│   ├── limits/            # Čip a progress bar limitů
│   │   ├── LimitChip.jsx, LimitProgressBar.jsx, index.js
│   ├── overview/          # Přehled – filtry a globální statistiky
│   │   ├── DeviceFilter.jsx, GlobalStats.jsx
│   ├── shield/            # Alert karty, sekce kategorií (Smart Shield)
│   │   ├── AlertCard.jsx, CategorySection.jsx, index.js
│   ├── SmartShield/       # UI Smart Shield (AlertCard, FilterChips, KeywordManager)
│   ├── SmartShield.jsx, SmartShieldView.jsx
│   ├── SmartInsights.jsx  # Smart Insights metriky
│   ├── StatusOverview.jsx  # Přehled stavu zařízení
│   ├── Reports.jsx        # Statistiky (kontejner)
│   ├── Reports/           # Podkomponenty reportů
│   │   ├── ProcessMonitor.jsx, ReportApps.jsx, ReportMetrics.jsx
│   ├── Overview.jsx       # Přehled
│   ├── DayPicker.jsx       # Výběr dne
│   ├── NotificationDropdown.jsx  # Rozbalovací notifikace
│   ├── setup/
│   │   ├── InitialSetup.jsx     # Prvotní nastavení
│   │   └── InitialSetup.css
│   ├── charts/            # Grafické komponenty
│   │   ├── ActivityHeatmap.jsx, ActivityTimeline.jsx
│   │   ├── UsageTrendChart.jsx, WeeklyBarChart.jsx, WeeklyPatternChart.jsx
│   │   └── AppDetailsModal.jsx
│   ├── DynamicIcon.jsx    # Dynamická ikona podle typu
│   └── ...
├── services/
│   ├── api.js             # API klient
│   └── websocket.js       # WebSocket klient
├── hooks/
│   ├── useDevices.js, useRules.js, useQuickActions.js
│   └── index.js
├── utils/
│   ├── auth.js            # Autentizace
│   ├── date.js            # Formátování datumů
│   └── formatting.js      # Formátování (včetně getAppIcon)
└── styles/
    └── design-tokens.css  # Design tokeny
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
- `/login` - Přihlášení (komponenta `auth/Login.jsx`)
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

### RuleEditor.jsx a podsložka RuleEditor/

**RuleEditor.jsx**: Kontejner editoru pravidel – vytváření, úprava a mazání pravidel (app_block, time_limit, daily_limit, schedule, lock_device, network_block, website_block).

**RuleEditor/** (styly a podkomponenty): `RuleCards.css`, `RuleForms.css` – karty pravidel a formuláře.

### rules/

Komponenty pro práci s pravidly: **AppPicker.jsx** (výběr aplikace), **RuleCard.jsx** (karta pravidla), **ScheduleForm.jsx** (časové okno), **HiddenAppsSection.jsx** (skryté aplikace), **constants.js**, **index.js**.

### devices/ a devices/platforms/

**DeviceCard.jsx**, **QuickActionsBar.jsx** – karta zařízení a rychlé akce. **platforms/AndroidDeviceCard.jsx**, **platforms/WindowsDeviceCard.jsx** – platformně specifické karty.

### modals/

**AllAppsModal.jsx** – výběr všech aplikací. **ScreenshotModal.jsx** – zobrazení screenshotu z Smart Shield.

### limits/

**LimitChip.jsx**, **LimitProgressBar.jsx** – čip a progress bar pro zobrazení limitů použití.

### overview/

**DeviceFilter.jsx**, **GlobalStats.jsx** – filtry a globální statistiky na stránce přehledu.

### shield/ a SmartShield/

**shield/**: **AlertCard.jsx**, **CategorySection.jsx** – karty alertů a sekce kategorií Smart Shield.

**SmartShield.jsx**, **SmartShieldView.jsx** – hlavní view Smart Shield. **SmartShield/** – styly a komponenty (AlertCard, FilterChips, KeywordManager).

### Ostatní stránkové komponenty

- **QRPairing.jsx** – párování přes QR kód.
- **DeviceOwnerSetup.jsx** – průvodce nastavením Android Device Owner.
- **SmartInsights.jsx** – Smart Insights metriky (focus, wellness).
- **StatusOverview.jsx** – přehled stavu zařízení.
- **DayPicker.jsx** – výběr dne pro reporty.
- **NotificationDropdown.jsx** – rozbalovací notifikace (např. Smart Shield alerty).
- **setup/InitialSetup.jsx** – prvotní nastavení aplikace (účet, konfigurace).

### Reports.jsx a Reports/

**Reports.jsx**: Kontejner statistik – grafy, filtrování podle období.

**Reports/**: **ProcessMonitor.jsx** (běžící procesy), **ReportApps.jsx** (aplikace), **ReportMetrics.jsx** (metriky).

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

## Služby a hooky

### API (`services/api.js`)

**Funkce**:
- HTTP klient (Axios)
- Automatické přidání JWT tokenu
- Error handling
- Base URL konfigurace

**Metody**:
- `get()`, `post()`, `put()`, `delete()`
- Automatická autentizace

### WebSocket (`services/websocket.js`)

Připojení k backendu pro real-time zprávy (notifikace, aktualizace zařízení).

### Hooky (`hooks/`)

**useDevices.js** – načtení a aktualizace seznamu zařízení. **useRules.js** – pravidla pro zařízení. **useQuickActions.js** – rychlé akce (lock, unlock, pause-internet).

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

