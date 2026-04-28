"""
Step 1 — Genera messaggi personalizzati per annunci Subito.it
Input:  Subito_scraper*.csv (CSV da Apify)
Output: listings_ready.csv
"""

import csv
import re
import random
import glob
import os

NO_AGENCY_VARIANTS = [
    "e nessun costo di agenzia, lavoriamo diversamente. Potrebbe interessarti?",
    "e non siamo un'agenzia, zero commissioni. Ti va di parlarne?",
    "e tra l'altro non chiediamo provvigioni, non siamo un'agenzia. Ti interessa?",
    "senza costi di intermediazione. Ci facciamo una chiamata?",
    "e nessuna provvigione, non lavoriamo come agenzia. Vuoi saperne di piu'?",
    "e per te nessun costo, non siamo un'agenzia. Ne parliamo?",
    "e zero spese di mediazione da parte nostra. Ti puo' interessare?",
    "e non applichiamo commissioni di nessun tipo. Che ne dici?",
]

BUSINESS_KEYWORDS = [
    "srl", "s.r.l", "snc", "sas", "s.a.s", "studio", "immobiliare",
    "affiliato", "tecnocasa", "re ", "group", "consulenza", "gestio",
    "agency", "agenzia", "real estate", "m&c", "m & c", "&",
    "casa", "property", "invest", "capital", "management",
    "amminitrazione", "amministrazione",
]

STREET_PREFIX_RE = re.compile(
    r'\b(via|viale|corso|piazza|piazzale|largo|salita|vico|vicolo|contrada|strada|lungomare)\b',
    re.IGNORECASE
)


def find_csv(script_dir: str) -> str:
    for pat in ["Subito_scraper*.csv", "Subito*.csv", "subito*.csv", "dataset_subito*.csv"]:
        files = glob.glob(os.path.join(script_dir, pat))
        candidates = [f for f in files if "listings_ready" not in f]
        if candidates:
            return max(candidates, key=os.path.getmtime)
    all_csv = glob.glob(os.path.join(script_dir, "*.csv"))
    candidates = [f for f in all_csv if "listings_ready" not in f]
    if candidates:
        return max(candidates, key=os.path.getmtime)
    raise FileNotFoundError(f"Nessun CSV trovato in {script_dir}")


def parse_title(title: str) -> dict:
    result = {"listing_type": "", "address": "", "zone": ""}
    if not title:
        return result
    m = STREET_PREFIX_RE.search(title)
    if m:
        result["listing_type"] = title[:m.start()].strip().rstrip(",").rstrip("-").strip()
        rest = title[m.start():]
        parts = re.split(r'\s*[-,]\s*', rest, maxsplit=1)
        result["address"] = parts[0].strip() if parts else ""
        result["zone"] = parts[1].strip() if len(parts) > 1 else ""
    else:
        parts = re.split(r'\s*[-,]\s*', title, maxsplit=1)
        result["listing_type"] = parts[0].strip() if parts else title
        result["zone"] = parts[1].strip() if len(parts) > 1 else ""
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
    name = extract_first_name(row.get("advertiser/name", ""))
    city = row.get("location/city", "").strip()

    if parsed["address"]:
        loc = parsed["address"]
    elif parsed["zone"]:
        loc = parsed["zone"]
    elif city:
        loc = city
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
    sig = "Mattia, Freedhome"

    parts = [opening]
    if price_str:
        parts.append(price_str)
    parts.append(f"{hook} {no_ag}")
    parts.append(sig)
    msg = "\n".join(parts)

    if len(msg) > 280 and price_str:
        parts = [opening, f"{hook} {no_ag}", sig]
        msg = "\n".join(parts)

    return msg, parsed, name, city


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

    processed = skipped_url = skipped_az = 0

    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()

        for row in rows:
            url = row.get("page_url", "").strip()
            if not url:
                skipped_url += 1
                continue
            if row.get("advertiser/type", "").strip().lower() == "azienda":
                skipped_az += 1
                continue

            msg, parsed, name, city = build_message(row)

            out = dict(row)
            out["url"] = url
            out["parsed_name"] = name
            out["parsed_type"] = parsed["listing_type"]
            out["parsed_address"] = parsed["address"]
            out["parsed_zone"] = parsed["zone"]
            out["parsed_city"] = city
            out["custom_message"] = msg
            out["status"] = "pending"
            writer.writerow(out)
            processed += 1

    print(f"Processati       : {processed}")
    if skipped_url:
        print(f"Saltati (no URL)  : {skipped_url}")
    if skipped_az:
        print(f"Saltati (azienda) : {skipped_az}")

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
