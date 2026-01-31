# FamilyEye – webovka (landing page)

Landing page projektu FamilyEye. Nasazuje se na GitHub Pages (dokumentace na `/docs/`).

## Lokální náhled

```bash
cd website
npm install
npm run dev
```

Odkaz „Dokumentace“ vede na `base/docs/` – na GitHub Pages po deployi tam bude MkDocs.

## GitHub Pages (deploy)

Workflow `deploy-website.yml` sestaví webovku i MkDocs a nasadí je: webovka na kořen, dokumentace na `/docs/`.

## Obrázky

Do `website/public/images/` vložte logo a screenshoty. Při deployi CI zkopíruje assety z `docs/`.
