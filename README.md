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
| `upload_surfer.sh` | Upload dat na Surfer |

## Lokální spuštění
```bash
python3 -m http.server 8080
# http://localhost:8080/accounts.html
```

## Generování dat
```bash
python3 mastodon_cz_accounts.py --output .
```

## Nasazení na VPS

### Závislosti
```bash
pip3 install requests python-dateutil
npm install -g cloudron-surfer
```

### Nastavení .env
Vytvoř soubor `.env` v kořeni projektu:
```
MASTODON_TOKEN=tvuj_mastodon_token
GTS_TOKEN=tvuj_gts_token
SURFER_TOKEN=tvuj_surfer_token
```

- **MASTODON_TOKEN** — přístupový token z nastavení Mastodon účtu (Settings → Development → New application)
- **GTS_TOKEN** — token pro GoToSocial instanci
- **SURFER_TOKEN** — token z Cloudron Surfer (viz sekce Upload na Surfer)

## Cron

Automatické generování dat každý den ve 3:00:
```
0 3 * * * cd /opt/fedi_start && python3 mastodon_cz_accounts.py --output . && bash upload_surfer.sh
```

## Upload na Surfer

### Instalace
```bash
npm install -g cloudron-surfer
```

### Konfigurace
```bash
surfer config --server fedi.mamutovo.cz --token TOKEN
```

### Spuštění uploadu
```bash
bash upload_surfer.sh
```

### CLI — manuální upload
```bash
# Nahrát konkrétní soubor do kořene
surfer put -t $SURFER_TOKEN accounts.json /

# Nahrát více souborů najednou
surfer put -t $SURFER_TOKEN accounts.json accounts.csv /

# Nahrát celý adresář
surfer put -t $SURFER_TOKEN dist/ /

# Zobrazit obsah na serveru
surfer get

# Smazat soubor
surfer del /accounts.json
```

## Web

Stránka je dostupná na: https://fedi.mamutovo.cz
