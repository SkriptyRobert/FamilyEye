# Parental Control Enterprise - Dokumentace

## Přehled

Systém rodičovské kontroly pro Windows s webovým dashboardem a agentem pro monitorování a vynucování pravidel.

## Struktura dokumentace

### Základní dokumenty

- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - Architektura systému, komponenty, toky dat
- **[BACKEND.md](./BACKEND.md)** - Backend API, moduly, konfigurace
- **[FRONTEND.md](./FRONTEND.md)** - Frontend komponenty, routing, služby
- **[AGENT.md](./AGENT.md)** - Windows agent, monitorování, vynucování pravidel
- **[API.md](./API.md)** - API endpointy, autentizace, schémata
- **[DATABASE.md](./DATABASE.md)** - Databázové modely, schéma, vztahy
- **[DEPLOYMENT.md](./DEPLOYMENT.md)** - Instalace, konfigurace, nasazení
- **[DEVELOPMENT.md](./DEVELOPMENT.md)** - Vývojové prostředí, build, testování

### Specifikace a nástroje

- **[UX_REDESIGN_SPEC.md](./UX_REDESIGN_SPEC.md)** - UX/UI redesign specifikace, design guidelines
- **[GITHUB.md](./GITHUB.md)** - GitHub limity, doporučení, best practices

## Rychlý start

1. **Instalace serveru**: Viz [DEPLOYMENT.md](./DEPLOYMENT.md#instalace-serveru)
2. **Instalace agenta**: Viz [DEPLOYMENT.md](./DEPLOYMENT.md#instalace-agentu)
3. **Vývoj**: Viz [DEVELOPMENT.md](./DEVELOPMENT.md)

## Komponenty

```
Parental-Control_Enterprise/
├── backend/          # FastAPI backend server
├── frontend/         # React dashboard
├── clients/windows/   # Windows agent
└── docs/             # Tato dokumentace
```

## Verze

- **Backend**: FastAPI 0.104.1
- **Frontend**: React 18.2.0, Vite 5.0.8
- **Agent**: Python 3.x, psutil, pywin32

## Aktualizace dokumentace

Při přidávání nových funkcí:
1. Aktualizujte příslušný modul (BACKEND.md, FRONTEND.md, atd.)
2. Přidejte změny do CHANGELOG.md (pokud existuje)
3. Aktualizujte API.md pro nové endpointy

## Kontakt

Pro dotazy a podporu viz README.md v kořenovém adresáři projektu.

