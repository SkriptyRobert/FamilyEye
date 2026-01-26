# Výpočty Úspor - WebSocket vs HTTP Polling
## Detailní analýza pro Windows Agent

**Datum:** 2025-01-27  
**Cíl:** Vysvětlit, jak by WebSocket snížil HTTP requesty a datový přenos

---

## 📊 Aktuální Stav (HTTP Polling)

### Důležité: Rozdíl mezi lokálním a síťovým dotazováním

**LOKÁLNÍ (ne síťové):**
- **Monitor Loop:** Každých 5 sekund - ptá se **Windows API** (lokální, ne síť)
- **Enforcer Loop:** Každých 2 sekundy - kontroluje pravidla **lokálně** (ne síť)

**SÍŤOVÉ (HTTP requesty):**
- **Rule Fetching:** Každých 30 sekund - fetchuje pravidla z **backendu** přes HTTP
- **Usage Reporting:** Každých 60-300 sekund - odesílá data na **backend** přes HTTP

### Počet HTTP Requestů

**Za 1 hodinu:**
- **Rule Fetching:** Každých 30 sekund
  - 3600 sekund / 30 sekund = **120 requestů/hodinu**
  - Endpoint: `POST /api/rules/agent/fetch`
  
- **Usage Reporting:** Každých 60-300 sekund (závisí na konfiguraci)
  - Default: 300 sekund (5 minut) = **12 requestů/hodinu**
  - Nebo: 60 sekund = **60 requestů/hodinu**
  - Endpoint: `POST /api/reports/agent/report`

- **Critical Events:** On-demand (při limit exceeded)
  - ~0-5 requestů/hodinu (závisí na aktivitě)
  - Endpoint: `POST /api/reports/agent/critical-event`

**CELKEM: ~132-185 HTTP requestů/hodinu** (závisí na reporting_interval)

### Velikost Requestů

**Rule Fetch Request:**
```
POST /api/rules/agent/fetch
Headers: ~500 bytes (Content-Type, User-Agent, X-Device-ID, X-API-Key)
Body: ~100 bytes (device_id, api_key)
─────────────────────────────────────
Request: ~600 bytes
```

**Rule Fetch Response:**
```
Status: 200 OK
Headers: ~300 bytes
Body: ~2-5 KB (rules JSON + usage stats)
─────────────────────────────────────
Response: ~2.3-5.3 KB
```

**Usage Report Request:**
```
POST /api/reports/agent/report
Headers: ~500 bytes
Body: ~1-10 KB (usage logs batch)
─────────────────────────────────────
Request: ~1.5-10.5 KB
```

**Usage Report Response:**
```
Status: 200 OK
Headers: ~300 bytes
Body: ~200 bytes (acknowledgment)
─────────────────────────────────────
Response: ~500 bytes
```

### Datový Přenos za 1 Hodinu

**Rule Fetching:**
- Requesty: 120 × 600 bytes = **72 KB**
- Response: 120 × 3 KB (průměr) = **360 KB**
- **Celkem: ~432 KB/hodinu**

**Usage Reporting:**
- Requesty: 12 × 5 KB (průměr) = **60 KB**
- Response: 12 × 500 bytes = **6 KB**
- **Celkem: ~66 KB/hodinu**

**CELKEM: ~498 KB/hodinu** (přibližně 0.5 MB/hodinu)

---

## 🔄 S WebSocket (Teoreticky)

### Počet HTTP Requestů

**Za 1 hodinu:**
- **WebSocket Connection:** 1x trvalé připojení (není HTTP request)
  - Initial handshake: 1x HTTP request (upgrade)
  - Keepalive: 0 HTTP requestů (ping/pong přes WebSocket)
  
- **Rule Updates:** Push přes WebSocket
  - Backend pushuje změny = **0 HTTP requestů**
  - Agent pouze potvrzuje přes WebSocket
  
- **Usage Logs:** Push přes WebSocket (malé batchy)
  - Malé batchy (<20 logů) = **0 HTTP requestů**
  - Velké batchy (>20 logů) = možná 1-2 HTTP requesty/hodinu (fallback)
  
- **Critical Events:** Push přes WebSocket
  - **0 HTTP requestů** (pouze WebSocket message)

**CELKEM: ~1-3 HTTP requestů/hodinu** (pouze initial handshake + případné fallbacky)

### Velikost WebSocket Messages

**WebSocket Overhead:**
- Frame header: ~2-14 bytes (závisí na délce payloadu)
- Masking: 4 bytes (client → server)
- **Celkem overhead: ~6-18 bytes/message**

**Rule Update Message:**
```
WebSocket Frame:
  Header: ~10 bytes
  Payload: ~2-5 KB (rules JSON)
─────────────────────────────────────
Message: ~2-5 KB
```

**Usage Log Message:**
```
WebSocket Frame:
  Header: ~10 bytes
  Payload: ~1-5 KB (usage logs batch)
─────────────────────────────────────
Message: ~1-5 KB
```

**Ping/Pong (Keepalive):**
```
WebSocket Frame:
  Header: ~6 bytes
  Payload: 0 bytes (ping) nebo ~10 bytes (pong)
─────────────────────────────────────
Message: ~6-16 bytes
```

### Datový Přenos za 1 Hodinu (s WebSocket)

**Initial Handshake:**
- HTTP Upgrade: ~1 KB (1x)
- **Celkem: ~1 KB**

**WebSocket Messages:**
- Rule updates: ~10-20 messages × 3 KB = **30-60 KB**
- Usage logs: ~12-15 messages × 3 KB = **36-45 KB**
- Ping/Pong: ~120 messages × 10 bytes = **1.2 KB**
- **Celkem: ~67-106 KB/hodinu**

**CELKEM: ~68-107 KB/hodinu** (přibližně 0.1 MB/hodinu)

---

## 📈 Srovnání a Úspory

### HTTP Requesty

| Typ | HTTP Polling | WebSocket | Úspora |
|-----|--------------|-----------|--------|
| **Rule Fetching** | 120/hodinu | 0/hodinu | **100%** |
| **Usage Reporting** | 12/hodinu | 1-2/hodinu | **83-92%** |
| **Critical Events** | 0-5/hodinu | 0/hodinu | **100%** |
| **Keepalive** | 0 (v HTTP) | 0 (ping/pong) | - |
| **CELKEM** | **132-137/hodinu** | **1-3/hodinu** | **~98%** |

**Vysvětlení:**
- Rule fetching: Místo 120x dotazování "mají se změnit pravidla?" backend pushuje změny = **0 HTTP requestů**
- Usage reporting: Místo 12x HTTP POST se posílá přes WebSocket = **0 HTTP requestů** (pouze fallback pro velké batchy)
- **Výsledek:** 132 requestů → 2 requesty = **98.5% úspora**

### Datový Přenos

| Typ | HTTP Polling | WebSocket | Úspora |
|-----|--------------|-----------|--------|
| **Request Headers** | ~72 KB/hodinu | ~0 KB/hodinu | **100%** |
| **Response Headers** | ~36 KB/hodinu | ~0 KB/hodinu | **100%** |
| **Payload Data** | ~390 KB/hodinu | ~66-96 KB/hodinu | **75-83%** |
| **WebSocket Overhead** | 0 KB/hodinu | ~1-2 KB/hodinu | - |
| **CELKEM** | **~498 KB/hodinu** | **~68-107 KB/hodinu** | **~78-86%** |

**Vysvětlení:**
- **HTTP Headers:** Každý HTTP request má headers (~500 bytes request + ~300 bytes response) = **~800 bytes overhead na request**
  - 132 requestů × 800 bytes = **~105 KB/hodinu jen na headers**
  - WebSocket: Headers jen při initial handshake (~1 KB) = **~104 KB úspora**
  
- **Payload Data:** Podobné (rules JSON, usage logs), ale:
  - HTTP: Každý request musí obsahovat všechna data
  - WebSocket: Push pouze změny (deltas) = **menší payloady**
  
- **WebSocket Overhead:** Frame headers (~6-18 bytes/message) jsou menší než HTTP headers (~800 bytes/request)

**Výsledek:** ~498 KB → ~100 KB = **~80% úspora dat**

---

## 🔍 Detailní Rozbor

### Proč 90%+ úspora HTTP Requestů?

**1. Rule Fetching (120 → 0 requestů)**
```
HTTP Polling:
  Agent: "Mají se změnit pravidla?" (každých 30s)
  Backend: "Ne" nebo "Ano, tady jsou" (i když se nic nezměnilo)
  
WebSocket:
  Backend: Pushuje změny pouze když se něco změní
  Agent: Potvrzuje příjem
  = 0 HTTP requestů (pouze WebSocket messages)
```

**2. Usage Reporting (12 → 1-2 requestů)**
```
HTTP Polling:
  Agent: POST /api/reports/agent/report (každých 5 min)
  Backend: 200 OK
  
WebSocket:
  Agent: Pushuje logy přes WebSocket (malé batchy)
  Backend: Potvrzuje přes WebSocket
  = 0 HTTP requestů (pouze WebSocket messages)
  Fallback: Velké batchy (>20 logů) → HTTP (1-2x/hodinu)
```

**3. Critical Events (0-5 → 0 requestů)**
```
HTTP Polling:
  Agent: POST /api/reports/agent/critical-event (on-demand)
  
WebSocket:
  Agent: Pushuje přes WebSocket
  = 0 HTTP requestů
```

### Proč 80% úspora Datového Přenosu?

**1. HTTP Headers Overhead**
```
Každý HTTP request:
  Request headers: ~500 bytes
  Response headers: ~300 bytes
  ────────────────────────────
  Celkem: ~800 bytes overhead
  
132 requestů × 800 bytes = 105.6 KB/hodinu jen na headers!
```

**2. WebSocket Overhead**
```
WebSocket frame:
  Frame header: ~6-18 bytes (závisí na délce)
  Masking: 4 bytes (client → server)
  ────────────────────────────
  Celkem: ~10-22 bytes overhead
  
~30 messages × 15 bytes = 0.45 KB/hodinu na overhead
```

**3. Delta Updates (místo full payload)**
```
HTTP Polling:
  Rule fetch: Vždy posílá všechna pravidla (i když se nic nezměnilo)
  = 2-5 KB každých 30s
  
WebSocket:
  Rule update: Pushuje pouze změny (delta)
  = 0.5-2 KB pouze když se něco změní
  = Úspora 50-80% na payload
```

---

## 📊 Reálné Příklady

### Scénář 1: Normální Použití (1 hodina)

**HTTP Polling:**
- Rule fetching: 120 requestů × 3.6 KB = **432 KB**
- Usage reporting: 12 requestů × 5.5 KB = **66 KB**
- **Celkem: 498 KB**

**WebSocket:**
- Initial handshake: 1 KB
- Rule updates: 2 změny × 3 KB = **6 KB**
- Usage logs: 12 messages × 3 KB = **36 KB**
- Ping/Pong: 120 × 10 bytes = **1.2 KB**
- **Celkem: ~44 KB**

**Úspora: 498 KB → 44 KB = 91% úspora**

### Scénář 2: Aktivní Použití (1 hodina, více změn)

**HTTP Polling:**
- Rule fetching: 120 requestů × 3.6 KB = **432 KB**
- Usage reporting: 12 requestů × 8 KB = **96 KB**
- Critical events: 3 requesty × 1 KB = **3 KB**
- **Celkem: 531 KB**

**WebSocket:**
- Initial handshake: 1 KB
- Rule updates: 5 změn × 3 KB = **15 KB**
- Usage logs: 15 messages × 4 KB = **60 KB**
- Critical events: 3 messages × 1 KB = **3 KB**
- Ping/Pong: 120 × 10 bytes = **1.2 KB**
- **Celkem: ~80 KB**

**Úspora: 531 KB → 80 KB = 85% úspora**

---

## ⚠️ Důležité Poznámky

### 1. WebSocket má také overhead

**Keepalive:**
- Ping/Pong každých 30s = 120 messages/hodinu
- Každý ping/pong: ~10-16 bytes
- **Celkem: ~1.2 KB/hodinu** (ale stále méně než HTTP headers)

**Frame Headers:**
- Každá WebSocket message má frame header (~6-18 bytes)
- ~30 messages/hodinu × 15 bytes = **0.45 KB/hodinu**
- **Stále mnohem méně než HTTP headers (105 KB/hodinu)**

### 2. Úspora závisí na aktivitě

**Nízká aktivita (málo změn):**
- HTTP: Stále 120 rule fetches (i když se nic nezměnilo)
- WebSocket: Pouze 1-2 rule updates (když se něco změní)
- **Úspora: ~95%**

**Vysoká aktivita (hodně změn):**
- HTTP: 120 rule fetches + více usage reports
- WebSocket: Více rule updates + více usage messages
- **Úspora: ~75-85%** (stále významná)

### 3. Pro domácí nasazení není kritické

**Aktuální spotřeba (HTTP Polling):**
- 132 requestů/hodinu = **2.2 requesty/minutu**
- 498 KB/hodinu = **8.3 KB/minutu**
- **Hodnocení:** ✅ Velmi nízká zátěž

**S WebSocket:**
- 2 requesty/hodinu = **0.03 requesty/minutu**
- 100 KB/hodinu = **1.7 KB/minutu**
- **Úspora:** Ano, ale pro 2-4 zařízení není rozdíl kritický

---

## 🎯 Závěr

### Úspora HTTP Requestů: ~98%

**Výpočet:**
- Aktuálně: 132 HTTP requestů/hodinu
- S WebSocket: 2 HTTP requesty/hodinu (initial handshake + fallback)
- **Úspora: 130 requestů = 98.5%**

**Jak?**
- Rule fetching: 120 → 0 (push místo polling)
- Usage reporting: 12 → 1-2 (push místo POST, fallback pro velké batchy)
- Critical events: 0-5 → 0 (push místo POST)

### Úspora Datového Přenosu: ~80%

**Výpočet:**
- Aktuálně: ~498 KB/hodinu
- S WebSocket: ~100 KB/hodinu
- **Úspora: ~398 KB = 80%**

**Jak?**
- HTTP headers: ~105 KB/hodinu → ~1 KB (initial handshake) = **104 KB úspora**
- Payload: ~390 KB → ~96 KB (delta updates) = **294 KB úspora**
- WebSocket overhead: ~2 KB (ping/pong + frame headers)
- **Celkem: ~398 KB úspora**

### Pro domácí nasazení

**Aktuální spotřeba je nízká:**
- 132-185 requestů/hodinu = není problém
- 498 KB/hodinu = není problém
- **WebSocket by přinesl úsporu, ale není nutné**

**⚠️ DŮLEŽITÉ: HTTP Polling vs WebSocket - Firewall**

**HTTP Polling (aktuální):**
- ✅ Funguje přes všechny firewally (standardní HTTP/HTTPS porty)
- ✅ Funguje přes proxy servery
- ✅ Jednoduché pro "no geek" uživatele (žádná konfigurace FW)
- ✅ Offline-first: Agent funguje i bez připojení, data se synchronizují při reconnect
- ⚠️ Mírně vyšší spotřeba (ale pro 2-4 zařízení zanedbatelné)

**WebSocket:**
- ⚠️ Může mít problémy s firewally (některé FW blokují WebSocket upgrade)
- ⚠️ Může mít problémy s proxy servery (některé proxy nepodporují WebSocket)
- ⚠️ Vyžaduje konfiguraci firewallu (otevření WebSocket portu)
- ⚠️ Pro "no geek" uživatele může být problém (nutnost konfigurace)
- ✅ Nižší spotřeba (ale pro domácí nasazení není kritické)

**Závěr pro domácí nasazení:**
- **HTTP Polling je lepší volba** pro jednoduchost a spolehlivost
- WebSocket by přinesl úsporu, ale přidá složitost (firewall konfigurace)
- Pro 2-4 zařízení není rozdíl v spotřebě kritický

**Kdy by WebSocket dával smysl:**
- 10+ zařízení (snížení server load)
- Notebooky s baterií (méně wake-ups = úspora baterie)
- Potřeba real-time příkazů (<1s latence)
- Techničtí uživatelé, kteří si umí nakonfigurovat firewall

---

**Autor výpočtů:** AI Assistant  
**Kontakt:** robert.pesout@gmail.com
