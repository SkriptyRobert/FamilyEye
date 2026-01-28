# Politika Zabezpečení

## Podporované Verze

| Verze | Podporováno |
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

- **Doba odezvy:** Snažím se odpovědět co nejdříve
- **Aktualizace:** Budu zpětně informovat o postupu
- **Kredit:** Rád vás uvedu v poděkování u opravy (pokud si to přejete)

## Bezpečnostní Doporučení 

Při nasazování FamilyEye:

1. **Vždy nastavte `SECRET_KEY`** - Nikdy nepoužívejte defaultní hodnotu v produkci
2. **Používejte HTTPS** - Umístěte platné SSL certifikáty do `certs/`
3. **Zabezpečte databázi** - Udržujte `parental_control.db` šifrovanou nebo chráněnou
4. **Aktualizujte** - Pravidelně aktualizujte na nejnovější verzi

## Známá Bezpečnostní Opatření

### Uložení PINu (Android Agent)
Android agent používá SHA-256 pro lokální uložení PINu. Pro zvýšení bezpečnosti v budoucích verzích plánujeme migraci na bcrypt se solí specifickou pro zařízení.

### Self-Signed Certifikáty
Pro nasazení v lokální síti jsou self-signed certifikáty akceptovatelné. Pro veřejné nasazení použijte Let's Encrypt nebo podobnou certifikační autoritu.

---

Děkuji, že pomáháte udržet FamilyEye bezpečné! 🔐
