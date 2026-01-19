# Analýza Robustnosti WebSocket: Výpadky, Firewall, NAT

## Aktuální Stav - Identifikované Problémy

### 🔴 Kritické Problémy

#### 1. **Jednoduchá Reconnect Logika**
```kotlin
// Aktuálně: Fixed interval 5s, žádný backoff
delay(AgentConstants.WEBSOCKET_RETRY_INTERVAL_MS) // 5s vždy
```

**Problémy:**
- ❌ Žádný exponential backoff
- ❌ Retry i když není síť (zbytečná spotřeba baterie)
- ❌ Žádná detekce "zombie" spojení (otevřené, ale nefunkční)
- ❌ Nekonečné retry (i při trvalém výpadku)

#### 2. **Chybějící Network Awareness**
```kotlin
// WebSocket NEPOUŽÍVÁ NetworkCallback (Reporter ano)
// WebSocket retry i když není síť!
```

**Problémy:**
- ❌ WebSocket se pokouší reconnect i bez sítě
- ❌ Žádná detekce Wi-Fi vs. Mobile data
- ❌ Ignoruje Data Saver mode

#### 3. **Žádná Detekce "Zombie" Spojení**
```kotlin
// Aktuálně: Pokud je webSocket != null, považuje se za připojený
// Ale spojení může být "mrtvé" (FW timeout, NAT timeout)
```

**Problémy:**
- ❌ Spojení vypadá jako připojené, ale data neprocházejí
- ❌ Žádný heartbeat timeout detection
- ❌ Žádná detekce TCP keepalive failure

#### 4. **Chybějící Offline Queue**
```kotlin
// Data se ukládají do DB, ale:
// - Žádná priorizace (urgent vs. normal)
// - Žádný batch limit při reconnect
// - Všechno se pošle najednou = možný timeout
```

#### 5. **Backend Timeout Handling**
```python
# Backend: Žádný explicit timeout
while True:
    data = await websocket.receive_text()  # Může čekat nekonečně
```

**Problémy:**
- ❌ Backend neví, kdy je spojení "mrtvé"
- ❌ Žádný cleanup "zombie" spojení
- ❌ Memory leak při neukončených spojeních

#### 6. **Firewall/NAT Problémy**
```
Firewall/NAT může:
- Blokovat WebSocket úplně
- Timeout idle spojení (30-60s)
- Blokovat WSS (port 443) ale ne HTTP
- Proxy může přerušit long-lived spojení
```

**Aktuálně:** ❌ Žádné řešení

---

## Scénáře Selhání

### Scénář 1: Krátkodobý Výpadek Sítě (5-30s)
```
1. WebSocket ztratí spojení
2. Retry každých 5s
3. Po reconnect: ✅ Funguje
```
**Status:** ✅ Funguje (ale neoptimálně - zbytečné retry)

### Scénář 2: Dlouhodobý Výpadek (5+ minut)
```
1. WebSocket ztratí spojení
2. Retry každých 5s (nekonečně)
3. Baterie se vybíjí
4. Po reconnect: ✅ Funguje, ale zbytečná spotřeba
```
**Status:** ⚠️ Funguje, ale plýtvá baterií

### Scénář 3: Firewall Timeout (30-60s idle)
```
1. WebSocket je "připojený" (TCP OK)
2. Ale data neprocházejí (FW timeout)
3. Agent si myslí, že je online
4. Příkazy se ztrácejí
5. Data se neposílají
```
**Status:** 🔴 **KRITICKÉ** - Agent si myslí, že je online, ale není!

### Scénář 4: NAT Timeout (2-5 minut)
```
1. WebSocket funguje
2. NAT timeout (žádný traffic)
3. Spojení se "rozbije" (ale TCP neví)
4. Agent si myslí, že je online
5. Backend si myslí, že je online
6. Ale komunikace nefunguje
```
**Status:** 🔴 **KRITICKÉ** - Stejný problém jako FW timeout

### Scénář 5: Firewall Blokuje WebSocket Úplně
```
1. WebSocket se nikdy nepřipojí
2. Retry každých 5s (nekonečně)
3. HTTP fallback funguje, ale WebSocket ne
4. Agent by měl použít HTTP, ale neví o problému
```
**Status:** ⚠️ Funguje přes HTTP, ale WebSocket retry plýtvá baterií

### Scénář 6: Proxy Přeruší Spojení
```
1. WebSocket funguje
2. Proxy timeout (corporate proxy)
3. Spojení se "rozbije"
4. Agent neví, že je problém
5. Data se ztrácejí
```
**Status:** 🔴 **KRITICKÉ** - Stejný problém jako FW/NAT timeout

---

## Robustní Řešení

### Fáze 1: Network-Aware Reconnect

```kotlin
class WebSocketClient {
    private val connectivityManager: ConnectivityManager
    private var networkCallback: ConnectivityManager.NetworkCallback? = null
    private var consecutiveFailures = 0
    private var lastSuccessfulPong = 0L
    
    fun start() {
        registerNetworkCallback()
        connectLoop()
    }
    
    private fun registerNetworkCallback() {
        val request = NetworkRequest.Builder()
            .addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
            .build()
            
        networkCallback = object : ConnectivityManager.NetworkCallback() {
            override fun onAvailable(network: Network) {
                Timber.i("Network available - reconnecting WebSocket")
                consecutiveFailures = 0
                reconnect()
            }
            
            override fun onLost(network: Network) {
                Timber.i("Network lost - closing WebSocket")
                webSocket?.close(1000, "Network lost")
                _isConnected.value = false
            }
        }
        
        connectivityManager.registerNetworkCallback(request, networkCallback!!)
    }
    
    private suspend fun connectLoop() {
        while (isRunning) {
            // POKUD NENÍ SÍŤ → NERETRY!
            if (!isNetworkAvailable()) {
                delay(10_000L) // Check každých 10s
                continue
            }
            
            if (webSocket == null && configRepository.isPaired.first()) {
                connect(...)
            }
            
            // Exponential backoff
            val backoff = calculateBackoff()
            delay(backoff)
        }
    }
    
    private fun calculateBackoff(): Long {
        val base = 5_000L // 5s
        val max = 5 * 60 * 1000L // 5 minut max
        val backoff = base * (1L shl minOf(consecutiveFailures, 6))
        return minOf(backoff, max)
    }
}
```

**Výhody:**
- ✅ Retry pouze když je síť
- ✅ Exponential backoff (neplýtvá baterií)
- ✅ Auto-reconnect při reconnect sítě

### Fáze 2: Heartbeat Timeout Detection

```kotlin
class WebSocketClient {
    private var lastPongTime = 0L
    private val HEARTBEAT_INTERVAL = 30_000L // 30s
    private val HEARTBEAT_TIMEOUT = 90_000L // 90s (3x interval)
    
    private fun startHeartbeat() {
        scope.launch {
            while (isRunning && webSocket != null) {
                // Poslat ping
                webSocket?.send("{\"type\":\"ping\"}")
                
                // Zkontrolovat timeout
                val timeSinceLastPong = System.currentTimeMillis() - lastPongTime
                if (timeSinceLastPong > HEARTBEAT_TIMEOUT) {
                    Timber.w("Heartbeat timeout - reconnecting")
                    webSocket?.close(1001, "Heartbeat timeout")
                    webSocket = null
                    _isConnected.value = false
                }
                
                delay(HEARTBEAT_INTERVAL)
            }
        }
    }
    
    override fun onMessage(webSocket: WebSocket, text: String) {
        val msg = parseMessage(text)
        if (msg.type == "pong") {
            lastPongTime = System.currentTimeMillis()
        }
        // ... handle other messages
    }
}
```

**Výhody:**
- ✅ Detekce "zombie" spojení
- ✅ Auto-reconnect při timeout
- ✅ Spolehlivá detekce problémů

### Fáze 3: Offline Queue s Priorizací

```kotlin
class OfflineQueue {
    data class QueuedMessage(
        val type: MessageType,
        val data: Any,
        val priority: Priority,
        val timestamp: Long,
        val retryCount: Int = 0
    )
    
    enum class Priority {
        URGENT,    // LOCK_NOW, UNLOCK_NOW
        HIGH,      // Usage logs (recent)
        NORMAL,    // Usage logs (old)
        LOW        // Keywords sync
    }
    
    private val queue = PriorityQueue<QueuedMessage> { a, b ->
        when {
            a.priority != b.priority -> a.priority.ordinal - b.priority.ordinal
            else -> a.timestamp.compareTo(b.timestamp)
        }
    }
    
    fun enqueue(message: QueuedMessage) {
        queue.offer(message)
        // Limit queue size (prevent memory leak)
        if (queue.size > MAX_QUEUE_SIZE) {
            queue.poll() // Remove oldest LOW priority
        }
    }
    
    suspend fun flush(webSocket: WebSocket?, maxBatch: Int = 20) {
        val batch = mutableListOf<QueuedMessage>()
        repeat(maxBatch) {
            queue.poll()?.let { batch.add(it) }
        }
        
        batch.forEach { msg ->
            try {
                if (webSocket != null && webSocket.isConnected) {
                    sendViaWebSocket(msg)
                } else {
                    sendViaHTTP(msg) // Fallback
                }
            } catch (e: Exception) {
                // Retry later
                msg.retryCount++
                if (msg.retryCount < MAX_RETRIES) {
                    queue.offer(msg)
                }
            }
        }
    }
}
```

**Výhody:**
- ✅ Priorizace důležitých zpráv
- ✅ Batch limit (prevence timeout)
- ✅ Retry logika
- ✅ Memory leak prevention

### Fáze 4: Backend Timeout & Cleanup

```python
@router.websocket("/ws/device/{device_id}")
async def websocket_device_endpoint(websocket: WebSocket, device_id: str, ...):
    await manager.connect_device(websocket, device_id)
    
    try:
        # Timeout pro receive (detekce "zombie" spojení)
        while True:
            try:
                # Wait max 60s for message
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=60.0
                )
                # Handle message
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                # No message in 60s - send ping to check if alive
                try:
                    await websocket.send_json({"type": "ping_check"})
                except:
                    # Connection is dead
                    raise WebSocketDisconnect
                    
    except WebSocketDisconnect:
        manager.disconnect_device(device_id)
    except Exception as e:
        logger.error(f"WS Error: {e}")
        manager.disconnect_device(device_id)
```

**Výhody:**
- ✅ Detekce "zombie" spojení na backendu
- ✅ Auto-cleanup mrtvých spojení
- ✅ Memory leak prevention

### Fáze 5: Firewall/NAT Workaround

```kotlin
class WebSocketClient {
    // Strategy 1: Keep-alive ping každých 20s (méně než FW timeout)
    private val KEEPALIVE_INTERVAL = 20_000L // 20s
    
    // Strategy 2: Fallback na HTTP pokud WebSocket selže 3x
    private var wsFailureCount = 0
    private val MAX_WS_FAILURES = 3
    
    private suspend fun connectWithFallback() {
        if (wsFailureCount >= MAX_WS_FAILURES) {
            Timber.w("WebSocket failed multiple times - using HTTP fallback")
            useHttpMode = true
            return
        }
        
        try {
            connect(...)
            wsFailureCount = 0 // Reset on success
        } catch (e: Exception) {
            wsFailureCount++
            // Retry with backoff
        }
    }
    
    // Strategy 3: WebSocket upgrade s explicit keepalive
    private fun createWebSocketRequest(): Request {
        return Request.Builder()
            .url(wsUrl)
            .addHeader("X-API-Key", apiKey)
            .addHeader("Connection", "Upgrade")
            .addHeader("Upgrade", "websocket")
            // Explicit keepalive hint
            .addHeader("Keep-Alive", "timeout=60")
            .build()
    }
}
```

**Výhody:**
- ✅ Workaround pro FW timeout (keepalive)
- ✅ Auto-fallback na HTTP
- ✅ Explicit keepalive headers

---

## Kompletní Robustní Architektura

```
┌─────────────────────────────────────────────────────────┐
│  Network-Aware WebSocket Client                         │
├─────────────────────────────────────────────────────────┤
│  ✓ NetworkCallback (retry pouze když je síť)           │
│  ✓ Exponential backoff (5s → 5min)                      │
│  ✓ Heartbeat timeout detection (30s ping, 90s timeout) │
│  ✓ Keepalive každých 20s (prevence FW timeout)          │
│  ✓ Auto-fallback na HTTP (po 3x selhání)                │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  Offline Queue (Prioritized)                            │
├─────────────────────────────────────────────────────────┤
│  ✓ URGENT: LOCK_NOW, UNLOCK_NOW                        │
│  ✓ HIGH: Recent usage logs                             │
│  ✓ NORMAL: Old usage logs                              │
│  ✓ LOW: Keywords sync                                  │
│  ✓ Batch limit (20 msg/reconnect)                      │
│  ✓ Retry s exponential backoff                          │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  Backend Timeout & Cleanup                              │
├─────────────────────────────────────────────────────────┤
│  ✓ Receive timeout (60s)                                │
│  ✓ Ping check každých 60s                              │
│  ✓ Auto-cleanup "zombie" spojení                        │
│  ✓ Connection state tracking                            │
└─────────────────────────────────────────────────────────┘
```

---

## Srovnání: Aktuální vs. Robustní

| Scénář | Aktuální | Robustní |
|--------|----------|----------|
| **Krátký výpadek (5-30s)** | ✅ Funguje | ✅ Funguje + rychlejší reconnect |
| **Dlouhý výpadek (5+ min)** | ⚠️ Plýtvá baterií | ✅ Retry pouze když je síť |
| **FW timeout (30-60s)** | 🔴 **KRITICKÉ** | ✅ Detekce + reconnect |
| **NAT timeout (2-5 min)** | 🔴 **KRITICKÉ** | ✅ Keepalive + detekce |
| **FW blokuje WS** | ⚠️ Nekonečné retry | ✅ Auto-fallback na HTTP |
| **Proxy timeout** | 🔴 **KRITICKÉ** | ✅ Detekce + reconnect |
| **Offline data** | ⚠️ Hromadí se | ✅ Prioritizovaná queue |
| **Zombie spojení** | 🔴 **KRITICKÉ** | ✅ Heartbeat timeout |

---

## Implementační Priorita

### 🔴 Priorita 1 - Kritické (Okamžitě)
1. **Heartbeat timeout detection** (detekce zombie spojení)
2. **Network-aware reconnect** (retry pouze když je síť)
3. **Backend timeout handling** (cleanup zombie spojení)

**Dopad:** Opraví kritické problémy s FW/NAT timeout

### 🟡 Priorita 2 - Důležité (1 týden)
4. **Exponential backoff** (úspora baterie)
5. **Offline queue s prioritizací** (spolehlivé odesílání)
6. **Keepalive ping** (prevence FW timeout)

**Dopad:** Zlepší robustnost a úsporu baterie

### 🟢 Priorita 3 - Vylepšení (1 měsíc)
7. **Auto-fallback na HTTP** (pokud WS selže)
8. **Connection state tracking** (monitoring)
9. **Adaptivní intervaly** (podle network quality)

**Dopad:** Další vylepšení UX a reliability

---

## Závěr

**Aktuální implementace má kritické problémy:**
- 🔴 **Zombie spojení** (FW/NAT timeout) - agent si myslí, že je online, ale není
- 🔴 **Nekonečné retry** bez sítě - plýtvá baterií
- ⚠️ **Chybějící offline queue** - data se mohou ztratit

**Robustní řešení:**
- ✅ Network-aware reconnect (retry pouze když je síť)
- ✅ Heartbeat timeout detection (detekce zombie spojení)
- ✅ Exponential backoff (úspora baterie)
- ✅ Offline queue s prioritizací (spolehlivé odesílání)
- ✅ Backend timeout handling (cleanup)
- ✅ Keepalive ping (prevence FW timeout)
- ✅ Auto-fallback na HTTP (pokud WS selže)

**Doporučení:** Implementovat alespoň Prioritu 1 (kritické) okamžitě, protože aktuální stav může vést k ztrátě dat a falešnému pocitu, že agent je online.
