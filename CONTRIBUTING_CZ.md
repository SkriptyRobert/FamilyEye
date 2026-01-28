# Jak přispět do FamilyEye

Děkujeme, že chcete pomoci vylepšit FamilyEye. Každá oprava nebo nápad se počítá.

## Jak přispět

1. **Fork** – Vytvořte si kopii projektu pod svým účtem.
2. **Větev** – Vytvořte větev (např. `feature/vas-napad`) a proveďte změny.
3. **Pull Request** – Až budete hotovi, otevřete PR proti cílové větvi.

### Technické minimum

- **Backend:** Python 3.11, spuštění přes `python run_https.py` v adresáři `backend/` (ve virtuálním prostředí).
- **Frontend:** Node.js 18+, spuštění přes `npm run dev` v adresáři `frontend/`.
- **Agent:** Viz `clients/windows/` a `clients/android/` pro sestavení a nastavení (volitelné, jen při změnách agenta).
- Udržujte kód čitelný a otestovaný, aby ho ostatní mohli kontrolovat a udržovat.

---

## Právní ujištění / Dohoda přispěvatele

Odesláním příspěvku (např. Pull Request) potvrzujete, že:

1. **Autorství a práva** – Jste autorem přispívaného kódu, nebo máte právo jej přispět pod licencí projektu (GPL-3.0).
2. **Žádná kolizní práva** – Váš příspěvek neporušuje práva třetích osob (včetně autorských práv, patentů, ochranných známek či jiných duševních vlastnických práv). Nebudete přispívat kódem, který je vázán licencí nebo patentem neslučitelným s licencí projektu.
3. **Odpovědnost** – Nesete odpovědnost za to, co odesíláte; změny jste zkontrolovali a souhlasíte s tím, že mohou být použity za podmínek projektu.
4. **Udělení práv projektu** – Udělujete správci projektu (Róbert Pešout / BertSoftware – robert.pesout@gmail.com) neomezené a trvalé právo používat, upravovat a začleňovat váš příspěvek do projektu, včetně možnosti jej v budoucnu použít pod jinými (i komerčními) licencemi.

*Proč?* Aby projekt mohl dál rozvíjet bez nutnosti žádat jednotlivé přispěvatele o souhlas. Zůstáváte uvedeni jako autor; projekt si ponechává právo kód používat a přelicencovat.

---

## Pravidla chování (Code of Conduct)

Chovejte se k ostatním s respektem. Cílem je tvořit užitečný nástroj pro rodiny.

---

## Testy, buildy a CI

### Co se spouští automaticky (GitHub Actions)

| Workflow | Kdy se spustí | Co dělá |
|----------|----------------|---------|
| **Backend testy** | Push/PR do `backend/**` | `pytest` v `backend/tests/` |
| **Frontend testy** | Push/PR do `frontend/**` | `npm test` v `frontend/` |
| **Android testy** | Push/PR do `clients/android/**` | `./gradlew test`; na hlavních větvích také build APK (artefakt) |
| **Build Server (Docker)** | Push/PR do `backend/**`, `frontend/**`, `docker/**` | Sestaví frontend, Docker image a pushne do GHCR (`familyeye-server`) |
| **Build Windows Agent** | Push/PR do `installer/agent/**`, `clients/windows/**` | Sestaví Windows instalátor (artefakt) |
| **Create Release** | Push tagu `v*` (např. `v2.4.0`) | Spustí unit testy backendu, frontendu a Androidu; sestaví APK a Windows instalátor; vytvoří GitHub Release a přiloží artefakty |

Release se vytvoří **až po úspěchu všech unit testů**. 

### Co spustit lokálně před otevřením PR

- **Backend:** Z `backend/`: `pip install -r requirements.txt pytest pytest-cov pytest-asyncio`, poté `python -m pytest tests/ -x --tb=short` (případně `DATABASE_URL=sqlite:///:memory:` a `BACKEND_URL=http://localhost:8000`).
- **Frontend:** Z `frontend/`: `npm ci && npm test -- --run`.
- **Android:** Z `clients/android/`: `./gradlew test` (nebo spuštění testů z Android Studio).

Podrobnější popis testů a kritických testů před releasem je v `docs/reference/testing.md`.

### Docker image a nasazení

- Předpřipravená serverová image: `ghcr.io/skriptyrobert/familyeye/familyeye-server:latest` (a tagy dle SHA commitu). Použití s `docker/server/docker-compose.yml`; v `.env` nastavte `BACKEND_URL` na veřejnou URL. Viz `docker/server/README.md`.
