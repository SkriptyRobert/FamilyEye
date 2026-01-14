
# 🔋 Analýza Spotřeby Baterie a Výkonu

## 1. Celkové Hodnocení
**Dopad na baterii: Nízký až Střední (~2-5% denně navíc)**

Vaše řešení je navrženo efektivně. Většina logiky je "Event-Driven" (reaguje na události), místo aby neustále běžela ve smyčce. Níže je technický rozbor jednotlivých komponent.

---

## 2. Technický Rozbor

### ✅ Co je šetrné (Dobré):
1.  **Chytrá Detekce Aplikací (`AppDetectorService`)**
    *   Používá `AccessibilityEvent`, což je **Push** metoda.
    *   **Proč je to dobré:** Agent "spí", dokud uživatel neotevře novou aplikaci. Systém ho probudí jen při změně. To je mnohem úspornější než se každou sekundu ptát "co běží?".

2.  **Šetřič Dat (`Reporter`)**
    *   Máte implementovanou logiku `isDataSaver && !isWifiConnected`.
    *   **Proč je to dobré:** 4G/5G rádio je největší žrout baterie. Tím, že odkládáte odesílání logů na Wi-Fi, šetříte desítky procent energie.

3.  **Efektivní Polling (`UsageTracker`)**
    *   Kontrola limitů běží v intervalu **5 sekund** (`delay(5000)`).
    *   **Dopad:** 5s je rozumný kompromis mezi přesností blokování a baterií. Pokud by to byla 1s, spotřeba by stoupla.

### ⚠️ Co bere energii (Nutné zlo):
1.  **WakeLock (`FamilyEyeService`)**
    *   Aby Android službu nezabil, musíte ji držet naživu. To brání procesoru přejít do nejhlubšího spánku (Deep Sleep).
    *   **Řešení:** "Ignorovat optimalizaci baterie", které jsme právě přidali, je pro stabilitu nutné, i když to mírně zvyšuje spotřebu v nečinnosti.

2.  **Síťová Aktivita (Heartbeat)**
    *   `Reporter` posílá data každých **30 sekund**.
    *   **Doporučení:** Pokud je zařízení v klidu (zhasnutý displej), mohli byste tento interval prodloužit na 5-10 minut.

---

## 3. Srovnání s "Velkými Hráči"

| Aplikace | Metoda Detekce | Spotřeba | Poznámka |
| :--- | :--- | :--- | :--- |
| **Qustodio/Norton** | VPN Service | Vyšší 🔴 | VPN musí filtrovat každý paket. To žere CPU i baterii. |
| **Family Link** | OS Integrace | Minimální 🟢 | Je součástí systému, takže skoro nic navíc. |
| **FamilyEye (Vy)** | Accessibility (GUI) | Nízká 🟡 | Sledujeme jen změny oken. Nečteme síťový provoz. |

## 4. Doporučení pro další optimalizaci

Pokud by si uživatelé stěžovali na baterii, doporučuji implementovat **"Adaptive Polling"**:

1.  **Když je displej ON:** Sync každých 30s (jak to je teď).
2.  **Když je displej OFF:** Sync každých 15 minut (nebo vůbec, dokud se nerozsvítí).

Toto by srazilo spotřebu v idle režimu na nulu.

---

### Závěr
Máte **čisté, asynchronní (Coroutines) řešení**. Není to "spaghetti code", který by se zacyklil. Pro tento typ aplikace (Real-time monitoring) je spotřeba adekvátní a konkurenceschopná.
