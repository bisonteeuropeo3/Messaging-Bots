"""
Step 1 — Genera messaggi personalizzati per annunci Immobiliare.it
Input:  dataset_*.csv o Immobili*.csv (CSV da Apify)
Output: listings_ready.csv
"""

import csv
import re
import random
import glob
import os

NO_AGENCY_VARIANTS = [
    "e nessun costo di agenzia, lavoriamo diversamente. Volendo puoi anche attivare una protezione opzionale contro morosita', danni e con assistenza legale inclusa. Potrebbe interessarti?",
    "e non siamo un'agenzia, zero commissioni. Se vuoi, c'e' anche la possibilita' di aggiungere una copertura opzionale per morosita', danni e assistenza legale. Ti va di parlarne?",
    "e tra l'altro non chiediamo provvigioni, non siamo un'agenzia. Volendo, puoi attivare una tutela opzionale contro morosita' e danni, con assistenza legale. Ti interessa?",
    "senza costi di intermediazione. Se ti interessa, c'e' anche un'opzione di protezione contro morosita', danni e assistenza legale. Ci facciamo una chiamata?",
    "e nessuna provvigione, non lavoriamo come agenzia. Su richiesta possiamo offrirti anche una copertura opzionale su morosita', danni e questioni legali. Vuoi saperne di piu'?",
    "e per te nessun costo, non siamo un'agenzia. Volendo, puoi aggiungere una protezione opzionale che ti copre da morosita', danni e ti da' assistenza legale. Ne parliamo?",
    "e zero spese di mediazione da parte nostra. In piu', se ti interessa, puoi attivare una tutela opzionale contro morosita', danni e con supporto legale. Ti puo' interessare?",
    "e non applichiamo commissioni di nessun tipo. Se vuoi, c'e' anche la possibilita' di una protezione opzionale completa: morosita', danni e assistenza legale. Che ne dici?",
]

BUSINESS_KEYWORDS = [
    "srl", "s.r.l", "snc", "sas", "s.a.s", "studio", "immobiliare",
    "affiliato", "tecnocasa", "re ", "group", "consulenza", "gestio",
    "agency", "agenzia", "real estate", "m&c", "m & c", "&",
    "casa", "property", "invest", "capital", "management",
]

STREET_PREFIX_RE = re.compile(
    r'\b(via|viale|corso|piazza|piazzale|largo|salita|vico|vicolo|contrada|strada|lungomare|lungosavo)\b',
    re.IGNORECASE
)


def find_csv(script_dir: str) -> str:
    for pat in ["dataset_*.csv", "Immobili*.csv", "immobili*.csv"]:
        files = glob.glob(os.path.join(script_dir, pat))
        candidates = [f for f in files if "listings_ready" not in f]
        if candidates:
            return max(candidates, key=os.path.getmtime)
    all_csv = glob.glob(os.path.join(script_dir, "*.csv"))
    candidates = [f for f in all_csv
                  if "listings_ready" not in f
                  and "Subito" not in os.path.basename(f)]
    if candidates:
        return max(candidates, key=os.path.getmtime)
    raise FileNotFoundError(f"Nessun CSV trovato in {script_dir}")


def parse_title(title: str) -> dict:
    result = {"listing_type": "", "address": "", "zone": "", "city": ""}
    if not title:
        return result
    m = STREET_PREFIX_RE.search(title)
    if m:
        result["listing_type"] = title[:m.start()].strip().rstrip(",")
        rest = title[m.start():]
        parts = [p.strip() for p in rest.split(",")]
        result["address"] = parts[0] if parts else ""
        result["zone"] = parts[1] if len(parts) > 1 else ""
        result["city"] = parts[2] if len(parts) > 2 else ""
    else:
        parts = [p.strip() for p in title.split(",")]
        result["listing_type"] = parts[0] if parts else title
        result["zone"] = parts[1] if len(parts) > 1 else ""
        result["city"] = parts[2] if len(parts) > 2 else ""
    return result


def extract_first_name(display_name: str) -> str:
    if not display_name:
        return ""
    name = display_name.strip().rstrip(".")
    for kw in BUSINESS_KEYWORDS:
        if kw in name.lower():
            return ""
    tokens = name.split()
    if not tokens:
        return ""
    first = tokens[0].capitalize()
    return first if len(first) >= 2 else ""


def shorten_location(text: str, max_chars: int = 30) -> str:
    words = text.split()
    if words and words[-1].rstrip(",").isdigit():
        words = words[:-1]
    clean = " ".join(words)
    return clean if len(clean) <= max_chars else " ".join(words[:3])


def build_message(row: dict) -> tuple:
    parsed = parse_title(row.get("title", ""))
    name = extract_first_name(
        row.get("advertiser/supervisor/displayName", "")
        or row.get("advertiser/agency/displayName", "")
    )

    if parsed["address"]:
        loc = parsed["address"]
    elif parsed["zone"]:
        loc = parsed["zone"]
    elif parsed["city"]:
        loc = parsed["city"]
    else:
        loc = ""

    loc = shorten_location(loc)
    if STREET_PREFIX_RE.match(loc):
        loc_str = f"in {loc}"
    elif loc:
        loc_str = f"a {loc}"
    else:
        loc_str = ""

    if name:
        opening = f"Ciao {name}, ho visto il tuo annuncio {loc_str}."
    else:
        opening = f"Ciao, ho visto il tuo annuncio {loc_str}."
    opening = re.sub(r'\s+', ' ', opening).replace(" .", ".")

    price_str = ""
    try:
        pv = int(row.get("price/value", 0) or 0)
        if pv > 50:
            price_str = f"Il prezzo ({pv} euro/mese) e' interessante per la zona."
    except (ValueError, TypeError):
        pass

    hook = "Abbiamo richieste di inquilini verificati per quella zona —"
    no_ag = random.choice(NO_AGENCY_VARIANTS)
    sig = "Luigi, FreedHome"

    parts = [opening]
    if price_str:
        parts.append(price_str)
    parts.append(f"{hook} {no_ag}")
    parts.append(sig)
    msg = "\n".join(parts)

    return msg, parsed, name


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = find_csv(script_dir)
    output_path = os.path.join(script_dir, "listings_ready.csv")

    print(f"Input : {os.path.basename(input_path)}")

    with open(input_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    extra = ["url", "parsed_name", "parsed_type", "parsed_address",
             "parsed_zone", "parsed_city", "custom_message", "status"]
    out_fields = fieldnames + extra

    processed = skipped = 0

    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()

        for row in rows:
            url = row.get("directLink", "").strip()
            if not url:
                skipped += 1
                continue

            msg, parsed, name = build_message(row)

            out = dict(row)
            out["url"] = url
            out["parsed_name"] = name
            out["parsed_type"] = parsed["listing_type"]
            out["parsed_address"] = parsed["address"]
            out["parsed_zone"] = parsed["zone"]
            out["parsed_city"] = parsed["city"]
            out["custom_message"] = msg
            out["status"] = "pending"
            writer.writerow(out)
            processed += 1

    print(f"Processati      : {processed}")
    if skipped:
        print(f"Saltati (no URL) : {skipped}")

    print(f"\nAnteprima 3 messaggi:")
    print("-" * 60)
    with open(output_path, encoding="utf-8-sig") as f:
        for i, row in enumerate(csv.DictReader(f)):
            if i >= 3:
                break
            print(f"[{i+1}] {row['title'][:60]}")
            print(f"     Nome: {row['parsed_name'] or '(nessuno)'}")
            for line in row["custom_message"].split("\n"):
                print(f"     {line}")
            print()


if __name__ == "__main__":
    main()
