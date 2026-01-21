# Agent Loopy a Komunikace - Detailní Vysvětlení

**Datum:** 2025-01-27  
**Cíl:** Vysvětlit rozdíl mezi lokálním dotazováním (systém) a síťovým dotazováním (backend)

---

## 🔍 Jak Agent Funguje - Tři Hlavní Loopy

### 1. Monitor Loop (Lokální - Není Síťové)

**Interval:** 5 sekund (default `monitor_interval`)  
**Co dělá:** Ptá se **Windows API** (lokální systém)

```python
# main.py - _monitor_loop()
while self.running:
    self.monitor.update()  # Ptá se Windows API (lokální)
    time.sleep(5)  # Default: monitor_interval
```

**Co se děje:**
- Zjišťuje běžící procesy (psutil)
- Zjišťuje aktivní okna (Windows API)
- Počítá čas použití aplikací (lokální)
- **NENÍ to síťové dotazování!**

**Příklad:**
```
Agent → Windows API: "Jaké procesy běží?"
Windows API → Agent: "chrome.exe, steam.exe, discord.exe"
Agent → Windows API: "Jaké okno je aktivní?"
Windows API → Agent: "Chrome - YouTube"
```

---

### 2. Enforcer Loop (Lokální - Není Síťové)

**Interval:** 2 sekundy (hardcoded)  
**Co dělá:** Kontroluje a vynucuje pravidla **lokálně**

```python
# main.py - _enforcer_loop()
while self.running:
    self.enforcer.update()  # Kontroluje pravidla lokálně
    time.sleep(2)  # Hardcoded
```

**Co se děje:**
- Kontroluje, jestli běžící aplikace nejsou blokované
- Kontroluje, jestli nejsou překročené limity času
- Vynucuje pravidla (zabíjí procesy, blokuje síť)
- **NENÍ to síťové dotazování!**

**Příklad:**
```
Agent (lokálně): "Je chrome.exe v seznamu blokovaných?"
Agent (lokálně): "Ano → zabít proces"
Agent (lokálně): "Je čas použití steam.exe > limit?"
Agent (lokálně): "Ano → zabít proces"
```

**⚠️ DŮLEŽITÉ:** Enforcer také fetchuje pravidla z backendu, ale to je **samostatná operace** (viz níže)

---

### 3. Reporter Loop (Síťové - HTTP Requesty)

**Interval:** 60-300 sekund (default `reporting_interval` = 300)  
**Co dělá:** Odesílá data na **backend** přes HTTP

```python
# main.py - _reporter_loop()
while self.running:
    self.reporter.send_reports()  # Odesílá na backend přes HTTP
    time.sleep(300)  # Default: reporting_interval
```

**Co se děje:**
- Shromáždí usage data z monitoru
- Odesílá batch na backend přes HTTP POST
- Backend odpovídá s příkazy (např. "TAKE_SCREENSHOT")
- **TO JE síťové dotazování!**

**Příklad:**
```
Agent → Backend (HTTP POST): "Tady jsou usage logy"
Backend → Agent (HTTP Response): "OK, tady jsou příkazy: TAKE_SCREENSHOT"
```

---

## 🔄 Rule Fetching (Síťové - HTTP Requesty)

**Interval:** 30 sekund (default `polling_interval`)  
**Kde:** V `enforcer.update()` (ale je to síťové!)

```python
# enforcer.py - update()
polling_interval = config.get("polling_interval", 30)  # Default: 30s

if current_time - self._last_fetch_rules_time >= polling_interval:
    self._fetch_rules()  # HTTP POST na backend
```

**Co se děje:**
- Agent se ptá backendu: "Mají se změnit pravidla?"
- Backend odpovídá: "Ano, tady jsou nová pravidla" nebo "Ne, žádné změny"
- **TO JE síťové dotazování!**

**Příklad:**
```
Agent → Backend (HTTP POST): "Mají se změnit pravidla?"
Backend → Agent (HTTP Response): "Ano, tady jsou nová pravidla + usage stats"
Agent: Aktualizuje lokální cache pravidel
```

---

## 📊 Souhrn: Co je Lokální vs. Síťové

| Loop/Operace | Interval | Typ | Co dělá |
|--------------|----------|-----|---------|
| **Monitor Loop** | 5s | **LOKÁLNÍ** | Ptá se Windows API (procesy, okna) |
| **Enforcer Loop** | 2s | **LOKÁLNÍ** | Kontroluje pravidla lokálně |
| **Rule Fetching** | 30s | **SÍŤOVÉ** | Fetchuje pravidla z backendu (HTTP) |
| **Reporter Loop** | 60-300s | **SÍŤOVÉ** | Odesílá data na backend (HTTP) |

---

## 🎯 Odpověď na Tvoji Otázku

> "Agent dělá pooling a ptá se systému každé 2s a pak data odesle co 30s"

**Přesněji:**
1. **Agent se ptá SYSTÉMU (Windows API) každých 5s** - to je lokální, ne síťové
2. **Agent kontroluje pravidla LOKÁLNĚ každých 2s** - to je také lokální, ne síťové
3. **Agent fetchuje pravidla z BACKENDU každých 30s** - to je síťové (HTTP)
4. **Agent odesílá data na BACKEND každých 60-300s** - to je síťové (HTTP)

**Takže:**
- **Lokální dotazování (systém):** 5s (monitor) + 2s (enforcer) = velmi rychlé, ale není síťové
- **Síťové dotazování (backend):** 30s (rules) + 60-300s (reports) = HTTP requesty

---

## 🔥 WebSocket vs. HTTP Polling - Firewall

### Tvoje Pozorování: "WebSocket = problémy s FW, HTTP polling to nemá"

**✅ MÁŠ PRAVDU!**

### HTTP Polling (Aktuální)

**Výhody:**
- ✅ Funguje přes všechny firewally (standardní HTTP/HTTPS porty 80/443)
- ✅ Funguje přes proxy servery
- ✅ Jednoduché pro "no geek" uživatele (žádná konfigurace FW)
- ✅ Offline-first: Agent funguje i bez připojení, data se synchronizují při reconnect
- ✅ Spolehlivé (HTTP je všude podporováno)

**Nevýhody:**
- ⚠️ Mírně vyšší spotřeba (ale pro 2-4 zařízení zanedbatelné)
- ⚠️ Mírně vyšší latence (30s polling vs. real-time push)

### WebSocket

**Výhody:**
- ✅ Nižší spotřeba (méně HTTP requestů)
- ✅ Real-time push (nižší latence)
- ✅ Efektivnější pro malé payloady

**Nevýhody:**
- ⚠️ **Může mít problémy s firewally** (některé FW blokují WebSocket upgrade)
- ⚠️ **Může mít problémy s proxy servery** (některé proxy nepodporují WebSocket)
- ⚠️ **Vyžaduje konfiguraci firewallu** (otevření WebSocket portu)
- ⚠️ **Pro "no geek" uživatele může být problém** (nutnost konfigurace)
- ⚠️ Složitější implementace (reconnect logic, error handling)

---

## 💡 Závěr

### Pro domácí nasazení (2-4 zařízení):

**HTTP Polling je lepší volba:**
- ✅ Jednoduchost (žádná konfigurace FW)
- ✅ Spolehlivost (funguje všude)
- ✅ Offline-first (agent funguje i bez připojení)
- ✅ Spotřeba je nízká (132-185 requestů/hodinu = není problém)

**WebSocket by přinesl:**
- ✅ Úsporu (ale pro 2-4 zařízení není kritické)
- ⚠️ Složitost (konfigurace FW)
- ⚠️ Potenciální problémy (FW, proxy)

### Kdy by WebSocket dával smysl:

- 10+ zařízení (snížení server load)
- Notebooky s baterií (méně wake-ups = úspora baterie)
- Potřeba real-time příkazů (<1s latence)
- Techničtí uživatelé, kteří si umí nakonfigurovat firewall

---

**Autor:** AI Assistant  
**Kontakt:** robert.pesout@gmail.com
