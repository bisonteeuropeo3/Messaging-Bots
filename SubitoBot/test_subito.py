"""
Test diagnostico per il flow di send_message su subito.it.

Apre un browser reale, prova diversi scenari e valida che i selettori funzionino.
Usa --url per testare un URL specifico, altrimenti testa scenari comuni.

Uso:
  python test_subito.py                          # test completo
  python test_subito.py --url <URL>              # test su URL specifico
  python test_subito.py --selectors-only         # solo test selettori (no invio)
"""

import os
import sys
import time
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
IMMOBILIARE_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "ImmobiliareBot")
sys.path.insert(0, IMMOBILIARE_DIR)

import yaml
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError

from platforms.subito import (
    Subito, CONTACT_BUTTON_SELECTORS, TEXTAREA_SELECTORS,
    SEND_BUTTON_SELECTORS, REMOVED_LISTING_INDICATORS,
)
from core.browser import (
    get_launch_args, create_context, accept_cookies, save_snapshot,
)


def load_config():
    path = os.path.join(SCRIPT_DIR, "config.yaml")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


# URL di test: un annuncio probabilmente venduto/rimosso e uno attivo
TEST_URLS = {
    "removed": "https://www.subito.it/appartamenti/3-locali-arredato-milano-641673787.htm",
    "active": None,  # verrà preso dal CSV se disponibile
}


def get_active_url():
    """Prendi un URL attivo dal CSV se disponibile."""
    csv_path = os.path.join(SCRIPT_DIR, "listings_ready.csv")
    if not os.path.exists(csv_path):
        return None
    import csv
    with open(csv_path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            url = row.get("url", "").strip()
            status = row.get("status", "").strip()
            if url and status == "pending":
                return url
    return None


def test_page_load(page, url, config):
    """Test 1: La pagina si carica correttamente?"""
    print(f"\n{'='*60}")
    print(f"TEST: Caricamento pagina")
    print(f"  URL: {url}")

    start = time.time()
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=25000)
    except PWTimeoutError:
        print(f"  FAIL: domcontentloaded timeout dopo 25s")
        return False
    except Exception as e:
        print(f"  FAIL: {e}")
        return False

    dom_time = time.time() - start
    print(f"  domcontentloaded: {dom_time:.1f}s")

    # networkidle — non bloccante
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
        idle_time = time.time() - start
        print(f"  networkidle: {idle_time:.1f}s")
    except PWTimeoutError:
        elapsed = time.time() - start
        print(f"  networkidle: timeout dopo {elapsed:.1f}s (proseguo comunque)")

    time.sleep(2)
    accept_cookies(page)
    print(f"  OK: pagina caricata")
    return True


def test_removed_detection(page, platform):
    """Test 2: Rileva annunci rimossi/venduti?"""
    print(f"\n{'='*60}")
    print(f"TEST: Rilevamento annuncio rimosso")

    is_removed = platform.detect_removed(page)
    if is_removed:
        print(f"  OK: annuncio rimosso rilevato correttamente")
    else:
        print(f"  INFO: annuncio NON rimosso (potrebbe essere ancora attivo)")

    # Mostra quali indicatori matchano
    for sel in REMOVED_LISTING_INDICATORS:
        try:
            visible = page.locator(sel).first.is_visible(timeout=1000)
            if visible:
                print(f"    match: {sel}")
        except Exception:
            pass

    return is_removed


def test_block_detection(page, platform):
    """Test 3: Rileva blocchi anti-bot?"""
    print(f"\n{'='*60}")
    print(f"TEST: Rilevamento blocco anti-bot")

    is_blocked = platform.detect_block(page)
    if is_blocked:
        print(f"  ATTENZIONE: blocco anti-bot rilevato!")
    else:
        print(f"  OK: nessun blocco rilevato")
    return is_blocked


def test_contact_button(page):
    """Test 4: Il bottone Contatta è visibile?"""
    print(f"\n{'='*60}")
    print(f"TEST: Ricerca bottone Contatta")

    # Simula scroll come fa il bot
    from core.browser import human_scroll
    for _ in range(5):
        human_scroll(page)
        time.sleep(0.5)
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(2)
    page.evaluate("window.scrollBy(0, -300)")
    time.sleep(1)

    # Aspetta idratazione React
    try:
        page.wait_for_function(
            "() => !document.querySelector('[class*=\"skeleton\"][class*=\"themed\"]')",
            timeout=10000,
        )
    except Exception:
        pass

    found = None
    for sel in CONTACT_BUTTON_SELECTORS:
        try:
            btns = page.locator(sel)
            count = btns.count()
            if count > 0:
                for i in range(count):
                    btn = btns.nth(i)
                    try:
                        btn.scroll_into_view_if_needed(timeout=3000)
                        if btn.is_visible(timeout=2000):
                            text = btn.inner_text()
                            print(f"  TROVATO: '{text}' con selettore: {sel}")
                            found = btn
                            break
                    except Exception:
                        continue
            if found:
                break
        except Exception:
            continue

    if not found:
        print(f"  FAIL: bottone Contatta non trovato con nessun selettore")

        # Diagnostica: cerca tutti i bottoni visibili
        print(f"\n  Diagnostica — tutti i bottoni visibili:")
        all_btns = page.locator("button:visible, a[role='button']:visible")
        for i in range(min(all_btns.count(), 15)):
            try:
                btn = all_btns.nth(i)
                text = btn.inner_text().strip()[:50]
                classes = btn.get_attribute("class") or ""
                if text:
                    print(f"    [{i}] '{text}' class={classes[:60]}")
            except Exception:
                pass

        # Cerca link con testo "contatta" in qualsiasi caso
        print(f"\n  Diagnostica — link/bottoni con testo contatto:")
        contact_els = page.locator(
            "button:visible, a:visible"
        )
        for i in range(contact_els.count()):
            try:
                el = contact_els.nth(i)
                text = el.inner_text().strip().lower()
                if any(kw in text for kw in ["contatt", "scrivi", "messag", "chatt", "rispondi"]):
                    tag = el.evaluate("e => e.tagName")
                    classes = el.get_attribute("class") or ""
                    href = el.get_attribute("href") or ""
                    print(f"    {tag} '{el.inner_text().strip()[:40]}' class={classes[:50]} href={href[:50]}")
            except Exception:
                pass

        save_snapshot(page, "test_no_contact_btn")

    return found


def test_full_flow(page, url, config, platform):
    """Test completo del flow send_message (dry run - non invia realmente)."""
    print(f"\n{'='*60}")
    print(f"TEST COMPLETO: flow send_message")
    print(f"  URL: {url}")

    status, reason = platform.send_message(page, url, "Test messaggio di prova - non inviare", config)
    print(f"  Risultato: status={status}, reason={reason}")
    return status, reason


def main():
    parser = argparse.ArgumentParser(description="Test diagnostico SubitoBot")
    parser.add_argument("--url", type=str, help="URL specifico da testare")
    parser.add_argument("--selectors-only", action="store_true",
                        help="Testa solo i selettori, senza inviare")
    args = parser.parse_args()

    config = load_config()
    platform = Subito()
    auth_path = os.path.join(SCRIPT_DIR, "auth_state.json")

    if not os.path.exists(auth_path):
        print("ERRORE: auth_state.json non trovato. Esegui prima send_messages.py per il login.")
        sys.exit(1)

    results = {}

    with sync_playwright() as p:
        launch_args = get_launch_args(config)
        browser = p.chromium.launch(**launch_args)
        context = create_context(browser, config, auth_path)
        page = context.new_page()

        # Verifica login
        print("Verifica login...")
        if not platform.is_logged_in(page):
            print("ERRORE: sessione scaduta. Ri-esegui send_messages.py per ri-autenticarti.")
            context.close()
            browser.close()
            sys.exit(1)
        print("Login OK\n")

        urls_to_test = []

        if args.url:
            urls_to_test = [("custom", args.url)]
        else:
            urls_to_test.append(("removed", TEST_URLS["removed"]))
            active = get_active_url()
            if active:
                urls_to_test.append(("active", active))
            else:
                print("AVVISO: nessun URL attivo trovato in listings_ready.csv")

        for label, url in urls_to_test:
            print(f"\n{'#'*60}")
            print(f"# SCENARIO: {label}")
            print(f"# URL: {url}")
            print(f"{'#'*60}")

            scenario_results = {}

            # Test 1: Caricamento
            loaded = test_page_load(page, url, config)
            scenario_results["page_load"] = loaded

            if not loaded:
                results[label] = scenario_results
                continue

            # Test 2: Annuncio rimosso?
            is_removed = test_removed_detection(page, platform)
            scenario_results["is_removed"] = is_removed

            if is_removed:
                print(f"\n  Annuncio rimosso — skip test selettori")
                results[label] = scenario_results
                continue

            # Test 3: Blocco?
            is_blocked = test_block_detection(page, platform)
            scenario_results["is_blocked"] = is_blocked

            if is_blocked:
                results[label] = scenario_results
                continue

            # Test 4: Bottone Contatta
            contact_btn = test_contact_button(page)
            scenario_results["contact_button_found"] = contact_btn is not None

            results[label] = scenario_results

        context.close()
        browser.close()

    # Riepilogo
    print(f"\n\n{'='*60}")
    print(f"RIEPILOGO TEST")
    print(f"{'='*60}")
    all_pass = True
    for label, res in results.items():
        print(f"\n  {label}:")
        for k, v in res.items():
            status_str = "OK" if v else "FAIL"
            if k == "is_removed" and v:
                status_str = "RIMOSSO (correttamente rilevato)"
            elif k == "is_blocked":
                status_str = "BLOCCATO" if v else "OK"
            print(f"    {k}: {status_str}")
            if k in ("page_load", "contact_button_found") and not v:
                all_pass = False

    print(f"\n  Risultato globale: {'PASS' if all_pass else 'FAIL'}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
