"""
Converte cookies esportati dal browser nel formato auth_state.json di Playwright.

Supporta:
  - Netscape cookie file (.txt) — esportato da estensioni come "Cookie-Editor" di hotcleaner
  - JSON array — esportato da estensioni come "Cookie-Editor" di cgagnier

Uso:
  1. Esporta i cookies di subito.it dal browser
  2. Salva nella cartella SubitoBot (cookies_export.json o .txt)
  3. Esegui: python import_cookies.py [file]
"""

import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
AUTH_STATE_PATH = os.path.join(SCRIPT_DIR, "auth_state.json")

# Cerca input in ordine di priorita'
DEFAULT_INPUTS = [
    os.path.join(SCRIPT_DIR, "www.subito.it_cookies.txt"),
    os.path.join(SCRIPT_DIR, "cookies_export.json"),
    os.path.join(SCRIPT_DIR, "cookies_export.txt"),
]


def parse_netscape(input_path: str) -> list[dict]:
    """Parse Netscape HTTP Cookie File format."""
    pw_cookies = []
    with open(input_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 7:
                continue
            domain, _flag, path, secure, expires, name, value = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5], parts[6]
            cookie = {
                "name": name,
                "value": value,
                "domain": domain,
                "path": path,
                "secure": secure.upper() == "TRUE",
                "httpOnly": False,
                "sameSite": "Lax",
            }
            exp = int(expires)
            cookie["expires"] = float(exp) if exp > 0 else -1
            pw_cookies.append(cookie)
    return pw_cookies


def parse_json(input_path: str) -> list[dict]:
    """Parse JSON array di cookies (formato Cookie-Editor cgagnier)."""
    with open(input_path, encoding="utf-8") as f:
        raw = json.load(f)

    pw_cookies = []
    for c in raw:
        cookie = {
            "name": c.get("name", ""),
            "value": c.get("value", ""),
            "domain": c.get("domain", ""),
            "path": c.get("path", "/"),
            "secure": c.get("secure", False),
            "httpOnly": c.get("httpOnly", False),
            "sameSite": _map_samesite(c.get("sameSite", "Lax")),
        }
        if c.get("expirationDate"):
            cookie["expires"] = float(c["expirationDate"])
        elif c.get("expires"):
            cookie["expires"] = float(c["expires"])
        else:
            cookie["expires"] = -1
        pw_cookies.append(cookie)
    return pw_cookies


def _map_samesite(value) -> str:
    if isinstance(value, str):
        v = value.lower()
        if v in ("strict",):
            return "Strict"
        if v in ("none",):
            return "None"
        if v in ("lax",):
            return "Lax"
        if v in ("unspecified", "no_restriction"):
            return "None"
    return "Lax"


def detect_and_parse(input_path: str) -> list[dict]:
    """Rileva formato e parsa."""
    with open(input_path, encoding="utf-8") as f:
        first_line = f.readline().strip()

    if first_line.startswith("# Netscape") or first_line.startswith("# HTTP Cookie"):
        print(f"  Formato: Netscape cookie file")
        return parse_netscape(input_path)

    # Prova come Netscape se e' .txt
    if input_path.endswith(".txt"):
        print(f"  Formato: Netscape cookie file (.txt)")
        return parse_netscape(input_path)

    # Altrimenti JSON
    print(f"  Formato: JSON")
    return parse_json(input_path)


def main():
    # Trova file input
    if len(sys.argv) > 1:
        input_path = sys.argv[1]
    else:
        input_path = None
        for p in DEFAULT_INPUTS:
            if os.path.exists(p):
                input_path = p
                break

    if not input_path or not os.path.exists(input_path):
        print("Nessun file cookies trovato.")
        print()
        print("Esporta i cookies di subito.it e salvali come:")
        for p in DEFAULT_INPUTS:
            print(f"  {os.path.basename(p)}")
        print()
        print("Oppure specifica il percorso: python import_cookies.py <file>")
        sys.exit(1)

    print(f"Input: {os.path.basename(input_path)}")
    cookies = detect_and_parse(input_path)

    auth_state = {
        "cookies": cookies,
        "origins": [],
    }

    # Backup se esiste gia'
    if os.path.exists(AUTH_STATE_PATH):
        backup = AUTH_STATE_PATH + ".bak"
        os.replace(AUTH_STATE_PATH, backup)
        print(f"  Backup precedente: {backup}")

    with open(AUTH_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(auth_state, f, indent=2, ensure_ascii=False)

    subito_cookies = [c for c in cookies if "subito" in c.get("domain", "")]
    datadome = [c for c in cookies if "datadome" in c.get("name", "").lower()]
    print(f"  Cookies importati: {len(cookies)} totali, {len(subito_cookies)} di subito.it")
    if datadome:
        print(f"  DataDome cookie: presente (anti-bot bypass)")
    print(f"  Salvato in: {AUTH_STATE_PATH}")
    print()
    print("Ora puoi avviare: python send_messages.py")


if __name__ == "__main__":
    main()
