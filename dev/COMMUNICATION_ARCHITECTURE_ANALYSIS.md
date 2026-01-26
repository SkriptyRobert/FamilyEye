# Analýza Architektury Komunikace: Pooling + WebSocket

## Aktuální Stav

### HTTP Polling (Reporter.kt)
- **Interval:** 30 sekund (`SYNC_INTERVAL_MS`)
- **Účel:**
  - Odesílání usage logs (batch)
  - Heartbeat (i když žádné logy)
  - Server time sync
  - Keywords sync
- **Vlastnosti:**
  - Exponential backoff při chybách
  - Network-aware (auto-sync při reconnect)
  - Data Saver mode (pouze Wi-Fi)
  - Batch processing (max 100 logů)

### WebSocket (WebSocketClient.kt)
- **Typ:** Trvalé připojení s auto-reconnect
- **Retry:** 5 sekund (`WEBSOCKET_RETRY_INTERVAL_MS`)
- **Účel:**
  - Příjem příkazů z backendu:
    - `LOCK_NOW` / `UNLOCK_NOW`
    - `REFRESH_RULES`
    - `SCREENSHOT_NOW`
    - `RESET_PIN:xxx`
  - Ping/Pong heartbeat
- **Vlastnosti:**
  - API key v HTTP headeru (bezpečnější)
  - Auto-reconnect při ztrátě spojení

### Rule Fetching (FamilyEyeService.kt)
- **Interval:** 30 sekund (hardcoded)
- **Účel:** Stahování pravidel z backendu
- **Duplicita:** Také trigger přes WebSocket (`REFRESH_RULES`)

---

## Problémy Aktuální Architektury

### 🔴 Kritické Problémy

1. **Duplicitní HTTP Requesty**
   - Reporter: 30s interval
   - Rule Fetching: 30s interval
   - **Výsledek:** 2x HTTP request každých 30s (i když žádné změny)
   - **Dopad:** Zbytečná spotřeba baterie, dat, server resources

2. **Inefektivní Heartbeat**
   - HTTP heartbeat každých 30s (Reporter)
   - WebSocket ping/pong (pouze při připojení)
   - **Problém:** Dva nezávislé heartbeat mechanismy

3. **WebSocket Podvyužitý**
   - WebSocket je připojen, ale používá se jen pro příkazy
   - Usage logs se posílají přes HTTP (i když WebSocket funguje)
   - **Ztráta:** WebSocket může přenášet data efektivněji

### 🟡 Střední Problémy

4. **Nekonzistentní Intervaly**
   - Usage tracking: 5s
   - Sync: 30s
   - Rule fetch: 30s
   - WebSocket retry: 5s
   - **Problém:** Různé intervaly = složitější debugging

5. **Chybějící Priorizace**
   - Všechny requesty mají stejnou prioritu
   - **Chybí:** Urgent vs. Normal vs. Background

6. **Žádný Offline Queue**
   - Při ztrátě sítě se logy hromadí v DB
   - **Problém:** Při reconnect se posílá velký batch najednou

---

## Best Practices pro Mobile + Backend Komunikaci

### ✅ Doporučená Architektura: **Hybrid WebSocket + HTTP**

#### 1. **WebSocket jako Primární Kanál**
```
┌─────────────────────────────────────┐
│  WebSocket (Trvalé připojení)       │
├─────────────────────────────────────┤
│  ✓ Real-time příkazy (LOCK, etc.)   │
│  ✓ Usage logs (malé batchy)        │
│  ✓ Heartbeat (ping/pong)            │
│  ✓ Rule updates (push)              │
│  ✓ Status updates                   │
└─────────────────────────────────────┘
```

**Výhody:**
- Nižší latence (real-time)
- Nižší overhead (1x connection vs. Nx HTTP)
- Server může pushovat změny
- Efektivnější pro malé payloady

#### 2. **HTTP jako Fallback/Backup**
```
┌─────────────────────────────────────┐
│  HTTP REST (On-demand)              │
├─────────────────────────────────────┤
│  ✓ Velké batchy (fallback)          │
│  ✓ Screenshot upload (multipart)    │
│  ✓ Initial pairing                  │
│  ✓ WebSocket reconnect fallback     │
└─────────────────────────────────────┘
```

**Výhody:**
- Spolehlivější pro velké soubory
- Jednodušší error handling
- Lepší pro retry logiku

#### 3. **Adaptivní Strategie**
```
IF WebSocket connected:
    → Použij WebSocket pro vše
ELSE:
    → Fallback na HTTP polling
    → Pokus o WebSocket reconnect každých 10s
```

---

## Optimalizovaná Architektura

### Fáze 1: Unifikace Heartbeat

**Aktuálně:**
- HTTP heartbeat každých 30s (Reporter)
- WebSocket ping každých Xs (nekonzistentní)

**Optimalizace:**
```kotlin
// WebSocket heartbeat každých 30s
// HTTP heartbeat pouze pokud WebSocket není připojen
if (webSocketClient.isConnected) {
    // Heartbeat přes WebSocket
    webSocketClient.sendHeartbeat()
} else {
    // Fallback HTTP heartbeat
    reporter.sendHeartbeat()
}
```

**Úspora:** ~50% HTTP requestů

### Fáze 2: Usage Logs přes WebSocket

**Aktuálně:**
- Usage logs → HTTP POST každých 30s

**Optimalizace:**
```kotlin
// Posílej logy přes WebSocket (malé batchy)
if (webSocketClient.isConnected && unsyncedLogs.size < 20) {
    webSocketClient.sendUsageLogs(unsyncedLogs)
} else {
    // Velké batchy nebo fallback → HTTP
    reporter.syncLogs(unsyncedLogs)
}
```

**Úspora:** ~70% HTTP requestů (pokud WebSocket funguje)

### Fáze 3: Rule Updates přes WebSocket Push

**Aktuálně:**
- Rule fetching každých 30s (HTTP GET)
- WebSocket může triggerovat refresh

**Optimalizace:**
```kotlin
// Backend pushuje rule updates přes WebSocket
// Agent pouze potvrdí příjem
// HTTP fetch pouze při:
//   - Initial load
//   - WebSocket disconnect
//   - Explicit refresh request
```

**Úspora:** ~95% HTTP requestů pro rules

### Fáze 4: Smart Batching

**Aktuálně:**
- Fixed interval (30s)
- Batch size limit (100)

**Optimalizace:**
```kotlin
// Adaptivní interval podle:
//   - Počtu unsynced logů
//   - Network quality
//   - Battery level
//   - Data Saver mode

val interval = when {
    unsyncedLogs.size > 50 -> 10_000L  // Urgent: 10s
    unsyncedLogs.size > 20 -> 20_000L  // Normal: 20s
    batteryLevel < 20 -> 60_000L       // Battery save: 60s
    else -> 30_000L                     // Default: 30s
}
```

---

## Srovnání: Aktuální vs. Optimalizovaná

| Metrika | Aktuální | Optimalizovaná | Úspora |
|---------|----------|----------------|--------|
| **HTTP Requesty/min** | 4 (2x sync + 2x rules) | 0.5 (fallback) | **87.5%** |
| **WebSocket Messages/min** | ~2 (ping) | ~10 (data + ping) | - |
| **Latence příkazů** | 0-30s (polling) | <1s (push) | **30x rychlejší** |
| **Baterie** | Střední | Nízká | **~30% úspora** |
| **Data přenos** | Střední | Nízký | **~40% úspora** |
| **Server load** | Vysoký | Nízký | **~60% úspora** |

---

## Implementační Plán

### Priorita 1: Unifikace Heartbeat (1-2 dny)
1. Přesunout heartbeat na WebSocket
2. HTTP heartbeat pouze jako fallback
3. **Výsledek:** -50% HTTP requestů

### Priorita 2: Usage Logs přes WebSocket (2-3 dny)
1. Implementovat WebSocket message pro usage logs
2. Batch logy přes WebSocket (<20 logů)
3. Velké batchy přes HTTP
4. **Výsledek:** -70% HTTP requestů

### Priorita 3: Rule Push (3-4 dny)
1. Backend pushuje rule updates
2. Agent pouze potvrdí
3. HTTP fetch pouze při reconnect
4. **Výsledek:** -95% HTTP requestů pro rules

### Priorita 4: Smart Batching (1-2 dny)
1. Adaptivní intervaly
2. Battery-aware sync
3. Network-aware sync
4. **Výsledek:** -30% baterie, -40% dat

---

## Alternativní Architektury

### Varianta A: Server-Sent Events (SSE)
**Pro:** Jednosměrná komunikace (server → client)
**Proti:** Android nepodporuje nativně, potřebuje polyfill
**Závěr:** ❌ Ne pro Android

### Varianta B: Long Polling
**Pro:** Funguje všude, jednoduché
**Proti:** Vysoká latence, více requestů než WebSocket
**Závěr:** ⚠️ Pouze jako fallback

### Varianta C: MQTT
**Pro:** Velmi efektivní, low overhead
**Proti:** Potřebuje další server (broker), složitější setup
**Závěr:** ⚠️ Overkill pro tento use case

### Varianta D: gRPC Stream
**Pro:** Velmi efektivní, type-safe
**Proti:** Složitější implementace, větší binary size
**Závěr:** ⚠️ Možná v budoucnu, teď overkill

---

## Závěr a Doporučení

### ✅ Váš Přístup je **SPRÁVNÝ**, ale **NEOPTIMALIZOVANÝ**

**Co je dobře:**
- ✅ Kombinace WebSocket + HTTP (správný hybrid)
- ✅ Exponential backoff
- ✅ Network-aware sync
- ✅ Data Saver mode

**Co chybí:**
- ❌ WebSocket je podvyužitý (pouze příkazy)
- ❌ Duplicitní heartbeat (HTTP + WebSocket)
- ❌ Duplicitní rule fetching (HTTP + WebSocket trigger)
- ❌ Žádná adaptivní strategie

### 🎯 Doporučení

**Krátkodobě (1-2 týdny):**
1. Přesunout heartbeat na WebSocket
2. Posílat usage logs přes WebSocket (malé batchy)
3. Odstranit duplicitní rule fetching

**Střednědobě (1 měsíc):**
4. Implementovat rule push přes WebSocket
5. Smart batching s adaptivními intervaly
6. Offline queue s prioritizací

**Dlouhodobě (3+ měsíce):**
7. Zvážit MQTT pro velmi velké deploymenty
8. Implementovat QoS levels (Urgent/Normal/Background)
9. Analytics a monitoring komunikace

### 📊 Očekávané Výsledky

Po implementaci všech fází:
- **-87% HTTP requestů** (4/min → 0.5/min)
- **-30% spotřeba baterie**
- **-40% datový přenos**
- **30x rychlejší latence** příkazů (<1s vs. 0-30s)
- **-60% server load**

---

## Shrnutí

**Váš přístup pooling + WebSocket je správný**, ale potřebuje optimalizaci:

1. ✅ **WebSocket jako primární kanál** (ne jen pro příkazy)
2. ✅ **HTTP jako fallback** (pro velké batchy, reconnect)
3. ✅ **Unifikace heartbeat** (pouze WebSocket, HTTP jako backup)
4. ✅ **Smart batching** (adaptivní intervaly)

**Toto je industry best practice** pro mobile apps s real-time komunikací. Vaše architektura má správný základ, jen potřebuje využít WebSocket naplno.
