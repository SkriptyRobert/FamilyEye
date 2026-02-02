# Politika Zabezpečení

## Podporované Verze

| Verze | Podporováno        |
| ------- | ------------------ |
| 2.x.x   | :white_check_mark: |

## Hlášení Zranitelností

**Prosím hlašte chyby prostřednictvím veřejných GitHub Issues.**

Pokud objevíte bezpečnostní zranitelnost, nahlaste ji prosím následovně:

1. **Email:** Pošlete detaily na **robert.pesout@gmail.com** (Róbert Pešout, BertSoftware)
2. **Uveďte:**
   - Popis zranitelnosti
   - Kroky k reprodukci
   - Potenciální dopad
   - Navrhované opravy (volitelné)

### Co očekávat

- **Doba odezvy:** Snažíme se odpovědět do 48 hodin
- **Aktualizace:** Budeme vás informovat o našem postupu
- **Kredit:** Rádi vás uvedeme v poděkování u opravy (pokud si to přejete)

## Bezpečnostní Doporučení

Při nasazování FamilyEye:

1. **Vždy nastavte `SECRET_KEY`** - Nikdy nepoužívejte výchozí hodnotu v produkci
2. **Používejte HTTPS** - Umístěte platné SSL certifikáty do `certs/`
3. **Zabezpečte databázi** - Udržujte `parental_control.db` šifrovanou nebo chráněnou
4. **Aktualizujte** - Pravidelně aktualizujte na nejnovější verzi

### Veřejné / Internetové nasazení

Pokud je server vystaven na veřejné IP adrese (např. skeny API, boti):

- **Sondovací cesty (Probe paths)** - Backend vrací 404 pro citlivé/sondovací cesty (např. `/.env`, `/.git`, `wp-admin`, `phpmyadmin`, `config.json`) namísto obsluhy SPA.
- **Bezpečnostní hlavičky** - Odpovědi obsahují `X-Content-Type-Options: nosniff` a `X-Frame-Options: DENY`.
- **Omezení rychlosti (Rate limiting)** - Veřejné cesty (`/`, `/api/health`, `/api/info`, `/api/trust/*`) jsou omezeny na IP (60/min). Přihlášení 5/min, registrace 3/min, párování 10/min. Nastavte `TRUST_PROXY=1` pouze pokud jste za důvěryhodnou reverzní proxy (nginx), aby se klientská IP brala z `X-Forwarded-For`; jinak aplikace použije IP přímého spojení.
- **API dokumentace** - V produkci nastavte `DISABLE_DOCS=1` nebo `BACKEND_ENV=production` pro vypnutí `/docs`, `/redoc`, `/openapi.json`.
- **Reverzní proxy** - Pro veřejné nasazení použijte nginx (nebo podobný) vpředu: TLS terminace s platným certifikátem (např. Let's Encrypt), přísnější rate limity, volitelně WAF. Nepoužívejte `.env` v gitu (commit); nastavte `SECRET_KEY`, `POSTGRES_PASSWORD`, `BACKEND_URL` v prostředí.

## Známá Bezpečnostní Specifika

### Uložení PINu (Android Agent)
Android agent používá SHA-256 pro lokální uložení PINu. Pro zvýšení bezpečnosti v budoucích verzích plánujeme migraci na bcrypt se solí specifickou pro zařízení.

### Self-Signed Certifikáty
Pro nasazení v lokální síti jsou self-signed certifikáty akceptovatelné. Pro veřejné nasazení použijte Let's Encrypt nebo podobnou certifikační autoritu (CA).

### Logování
Nelogujte celé tokeny, API klíče nebo hesla. Logujte pouze prefixy (např. prvních 8 znaků) nebo citlivá pole vynechte.

---

Děkujeme, že pomáháte udržet FamilyEye bezpečné!
