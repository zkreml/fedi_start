# fedi_start

Onboarding průvodce pro [Mamutovo.cz](https://mamutovo.cz) – pomáhá nováčkům začít na Fediverse.

- **Web:** https://fedi.mamutovo.cz
- **Repo:** https://git.arch-linux.cz/Mamutovo/fedi_start
- **Účet:** [@archlinuxcz@mamutovo.cz](https://mamutovo.cz/@archlinuxcz)

---

## Obsah projektu

| Soubor | Popis |
|---|---|
| `index.html` | Hlavní stránka |
| `start.html` | Krok za krokem onboarding pro nováčky |
| `basics.html` | Základy Mastodonu |
| `accounts.html` | Interaktivní seznam CZ/SK účtů s filtry |
| `apps.html` | Doporučené aplikace (Android / iOS / Web / Desktop) |
| `accounts.json` | Data účtů (generováno skriptem, nahrává se na Surfer) |
| `accounts.csv` | Totéž v CSV (nahrává se na Surfer) |
| `manual_accounts.csv` | Ručně přidané účty (GTS instance a výjimky) |
| `starter-general.csv` | Starter pack – obecný – pro import do Mastodonu |
| `starter-tech.csv` | Starter pack – tech – pro import do Mastodonu |
| `mastodon_cz_accounts.py` | Hlavní skript – scraping CZ/SK účtů |
| `upload_surfer.sh` | Upload `accounts.json` a `accounts.csv` na Cloudron Surfer |

---

## Lokální vývoj

```bash
# Spustí lokální HTTP server
python3 -m http.server 8080
# Otevři v prohlížeči: http://localhost:8080/
```

---

## Skript `mastodon_cz_accounts.py`

Sbírá CZ/SK účty z Mastodonu a GoToSocial instancí, filtruje je a ukládá do `accounts.json` a `accounts.csv`.

### Jak funguje sběr dat

1. Pro každou instanci v `QUERY_INSTANCES` volá `/api/v1/directory` (veřejné Mastodon API).
2. Načte `manual_accounts.csv` a dohledá každý účet přes `/api/v1/accounts/lookup`.
3. Sloučí obojí, odstraní duplicity, seřadí a ořízne na `TOP_N` (výchozí 250) automatických účtů + všechny manuální.

### Kritéria pro zařazení (automatické účty)

| Podmínka | Hodnota |
|---|---|
| `discoverable = true` | Uživatel chce být nalezen |
| Aktivní za posledních | 90 dní |
| Min. počet příspěvků | 10 |
| Min. počet sledujících | 10 |

**Manuálně přidané účty** (`manual_accounts.csv`) jsou vždy zahrnuty bez ohledu na tato kritéria.

### Sledované instance

CZ/SK instance jsou v konstantě `QUERY_INSTANCES` v hlavičce skriptu:

```
mastodonczech.cz, cztwitter.cz, witter.cz, mastodon.pirati.cz,
f.cz, lgbtcz.social, boskovice.social, mamutovo.cz,
gts.arch-linux.cz, kompost.cz, spondr.cz, skorpil.cz,
ajtaci.club, toot.whatever.cz
```

### Spuštění

```bash
# Základní spuštění (výstup do aktuálního adresáře)
python3 mastodon_cz_accounts.py

# Výstup do konkrétního adresáře
python3 mastodon_cz_accounts.py --output /var/www/start/

# Omezení počtu účtů
python3 mastodon_cz_accounts.py --top 100

# Ladění
python3 mastodon_cz_accounts.py --debug
```

---

## Konfigurace `.env`

Vytvoř soubor `.env` v kořeni projektu (je v `.gitignore`, nikdy ho necommituj):

```ini
# Volitelný Mastodon token (pro vyšší rate limity)
MASTODON_TOKEN=tvuj_mastodon_token

# GoToSocial tokeny per-instance (viz sekce níže)
GTS_TOKEN_GTS_ARCH_LINUX_CZ=tvuj_token_zde
GTS_TOKEN_DALSI_INSTANCE_CZ=dalsi_token

# Surfer token pro upload na web
SURFER_TOKEN=tvuj_surfer_token

# Volitelně: jiný Surfer server (výchozí je fedi.mamutovo.cz)
# SURFER_SERVER=cloud.oscloud.cz
```

### Proměnné prostředí

| Proměnná | Povinná | Popis |
|---|---|---|
| `MASTODON_TOKEN` | ne | Token pro Mastodon API (vyšší rate limity) |
| `GTS_TOKEN_<DOMAIN>` | pro GTS instance | Read token per GoToSocial instance |
| `SURFER_TOKEN` | pro upload | Token z Cloudron Surfer |
| `SURFER_SERVER` | ne | Server Surferu, pokud není výchozí |

Název proměnné pro GTS token se tvoří z domény – tečky a pomlčky se nahradí podtržítkem a vše se převede na VELKÁ PÍSMENA:

```
gts.arch-linux.cz  →  GTS_TOKEN_GTS_ARCH_LINUX_CZ
shimon.gts.example →  GTS_TOKEN_SHIMON_GTS_EXAMPLE
```

---

## GoToSocial instance – jak získat read token

GoToSocial nepodporuje veřejné `/api/v1/directory`, takže každá GTS instance potřebuje vlastní read token. Postup:

### 1. Přihlášení a vytvoření aplikace

Přihlas se na dané GTS instanci a jdi do **Settings → Applications → New application**.

Vyplň:
- **Název aplikace:** např. `fedi_start scraper`
- **Scopes:** zaškrtni pouze `read`
- Ostatní pole nech prázdná nebo vyplň libovolně

Uložíš aplikaci a GTS ti vygeneruje `client_id` a `client_secret`. Poznamenej si obojí.

### 2. Získání authorization code

Otevři v prohlížeči tuto URL (nahraď `INSTANCI.CZ` a `CLIENT_ID`):

```
https://INSTANCI.CZ/oauth/authorize?client_id=CLIENT_ID&redirect_uri=urn:ietf:wg:oauth:2.0:oob&response_type=code&scope=read
```

Přihlášený prohlížeč zobrazí stránku s kódem – zkopíruj ho (jednorázový, platí jen chvíli).

### 3. Výměna code za access token

```bash
curl -X POST "https://INSTANCI.CZ/oauth/token" \
  -d "client_id=CLIENT_ID" \
  -d "client_secret=CLIENT_SECRET" \
  -d "redirect_uri=urn:ietf:wg:oauth:2.0:oob" \
  -d "grant_type=authorization_code" \
  -d "code=AUTHORIZATION_CODE" \
  -d "scope=read"
```

V odpovědi dostaneš JSON s `access_token`.

### 4. Přidání tokenu do `.env`

```ini
GTS_TOKEN_GTS_ARCH_LINUX_CZ=ziskany_access_token
```

### 5. Ověření

```bash
curl -H "Authorization: Bearer TVUJ_TOKEN" "https://INSTANCI.CZ/api/v1/accounts/verify_credentials"
```

Pokud vrátí JSON s tvým účtem, token funguje.

---

## Přidání nového účtu

### Mastodon instance

Uživatel se zobrazí automaticky, pokud má v nastavení zapnuté:

> **Settings → Privacy → Appearance in search engines** (nebo česky „Zobrazovat profil ve vyhledávacích algoritmech")

A splňuje kritéria výše (aktivita, min. počet příspěvků atd.).

Pokud chceš účet přidat ručně bez ohledu na kritéria, přidej ho do `manual_accounts.csv`:

```csv
handle@instance.cz,true,false,
```

### GoToSocial instance

GTS nemá veřejný adresář, proto:

1. Získej read token (viz postup výše).
2. Přidej `GTS_TOKEN_<DOMAIN>=token` do `.env`.
3. Přidej konkrétní účty do `manual_accounts.csv` (GTS adresář je přístupný s tokenem, ale pro jistotu je lepší přidat je ručně).
4. Přidej instanci do `QUERY_INSTANCES` v `mastodon_cz_accounts.py`.

---

## Nasazení na VPS

Projekt běží na VPS Hetzner v `/opt/fedi_start/`.

### Závislosti

```bash
# Python (stdlib only, žádné externí balíčky)
python3 --version  # 3.10+

# Node.js – Cloudron Surfer CLI
npm install -g cloudron-surfer
```

### Nastavení na serveru

```bash
git clone https://git.arch-linux.cz/Mamutovo/fedi_start /opt/fedi_start
cd /opt/fedi_start
cp .env.example .env  # nebo vytvoř .env ručně
# Vyplň tokeny v .env
```

### Cron

Automatická aktualizace 4× denně:

```
0 6,12,18,0 * * * cd /opt/fedi_start && python3 mastodon_cz_accounts.py --output . && bash upload_surfer.sh >> /var/log/fedi_start.log 2>&1
```

---

## Upload na Surfer

[Cloudron Surfer](https://cloudron.io/store/io.cloudron.surfer.html) je jednoduchý statický file hosting.

### Ruční spuštění uploadu

```bash
bash upload_surfer.sh
```

Skript načte `SURFER_TOKEN` z `.env` a nahraje `accounts.json` + `accounts.csv` do kořene Surfer serveru.

### Manuální Surfer příkazy

```bash
# Nahrát konkrétní soubory
surfer put -t $SURFER_TOKEN accounts.json accounts.csv /

# Zobrazit obsah na serveru
surfer get

# Smazat soubor
surfer del /accounts.json
```

---

## Struktura dat `accounts.json`

Každý záznam v poli `accounts` obsahuje:

```json
{
  "handle":         "uzivatel@instance.cz",
  "display_name":   "Zobrazované jméno",
  "note":           "Bio uživatele",
  "followers":      123,
  "following":      45,
  "statuses":       678,
  "last_active":    "2024-03-15",
  "avatar":         "https://...",
  "url":            "https://instance.cz/@uzivatel",
  "fields":         [...],
  "tags":           ["linux", "opensource"]
}
```

---

## Přispívání

Pull requesty vítány. Repo: https://git.arch-linux.cz/Mamutovo/fedi_start
