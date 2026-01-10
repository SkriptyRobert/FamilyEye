# Architektura Agenta: Měření a Synchronizace

Tento dokument popisuje technické fungování agenta FamilyEye (verze 2.0+), konkrétně jak měří čas, uplatňuje limity a synchronizuje data s backendem.

## 1. Měření Času a Aktivity

Agent používá modul `AppMonitor` (v `monitor.py`), který běží v nekonečné smyčce (default 1s interval).

### A. Detekce Aplikací
*   **Seznam procesů:** V každém cyklu získá seznam všech běžících procesů pomocí `psutil`.
*   **Filtrování šumu:** Ignoruje systémové procesy (např. `svchost`, `dwm`, `runtimebroker`), které jsou definovány v seznamu `IGNORED_PROCESSES`, aby se zabránilo falešným detekcím.
*   **Detekce Okna:** Zjišťuje, která aplikace má právě *aktivní okno* (focus) pomocí Windows API (`active_window_handle`).
*   **Konsolidace:** Slučuje pomocné procesy pod hlavní aplikaci (např. `steamwebhelper` -> `steam`, `chrome_crashpad` -> `chrome`).

### B. Počítání Času
*   **Aktivní okno:** Pokud má uživatel otevřené okno aplikace (např. Chrome) a hýbe myší/píše (není "idle"), přičítá se čas této aplikaci.
*   **Idle detekce:** Pokud uživatel neinteraguje se zařízením déle než X sekund, čas se přestane započítávat.
*   **Celkový čas zařízení:** Měří se "wall-clock" čas, kdy je agent aktivní a uživatel je přihlášen. Nejde jen o součet časů aplikací, ale o reálnou dobu strávenou na PC.

---

## 2. Synchronizace s Backendem

Agent nespoléhá pouze na své lokální počítadlo (které se resetuje restartem), ale synchronizuje se s ""pravdou"" na serveru.

### A. Odesílání Dat (Push) - `UsageReporter`
*   **Interval:** Každých 60 sekund (nebo ihned po znovu-připojení internetu).
*   **Delta Reporting:** Agent odesílá pouze *přírůstky* (kolik sekund uběhlo od posledního reportu).
*   **Offline Cache:** Pokud není internet, data se ukládají do fronty na disku (`report_queue.json`). Po obnovení spojení se odešlou všechna najednou.
*   **Mechanismus:** Data se "vyfotí" (snap) z monitoru a vloží do fronty, aby se neblokovalo měření.

### B. Stahování Pravidel (Pull) - `RuleEnforcer`
*   **Interval:** Každých 30-60 sekund.
*   **Data ze serveru:**
    1.  **Pravidla:** Limity, blokované weby, rozvrhy.
    2.  **Dnešní součty (`usage_by_app`):** Kolik sekund už daná aplikace dnes běžela (včetně jiných session a offline dat, která už server zpracoval).
    3.  **Čas serveru:** Pro ochranu proti změně času na PC.

---

## 3. Uplatňování Limitů a Rozvrhů

Agent používá logiku `MAX(Backend, Lokální)` pro určení aktuálního stavu. To zabraňuje obcházení limitů restartováním agenta.

### A. Denní Limity Aplikací
*   **Logika:** `Použito = MAX(Backend_Total, Lokální_Session_Usage)`
*   **Kontrola:** Pokud `Použito >= Limit`:
    1.  Agent okamžitě ukončí (kill) všechny procesy dané aplikace.
    2.  Zobrazí notifikaci uživateli.
    3.  Odešle kritickou událost na server (mimo běžnou frontu).

### B. Denní Limit Zařízení
*   Funguje stejně jako limity aplikací, ale počítá celkový čas.
*   Při překročení: Zamkne obrazovku Windows (`LockWorkStation`) a po odpočtu (60s) vypne počítač.

### C. Rozvrhy (Časová okna)
*   **Autoritativní čas:** Agent používá "Trusted Time". Porovnává svůj interní čas (monotonic clock) s časem serveru získaným při posledním syncu. Pokud si dítě změní čas ve Windows, agent to pozná a ignoruje to.
*   **Vynucení:** Pokud je aktuální "Trusted Time" mimo povolené rozvrhy, agent zamkne PC a vypne ho.

---

## 4. Odolnost proti výpadkům a offline režim

Sytém FamilyEye je navržen tak, aby byl odolný proti výpadkům internetu i pokusům o obcházení.

*   **Měření se nezastaví:** Agent na počítači nepotřebuje internet k tomu, aby sledoval aktivitu. Neustále (v sekundových intervalech) kontroluje běžící procesy a aktivní okna.
*   **Lokální paměť (Cache):** Veškerý čas strávený v aplikacích si agent ukládá do své lokální paměti na disku (tzv. `usage_cache.json`). I když není internet, agent pokračuje v měření.
*   **Sledování nových aplikací:** Agent zaznamená i aplikace, které uživatel otevřel až během výpadku.
*   **Dopočítání po připojení:** Jakmile se internet opět připojí, agent okamžitě rozpozná online stav a odesílá všechna nasbíraná data z doby offline v jedné dávce na server (`report_queue.json`).
*   **Offline Enforcing:** Pokud je nastaven limit (např. 2 hodiny), agent jej vynucuje i offline. Pokud uživatel dosáhne limitu během výpadku internetu, agent aplikaci ukončí na základě lokálně uložených pravidel.

---

## Shrnutí Toku Dat

1.  **Agent (Monitor)** naměří 1 minutu aktivity ve hře "Minecraft".
2.  **Agent (Reporter)** vloží tuto 1 minutu do fronty a odešle na Backend.
3.  **Backend** přičte 1 minutu k dnešnímu součtu pro Minecraft.
4.  **Agent (Enforcer)** si stáhne nová pravidla a dozví se: "Minecraft dnes běžel celkem 55 minut".
5.  Pokud je limit 60 minut, agent ví, že zbývá už jen 5 minut, i když tato lokální session běží teprve chvíli.
