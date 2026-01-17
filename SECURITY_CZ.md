# Politika Zabezpečení (Security Policy)

Bereme bezpečnost vážně. FamilyEye je nástroj pro ochranu rodin, a proto je bezpečnost na prvním místě.

## Podporované Verze

Opravy bezpečnostních chyb poskytujeme pro následující verze:

| Verze | Podporováno | Poznámka |
| ------- | ------------------ | ----- |
| 1.0.x | ✅ Ano | Současná stabilní verze |
| < 1.0 | ❌ Ne | Starší vývojové verze |

## Hlášení Zranitelností

Pokud objevíte bezpečnostní chybu, nahlaste nám ji prosím soukromě:

**Email:** robert.pesout@gmail.com (Róbert Pešout, BertSoftware)
**Doba odezvy:** Do 48 hodin.

**NEOTVÍREJTE** prosím veřejné GitHub Issue pro bezpečnostní chyby, dokud nejsou opraveny.

## Best Practices pro Uživatele

1.  Měňte si `SECRET_KEY` v `.env` pro produkční nasazení.
2.  Nikdy nevystavujte port 8000 veřejně do internetu bez SSL/TLS.
3.  Používejte silná hesla pro FamilyEye účty.

Děkujeme, že pomáháte udržet FamilyEye bezpečné! 🛡️
