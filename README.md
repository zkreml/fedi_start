# fedi_start

Onboarding systém pro nové uživatele Mastodonu (CZ/SK komunita).

## Soubory

| Soubor | Popis |
|---|---|
| `start.html` | Úvodní onboarding stránka |
| `accounts.html` | Interaktivní seznam CZ účtů s filtry |
| `accounts.json` | Data účtů (generováno skriptem) |
| `starter-general.csv` | Starter pack pro import do Mastodonu |
| `mastodon_cz_accounts.py` | Automatický sběr CZ/SK účtů |

## Lokální spuštění
```bash
python3 -m http.server 8080
# http://localhost:8080/accounts.html
```

## Generování dat
```bash
python3 mastodon_cz_accounts.py --output .
```

## Cron
```
0 3 * * * /usr/bin/python3 /opt/fedi_start/mastodon_cz_accounts.py --output /var/www/fedi_start/
```
