# 📱 Parental Control Dashboard - UX/UI Redesign Specification

## 🎯 Design Philosophy

> **"Rodiče musí pochopit stav zařízení do 5 sekund"**

Tento dokument definuje nový přístup k UX/UI a datovému modelu pro rodičovský dashboard.

---

## 📊 Datový Model - Stavy Zařízení

### Explicitní stavy (State Machine)

```
┌─────────────────┐
│    OFFLINE      │ ◄── Zařízení se nepřipojilo > 5 minut
├─────────────────┤
│ • Ikona: 📴     │
│ • Barva: RED    │
│ • Popis: "Nepřipojeno" │
└────────┬────────┘
         │ (heartbeat)
         ▼
┌─────────────────┐
│    ONLINE       │ ◄── Zařízení se hlásí, monitorování běží
├─────────────────┤
│ • Ikona: ✅     │
│ • Barva: GREEN  │
│ • Popis: "Aktivní" │
└────────┬────────┘
         │ (parent action)
         ▼
┌─────────────────┐
│    LOCKED       │ ◄── Rodič zamkl zařízení
├─────────────────┤
│ • Ikona: 🔒     │
│ • Barva: ORANGE │
│ • Popis: "Zamčeno" │
└────────┴────────┘
         │ (parent action)
         ▼
┌─────────────────┐
│ INTERNET_PAUSED │ ◄── Internet dočasně vypnut
├─────────────────┤
│ • Ikona: 🚫     │
│ • Barva: AMBER  │
│ • Popis: "Internet vypnut" │
└─────────────────┘
```

### Klíčové časové značky

| Pole | Účel | UI Zobrazení |
|------|------|--------------|
| `paired_at` | Kdy bylo zařízení poprvé připojeno | "Monitorování od 28.12.2025" |
| `last_seen` | Poslední heartbeat agenta | "před 2 minutami" |
| `today_usage_seconds` | Čas monitorování dnes | "2h 15m" |
| `first_report_today` | První report dnes | Pro interní výpočty |
| `last_report_today` | Poslední report dnes | Pro interní výpočty |

---

## 🖥️ UI Struktura

### 1. Device Status Header (vždy viditelný)

```
┌──────────────────────────────────────────┐
│  🖥️ Honzíkův počítač           ✅ Aktivní │
│  ────────────────────────────────────────│
│  📅 Monitorování od 28.12.2025           │
│  🔄 Naposledy před 2 minutami            │
└──────────────────────────────────────────┘
```

### 2. Today Overview (hlavní insight)

```
┌──────────────────────────────────────────┐
│          DNEŠNÍ ČAS                       │
│                                           │
│          2h 15m                           │
│          ━━━━━━━━━━━━━░░░░░ z 8h          │
│                                           │
│  Nejpoužívanější:                         │
│  • Minecraft   45m                        │
│  • YouTube     32m                        │
│  • Chrome      28m                        │
└──────────────────────────────────────────┘
```

### 3. Quick Actions (vždy přístupné)

```
┌────────────────┐ ┌────────────────┐
│ 🔒 Zamknout    │ │ 📵 Internet    │
└────────────────┘ └────────────────┘
```

### 4. Expanded Details (kliknutím)

```
┌──────────────────────────────────────────┐
│ DETAILY                                   │
│ ─────────────────────────────────────────│
│ 📅 Monitorování aktivní od               │
│    28. prosince 2025 v 18:32             │
│                                           │
│ 🔄 Poslední kontrola                     │
│    dnes v 11:15                          │
│ ─────────────────────────────────────────│
│ ┌────────────────┐ ┌────────────────┐    │
│ │ 🔓 Odemknout   │ │ 🌐 Obnovit     │    │
│ └────────────────┘ │    internet    │    │
│                    └────────────────┘    │
└──────────────────────────────────────────┘
```

---

## 📱 Mobile-First Design

### Breakpoints

| Breakpoint | Layout |
|------------|--------|
| < 640px | Mobilní - bottom navigation, karty na celou šířku |
| 640px - 1024px | Tablet - větší karty, side menu na klik |
| > 1024px | Desktop - side menu vždy viditelné, 2-3 karty v řadě |

### Navigace

**Mobile:**
```
┌──────────────────────────────────────────┐
│ 📊        📱        ⚙️         📈        │
│ Přehled   Zařízení  Pravidla   Statistiky│
└──────────────────────────────────────────┘
```

**Desktop:**
```
┌──────────┬───────────────────────────────┐
│ 📊 Přehled│                              │
│ 📱 Zařízení│      HLAVNÍ OBSAH           │
│ ⚙️ Pravidla│                              │
│ 📈 Statistiky│                           │
│ ➕ Přidat │                              │
└──────────┴───────────────────────────────┘
```

---

## 🔄 Synchronizace Dat

### Automatický refresh

- Data se automaticky obnovují každých **30 sekund**
- Při akci (zamknout, internet off) se data obnoví ihned
- **Žádné manuální "Sync" tlačítko** - uživatel nemusí přemýšlet

### Indikátor čerstvosti dat

```
● Aktuální data         (< 60s od refresh)
● Data před 2 min       (< 5min)
● Data mohou být zastaralá (> 5min)
```

---

## 🗣️ Jazyk pro rodiče

### ❌ Nepoužívat (technický žargon)

- "Agent"
- "Policy"
- "Sync"
- "Heartbeat"
- "1628.928257 sekund"

### ✅ Používat (srozumitelné fráze)

- "Zařízení se hlásí"
- "Pravidla"
- "Aktuální data"
- "Naposledy před 2 minutami"
- "2 hodiny 15 minut"

---

## 📐 Formátování Hodnot

### Čas

| Vstup (sekundy) | Výstup (zkráceně) | Výstup (plně) |
|-----------------|-------------------|---------------|
| 0 | 0m | 0 minut |
| 45 | <1m | méně než minuta |
| 300 | 5m | 5 minut |
| 3600 | 1h | 1 hodina |
| 8100 | 2h 15m | 2 hodiny 15 minut |

### Relativní čas

| Stáří | Výstup |
|-------|--------|
| < 30s | právě teď |
| < 60s | před chvílí |
| 1 min | před minutou |
| 2-5 min | před X minutami |
| 5-60 min | před X min |
| 1 hodina | před hodinou |
| 2-24 hodin | před X h |
| 1 den | včera |
| 2-7 dní | před X dny |
| > 7 dní | DD. MMM |

---

## 🎨 Barevná Paleta

### Stavy

| Stav | Barva | CSS Variable |
|------|-------|--------------|
| Online/OK | #10b981 (Zelená) | --success-color |
| Offline/Error | #ef4444 (Červená) | --error-color |
| Locked | #f97316 (Oranžová) | #f97316 |
| Warning | #f59e0b (Jantarová) | #f59e0b |
| Accent | #6366f1 (Indigo) | --accent-color |

### Gradienty

```css
/* Usage bar */
background: linear-gradient(135deg, #6366f1, #a855f7);

/* Card accents */
background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(168, 85, 247, 0.1));
```

---

## ⚡ Performance Guidelines

1. **Lazy loading** - komponenty se načítají až při navigaci
2. **Parallel API calls** - všechny summary se načítají současně
3. **Optimistic updates** - UI reaguje okamžitě, API call běží na pozadí
4. **Minimal re-renders** - useCallback + useMemo pro optimalizaci
5. **No heavy libraries** - žádné charting libraries, jen CSS

---

## 📋 Implementační Checklist

- [x] Nová komponenta `StatusOverview.jsx`
- [x] Utility funkce `formatting.js`
- [x] Mobile-first CSS
- [x] Bottom navigation pro mobil
- [x] Rozšířený Device model o `has_lock_rule`, `has_network_block`
- [x] Auto-refresh každých 30s
- [x] Data freshness indikátor
- [ ] Toast notifications pro akce
- [ ] Offline support (PWA)
- [ ] Push notifications

---

## 🔧 API Změny

### DeviceResponse - nová pole

```json
{
  "id": 1,
  "name": "Honzíkův počítač",
  "is_online": true,
  "has_lock_rule": false,
  "has_network_block": false,
  "paired_at": "2025-12-28T18:32:00Z",
  "last_seen": "2025-12-30T10:15:00Z"
}
```

### DeviceSummary - klíčová pole

```json
{
  "device_id": 1,
  "today_usage_seconds": 8100,
  "today_usage_hours": 2.25,
  "paired_at": "2025-12-28T18:32:00Z",
  "last_seen": "2025-12-30T10:15:00Z",
  "top_apps": [
    {"app_name": "Minecraft", "duration_seconds": 2700}
  ]
}
```

---

*Dokument vytvořen: 30.12.2025*
*Verze: 2.0*
