# FamilyEye - Dokumentace

Vítejte v dokumentaci FamilyEye, kompletního řešení rodičovské kontroly s pokročilou ochranou pomocí Device Owner módu a Smart Shield technologie.

## Co je FamilyEye?

FamilyEye je open-source systém rodičovské kontroly, který umožňuje rodičům:

- **Monitorovat použití zařízení** - Sledování času stráveného v aplikacích
- **Vynucovat pravidla** - Blokování aplikací, časové limity, rozvrhy
- **Smart Shield** - Pokročilá detekce škodlivého obsahu v reálném čase
- **Device Owner ochrana** - Android zařízení nelze odinstalovat bez souhlasu rodiče
- **Real-time notifikace** - Okamžité upozornění na důležité události

## Komponenty systému

### Backend Server
FastAPI server poskytující REST API a WebSocket komunikaci. Spravuje zařízení, pravidla, statistiky a Smart Shield detekce.

**Dokumentace**: [BACKEND.md](BACKEND.md)

### Frontend Dashboard
React dashboard pro rodiče s moderním UI. Zobrazuje statistiky, umožňuje správu pravidel a konfiguraci Smart Shield.

**Dokumentace**: [FRONTEND.md](FRONTEND.md)

### Windows Agent
Python agent pro Windows zařízení. Monitoruje aplikace, vynucuje pravidla a odesílá statistiky.

**Dokumentace**: [AGENT.md](AGENT.md)

### Android Agent
Kotlin agent pro Android zařízení s Device Owner ochranou. Poskytuje nejvyšší úroveň ochrany a Smart Shield detekci.

**Dokumentace**: [AGENT.md](AGENT.md#android-agent)

## Rychlý start

1. **Instalace serveru**: Viz [DEPLOYMENT.md](DEPLOYMENT.md#instalace-serveru)
2. **Párování zařízení**: Viz [tutorials/first-setup.md](tutorials/first-setup.md)
3. **Konfigurace Smart Shield**: Viz [tutorials/getting-started.md](tutorials/getting-started.md)

## Architektura

Kompletní popis architektury systému, toku dat a životního cyklu aplikace.

**Dokumentace**: [ARCHITECTURE.md](ARCHITECTURE.md)

**Detailní systémový design**: [architecture/system-design.md](architecture/system-design.md)

**Bezpečnostní model**: [architecture/security-model.md](architecture/security-model.md)

## API Reference

Kompletní dokumentace REST API endpointů.

**Dokumentace**: [API.md](API.md)

**Detailní API reference**: [reference/api-docs.md](reference/api-docs.md)

## Funkce

### Smart Shield
Pokročilá detekce škodlivého obsahu pomocí Aho-Corasick algoritmu. Skenuje obsah aplikací v reálném čase a detekuje klíčová slova.

**Dokumentace**: [reference/feature-matrix.md](reference/feature-matrix.md#smart-shield---aho-corasick-algoritmus)

### Device Owner
Android Device Owner mód poskytuje nejvyšší úroveň ochrany. Aplikaci nelze odinstalovat bez souhlasu rodiče.

**Dokumentace**: [architecture/security-model.md](architecture/security-model.md#device-owner-proč-nelze-odinstalovat)

### Pravidla a limity
- Blokování aplikací
- Časové limity
- Denní limity
- Časové rozvrhy
- Blokování sítě

**Dokumentace**: [API.md](API.md#pravidla)

## Návody

### Pro uživatele
- [První nastavení](tutorials/first-setup.md) - Jak začít s FamilyEye
- [Základy](tutorials/getting-started.md) - Základní použití

### Řešení problémů
- [Troubleshoot USB](how-to/troubleshoot-usb.md) - Problémy s USB připojením
- [Obnovení přístupu](how-to/restore-access.md) - Jak obnovit přístup
- [Změna PIN](how-to/change-pin.md) - Změna PIN kódu
- [Odblokování aplikace](how-to/unblock-app.md) - Jak odblokovat aplikaci

## Reference

- [Feature Matrix](reference/feature-matrix.md) - Kompletní mapa funkcí
- [API Dokumentace](reference/api-docs.md) - Detailní API reference
- [Error Codes](reference/error-codes.md) - Kódy chyb
- [Testing](reference/testing.md) - Testování

## Vývoj

Informace pro vývojáře o přidávání funkcí, testování a architektuře.

**Dokumentace**: [DEVELOPMENT.md](DEVELOPMENT.md)

## Nasazení

Návod na instalaci a nasazení systému v produkčním prostředí.

**Dokumentace**: [DEPLOYMENT.md](DEPLOYMENT.md)

## Databáze

Schéma databáze, modely a optimalizace.

**Dokumentace**: [DATABASE.md](DATABASE.md)

## Bezpečnost

Bezpečnostní model, Device Owner ochrana a imunitní systém proti killnutí.

**Dokumentace**: [architecture/security-model.md](architecture/security-model.md)

## Podpora

Pro dotazy a pomoc:
- **GitHub Issues**: Otevřete issue na GitHubu
- **Dokumentace**: Procházejte tuto dokumentaci
- **README**: Viz hlavní [README.md](../README.md)

---

**Verze dokumentace**: 1.0.0  
**Poslední aktualizace**: 2026-01-26
