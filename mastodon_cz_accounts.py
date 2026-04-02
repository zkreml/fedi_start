#!/usr/bin/env python3
"""
mastodon_cz_accounts.py
Sbírá CZ/SK účty z Mastodonu přes /api/v1/directory?language=cs
– stejná logika jako mstdn.cz od @adent.

Kritéria:
  - discoverable=true (uživatel chce být nalezen)
  - jazyk příspěvků nastaven na cs nebo sk
  - aktivní za posledních 30 dní
  - min. 10 příspěvků

Použití:
  python3 mastodon_cz_accounts.py
  python3 mastodon_cz_accounts.py --output /var/www/start/

Cron (každý den v 3:00):
  0 3 * * * /usr/bin/python3 /opt/mastodon-start/mastodon_cz_accounts.py --output /var/www/start/ >> /var/log/mastodon-start.log 2>&1
"""

import json, csv, time, re, argparse, logging, os
from datetime import datetime, timezone, timedelta
from pathlib import Path
import urllib.request, urllib.error, urllib.parse

def _load_tokens():
    tokens = {}
    env_path = Path(__file__).parent / ".env"
    env_lines = env_path.read_text().splitlines() if env_path.exists() else []
    for key in ("MASTODON_TOKEN", "GTS_TOKEN"):
        val = os.environ.get(key)
        if not val:
            for line in env_lines:
                line = line.strip()
                if line.startswith(f"{key}="):
                    val = line.split("=", 1)[1].strip()
                    break
        if val:
            tokens[key] = val.strip()
    # fallback: raw token value (legacy .env bez klíče)
    if "MASTODON_TOKEN" not in tokens:
        for line in env_lines:
            line = line.strip()
            if line and not line.startswith("#") and "=" not in line:
                tokens["MASTODON_TOKEN"] = line
                break
    return tokens

_TOKENS = _load_tokens()
MASTODON_TOKEN = _TOKENS.get("MASTODON_TOKEN")
GTS_TOKEN      = _TOKENS.get("GTS_TOKEN")

def _token_for(instance: str) -> str | None:
    """Vrátí GTS_TOKEN pro GoToSocial instance (obsahují 'gts.' v doméně), jinak MASTODON_TOKEN."""
    if GTS_TOKEN and "gts." in instance:
        return GTS_TOKEN
    return MASTODON_TOKEN

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

# ── CONFIG ────────────────────────────────────
QUERY_INSTANCES = [
    # CZ/SK instance – bereme všechny uživatele (bez language filtru)
    "mastodonczech.cz",   # 713 CZ uživatelů
    "cztwitter.cz",       # 229 CZ uživatelů
    "witter.cz",          # 212 CZ uživatelů
    "mastodon.pirati.cz", # 52 CZ uživatelů
    "f.cz",               # 40 CZ uživatelů
    "lgbtcz.social",      # 7 CZ uživatelů
    "boskovice.social",   # 5 CZ uživatelů
    "mamutovo.cz",
    "gts.arch-linux.cz",
    "kompost.cz",
    "spondr.cz",
    "skorpil.cz",
    "ajtaci.club",
]

MIN_STATUSES      = 10
MIN_FOLLOWERS     = 10
MAX_DAYS_INACTIVE = 90
TOP_N             = 200
RATE_LIMIT_DELAY  = 1.2
PAGE_LIMIT        = 80
MAX_PAGES         = 10

# ── HTTP ──────────────────────────────────────
def api_get(url, timeout=15, token=None):
    headers = {"User-Agent": "MamutovoStarterBot/1.0 (+https://mamutovo.cz)"}
    tok = token if token is not None else MASTODON_TOKEN
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 429:
            log.warning("Rate limit – čekám 60s"); time.sleep(60)
        elif e.code not in (404, 410):
            log.debug(f"HTTP {e.code} {url}")
        return None
    except Exception as e:
        log.debug(f"Chyba {url}: {e}"); return None

# ── SBĚR ─────────────────────────────────────
def _fetch_small_instance(instance, seen_handles, all_accounts):
    """Malé CZ/SK instance: bereme všechny uživatele z directory."""
    log.info(f"directory {instance} ...")
    token = _token_for(instance)
    page = 0
    while page < MAX_PAGES:
        offset = page * PAGE_LIMIT
        url = (f"https://{instance}/api/v1/directory"
               f"?limit={PAGE_LIMIT}&local=true&offset={offset}")
        batch = api_get(url, token=token)
        if not batch or not isinstance(batch, list):
            break
        added = 0
        for acc in batch:
            acct = acc.get("acct", "")
            handle = acct if "@" in acct else f"{acct}@{instance}"
            if handle.lower() in seen_handles:
                continue
            seen_handles.add(handle.lower())
            acc["_handle"] = handle
            acc["_source_instance"] = instance
            all_accounts.append(acc)
            added += 1
        log.debug(f"  {instance} offset={offset}: {added} nových")
        if len(batch) < PAGE_LIMIT:
            break
        page += 1
        time.sleep(RATE_LIMIT_DELAY)

def fetch_all_accounts():
    seen_handles = set()
    all_accounts = []
    for instance in QUERY_INSTANCES:
        _fetch_small_instance(instance, seen_handles, all_accounts)
        log.info(f"  → celkem {len(all_accounts)} unikátních účtů")
        time.sleep(RATE_LIMIT_DELAY)
    log.info(f"Sběr hotov: {len(all_accounts)} unikátních účtů")
    return all_accounts

def load_manual_accounts(seen_handles=None):
    """Načte manual_accounts.csv a dohledá každý účet přes /api/v1/accounts/lookup."""
    csv_path = Path(__file__).parent / "manual_accounts.csv"
    if not csv_path.exists():
        log.info("manual_accounts.csv nenalezen, přeskakuji")
        return []
    if seen_handles is None:
        seen_handles = set()
    accounts = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.reader(f):
            if not row:
                continue
            entry = row[0].strip()
            if not entry or "@" not in entry:
                continue
            handle_part, instance = entry.rsplit("@", 1)
            handle = f"{handle_part}@{instance}"
            if handle.lower() in seen_handles:
                log.debug(f"  {handle} již v seznamu, přeskakuji")
                continue
            url = f"https://{instance}/api/v1/accounts/lookup?acct={urllib.parse.quote(handle_part)}"
            token = _token_for(instance)
            if handle.lower() == "archos@gts.arch-linux.cz":
                tok_preview = (token[:8] + "...") if token else None
                log.info(f"[DEBUG archos] token={tok_preview} url={url}")
            acc = api_get(url, token=token)
            if handle.lower() == "archos@gts.arch-linux.cz":
                log.info(f"[DEBUG archos] api_get vrátil: {None if not acc else 'dict s ' + str(list(acc.keys())[:5])}")
            if not acc or not isinstance(acc, dict):
                log.warning(f"  {handle}: lookup selhal")
                continue
            seen_handles.add(handle.lower())
            acc["_handle"] = handle
            acc["_source_instance"] = instance
            accounts.append(acc)
            log.debug(f"  {handle}: OK ({acc.get('followers_count', 0)} followers)")
            time.sleep(RATE_LIMIT_DELAY)
    log.info(f"Manuální účty: {len(accounts)} načteno z {csv_path.name}")
    return accounts

# ── FILTRY ────────────────────────────────────
def passes_quality(acc):
    if acc.get("suspended") or acc.get("limited"):
        return False
    if (acc.get("statuses_count")  or 0) < MIN_STATUSES:  return False
    if (acc.get("followers_count") or 0) < MIN_FOLLOWERS: return False
    last = acc.get("last_status_at")
    if not last:
        return False
    try:
        dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
        if dt < datetime.now(timezone.utc) - timedelta(days=MAX_DAYS_INACTIVE):
            return False
    except Exception:
        pass
    return True

# ── SCORING ───────────────────────────────────
def score(acc):
    followers = acc.get("followers_count", 0) or 0
    statuses  = acc.get("statuses_count",  0) or 0
    following = acc.get("following_count", 1) or 1
    f = min(40, int(40 * min(followers, 2000) / 2000))
    a = min(30, int(30 * min(statuses,  2000) / 2000))
    r = min(20, int(min(followers / max(following, 1), 4) * 5))
    handle = acc.get("_handle", "")
    instance = handle.split("@")[-1] if "@" in handle else ""
    b = 10 if any(x in instance for x in ("mamutovo", "czech")) else 0
    return min(100, f + a + r + b)

# ── KATEGORIE ─────────────────────────────────
CATEGORIES = {
    "tech":    ["linux", "python", "programov", "software", "opensource", "developer", "sysadmin", "git"],
    "foto":    ["fotografi", "foto", "photograph", "objektiv", "kamera"],
    "veda":    ["věda", "fyzika", "biologi", "astronom", "výzkum", "science", "matematik"],
    "kultura": ["knihy", "literatura", "film", "hudba", "divadlo", "umění"],
    "gaming":  ["gaming", "hry", "videohry", "steam", "gamer"],
    "zpravy":  ["novinář", "zprávy", "politik", "média", "journalist"],
}

def categorize(acc):
    text = re.sub(r"<[^>]+>", " ", acc.get("note", "") or "").lower()
    text += " " + (acc.get("display_name", "") or "").lower()
    for cat, kws in CATEGORIES.items():
        if any(kw in text for kw in kws):
            return cat
    return "ostatni"

def extract_tags(acc):
    text = re.sub(r"<[^>]+>", " ", acc.get("note", "") or "").lower()
    found = []
    for kws in CATEGORIES.values():
        for kw in kws:
            if kw in text and kw not in found and len(kw) > 3:
                found.append(kw.strip())
    return found[:4]

# ── VÝSTUP ────────────────────────────────────
def build_output(raw):
    results = []
    for acc in raw:
        if not passes_quality(acc):
            continue
        handle = acc.get("_handle", acc.get("acct", ""))
        bio = re.sub(r"<[^>]+>", " ", acc.get("note", "") or "").strip()
        results.append({
            "name":        acc.get("display_name") or acc.get("username", ""),
            "handle":      handle,
            "bio":         bio[:220],
            "avatar":      acc.get("avatar", ""),
            "followers":   acc.get("followers_count", 0),
            "statuses":    acc.get("statuses_count",  0),
            "score":       score(acc),
            "tags":        extract_tags(acc),
            "category":    categorize(acc),
            "last_active": acc.get("last_status_at", ""),
            "url":         acc.get("url", ""),
        })
    seen = set()
    unique = []
    for r in sorted(results, key=lambda x: x["followers"], reverse=True):
        if r["handle"].lower() not in seen:
            seen.add(r["handle"].lower())
            unique.append(r)
    return unique[:TOP_N]

def write_json(accounts, output_dir):
    data = {"generated_at": datetime.now(timezone.utc).isoformat(), "count": len(accounts), "accounts": accounts}
    p = output_dir / "accounts.json"
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    log.info(f"JSON: {p} ({len(accounts)} účtů)")

def write_csv(accounts, output_dir):
    p = output_dir / "accounts.csv"
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Account address", "Show boosts"])
        for a in accounts:
            w.writerow([a["handle"], "true"])
    log.info(f"CSV:  {p}")

# ── MAIN ──────────────────────────────────────
def main():
    global TOP_N
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=".", help="Výstupní adresář")
    parser.add_argument("--top",    default=TOP_N, type=int)
    parser.add_argument("--debug",  action="store_true")
    args = parser.parse_args()
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    TOP_N = args.top
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    log.info(f"Startuji – {len(QUERY_INSTANCES)} instancí")
    raw = fetch_all_accounts()
    seen_handles = {acc["_handle"].lower() for acc in raw}
    raw += load_manual_accounts(seen_handles)
    accounts = build_output(raw)
    if not accounts:
        log.error("Žádné účty! Zkontroluj připojení.")
        return 1
    log.info(f"Po filtraci: {len(accounts)} účtů")
    write_json(accounts, output_dir)
    write_csv(accounts, output_dir)
    log.info("Hotovo.")
    return 0

if __name__ == "__main__":
    exit(main())
