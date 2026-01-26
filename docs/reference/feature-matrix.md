# Feature Matrix - Mapa funkcí a ikon

Kompletní reference všech funkcí Smart Shield, jejich chování a technických detailů. Tento dokument slouží jako "Bible funkcí" pro vývojáře i uživatele.

## Kategorizace aplikací

Aplikace jsou automaticky kategorizovány podle jejich package name nebo názvu. Kategorizace probíhá v `backend/app/services/app_filter.py` a používá konfiguraci z `backend/app/config/app-config.json`.

### Kategorie a ikony

| Kategorie | Ikona | Popis | Příklady aplikací |
|-----------|-------|-------|-------------------|
| `gameLaunchers` | `game` | Herní launchery | Steam, Epic Games, GOG Galaxy |
| `games` | `game` | Herní aplikace | Minecraft, Roblox, Fortnite |
| `communication` | `chat` | Komunikační aplikace | Discord, WhatsApp, Telegram |
| `browsers` | `globe` | Webové prohlížeče | Chrome, Firefox, Edge |
| `streaming` | `video` | Streamovací služby | YouTube, Netflix, Spotify |
| `productivity` | `file-text` | Produktivní aplikace | Word, Excel, Notion |
| `development` | `code` | Vývojářské nástroje | VS Code, IntelliJ, Android Studio |
| `creative` | `image` | Kreativní nástroje | Photoshop, Figma, Blender |
| `education` | `book` | Vzdělávací aplikace | Duolingo, Anki, Kahoot |
| `store` | `download` | Obchody s aplikacemi | Microsoft Store |

## Funkce filtrování aplikací

### `app_filter.is_trackable(app_name: str) -> bool`

**Co vidí uživatel:** Aplikace se zobrazuje/nezobrazuje v seznamu použití

**Technický detail:**
- Kontroluje `blacklistPatterns` z `app-config.json`
- Systémové procesy (idle, svchost, dwm) = `False`
- Běžné aplikace (chrome, msedge) = `True`

**Zdroj:** `backend/app/services/app_filter.py:is_trackable()`

### `app_filter.get_friendly_name(app_name: str) -> str`

**Co vidí uživatel:** Lidsky čitelný název aplikace (např. "Microsoft Edge" místo "msedge")

**Technický detail:**
- Mapování z `friendlyNames` v `app-config.json`
- Pokud není v mapě, vrací původní název
- Odstraňuje `.exe` příponu

**Příklady:**
- `msedge` → `Microsoft Edge`
- `steam` → `Steam`
- `UnknownApp` → `UnknownApp` (není v mapě)

**Zdroj:** `backend/app/services/app_filter.py:get_friendly_name()`

### `app_filter.get_category(app_name: str) -> str`

**Co vidí uživatel:** Kategorie aplikace (pro ikony a seskupování)

**Technický detail:**
- Prochází `whitelist` kategorie v `app-config.json`
- Vrací první shodnou kategorii
- Pokud není shoda, vrací `None`

**Zdroj:** `backend/app/services/app_filter.py:get_category()`

### `getAppIcon(appName: string, config: object) -> string`

**Co vidí uživatel:** Ikona aplikace v UI

**Technický detail:**
- Frontend funkce v `frontend/src/utils/formatting.js`
- Používá `iconMapping` z konfigurace
- Vrací název ikony (game, chat, globe, etc.)
- Fallback: `smartphone` pokud není nalezena kategorie

**Zdroj:** `frontend/src/utils/formatting.js:getAppIcon()`

## Smart Shield - Aho-Corasick algoritmus

### Jak funguje detekce klíčových slov

Smart Shield používá **Aho-Corasick algoritmus** pro efektivní detekci více klíčových slov současně v textu. Implementace je v `clients/android/app/src/main/java/com/familyeye/agent/scanner/KeywordDetector.kt`.

#### Trie struktura + Failure Links

1. **Trie (prefix tree)**: Každé klíčové slovo je uloženo jako cesta v stromu
2. **Failure links**: Každý uzel má odkaz na nejdelší vlastní sufix, který je také prefixem nějakého klíčového slova
3. **Vyhledávání**: Prochází text jednou a kontroluje všechny možné shody pomocí failure links

**Příklad:**
```
Klíčová slova: ["he", "she", "his", "hers"]
Text: "ushers"
- Najde "she" na pozici 2-4
- Najde "he" na pozici 3-4
- Najde "hers" na pozici 2-5
```

#### Normalizace textu

**Funkce:** `normalize(input: String?) -> String`

**Technický detail:**
1. `Normalizer.normalize(Form.NFD)` - Decompose diakritiku
2. Regex `\\p{InCombiningDiacriticalMarks}+` - Odstraní všechny diakritické značky
3. `lowercase(Locale.getDefault())` - Převede na malá písmena

**Výsledek:**
- `"Sebevražda"` → `"sebevrazda"`
- `"DROGY"` → `"drogy"`
- `"Násilí"` → `"nasili"`

**Zdroj:** `KeywordDetector.kt:normalize()`

#### Case-insensitive matching

Všechna klíčová slova a text jsou normalizována na lowercase před porovnáním. To znamená:
- `"DROGY"` detekuje `"drogy"`
- `"Sebevražda"` detekuje `"sebevražda"`

#### Ignorování scrollování

**Problém:** Streaming aplikace (YouTube, Netflix, Spotify) neustále scrollují obsah, což by způsobovalo spam detekcí.

**Řešení:** `IGNORED_PACKAGES` v `ContentScanner.kt`

```kotlin
private val IGNORED_PACKAGES = setOf(
    "com.google.android.youtube",
    "com.netflix.mediaclient",
    "com.spotify.music"
)
```

**Chování:** Pokud je aktuální aplikace v `IGNORED_PACKAGES`, Smart Shield **neskenuje obsah**.

**Zdroj:** `ContentScanner.kt:processScreen()`

#### Rate limiting

**Konstanta:** `SCAN_INTERVAL_MS = 2000L` (2 sekundy)

**Chování:** Smart Shield skenuje obsah maximálně jednou za 2 sekundy, i když se obsah mění častěji.

**Důvod:** Šetření baterie a CPU.

**Zdroj:** `ContentScanner.kt:processScreen()`

#### Node limit pro Chrome DOM

**Konstanta:** `MAX_NODES = 500`

**Problém:** Chrome DOM může mít tisíce uzlů, což by způsobovalo zamrznutí aplikace.

**Řešení:** DFS traversal je limitován na 500 uzlů.

**Zdroj:** `ContentScanner.kt:extractText()`

## Kategorie klíčových slov

Výchozí klíčová slova jsou definována v `backend/app/config/smart_shield_defaults.json` a jsou automaticky přidána při párování nového zařízení.

### Kategorie a severity

| Kategorie | Label | Barva | Severity levels | Příklady |
|-----------|-------|-------|-----------------|----------|
| `self-harm` | Sebevražda | - | critical | sebevražda, zabít se, podřezat |
| `drugs` | Drogy | - | high, medium | drogy, pervitin, kokain, tráva |
| `bullying` | Šikana | - | high, medium | šikana, chcípni, jsi nula |
| `adult` | Dospělí | - | high, medium | porno, xxx, onlyfans |
| `custom` | Vlastní | - | high, medium, low | Uživatelsky definované |

**Severity levels:**
- `critical` - Okamžité upozornění rodiči
- `high` - Vysoká priorita
- `medium` - Střední priorita
- `low` - Nízká priorita

**Zdroj:**
- Backend: `backend/app/config/smart_shield_defaults.json`
- Frontend: `frontend/src/components/shield/CategorySection.jsx`

## Chování funkcí

### Blokování aplikací

| Funkce | Chování | Priorita |
|--------|---------|----------|
| `app_block` | Aplikace je kompletně blokována | High |
| `time_limit` | Aplikace je blokována po dosažení limitu | Medium |
| `schedule` | Aplikace je blokována mimo časové okno | Medium |
| `lock_device` | Celé zařízení je zamčeno | Highest |
| `network_block` | Internet je blokován | High |

### Monitoring

| Funkce | Chování | Priorita |
|--------|---------|----------|
| Usage tracking | Sledování času použití | Low |
| Content scanning | Skenování obsahu pro klíčová slova | Medium |
| Screenshot capture | Pořízení screenshotu při detekci | High |

## Technické reference

### Backend soubory

- `backend/app/config/app-config.json` - Whitelist, iconMapping, friendlyNames
- `backend/app/config/smart_shield_defaults.json` - Výchozí klíčová slova
- `backend/app/services/app_filter.py` - Filtrování a kategorizace aplikací

### Android soubory

- `clients/android/app/src/main/java/com/familyeye/agent/scanner/KeywordDetector.kt` - Aho-Corasick implementace
- `clients/android/app/src/main/java/com/familyeye/agent/scanner/ContentScanner.kt` - Skenování obsahu
- `clients/android/app/src/main/java/com/familyeye/agent/scanner/KeywordManager.kt` - Správa klíčových slov

### Frontend soubory

- `frontend/src/utils/formatting.js` - `getAppIcon()`, formátování
- `frontend/src/components/shield/CategorySection.jsx` - UI kategorie
- `frontend/src/components/DynamicIcon.jsx` - Mapování ikon na Lucide komponenty
