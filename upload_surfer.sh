#!/usr/bin/env bash
# upload_surfer.sh — nahraje accounts.json a accounts.csv na Surfer
#
# NASTAVENÍ TOKENU:
#   1. Přihlas se do svého Surfer instance (např. https://cloud.oscloud.cz)
#   2. Jdi do Settings → API Tokens a vygeneruj nový token
#   3. Přidej do souboru .env řádek:
#        SURFER_TOKEN=tvuj_token_zde
#   4. Volitelně nastav SURFER_SERVER, pokud nepoužíváš výchozí server:
#        SURFER_SERVER=cloud.oscloud.cz

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"

# Načti proměnné z .env
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Chyba: soubor .env nenalezen ($ENV_FILE)" >&2
  exit 1
fi

set -a
# shellcheck source=.env
source "$ENV_FILE"
set +a

# Ověř, že token existuje
if [[ -z "${SURFER_TOKEN:-}" ]]; then
  echo "Chyba: SURFER_TOKEN není nastaven v .env" >&2
  exit 1
fi

# Soubory k nahrání
FILES=("$SCRIPT_DIR/accounts.json" "$SCRIPT_DIR/accounts.csv")

for f in "${FILES[@]}"; do
  if [[ ! -f "$f" ]]; then
    echo "Varování: soubor nenalezen, přeskakuji: $f" >&2
  fi
done

echo "Nahrávám na Surfer..."

SURFER_ARGS=(-t "$SURFER_TOKEN")
if [[ -n "${SURFER_SERVER:-}" ]]; then
  SURFER_ARGS+=(-s "$SURFER_SERVER")
fi

surfer put "${SURFER_ARGS[@]}" accounts.json accounts.csv /

echo "Hotovo."
