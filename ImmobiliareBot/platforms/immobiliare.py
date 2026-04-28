"""Piattaforma immobiliare.it"""

import time
import random
from playwright.sync_api import Page, TimeoutError as PWTimeoutError

from platforms.base import Platform
from core.browser import (
    accept_cookies, find_element, human_click, human_type,
    human_scroll, save_snapshot,
)

TEXTAREA_SELECTORS = [
    "textarea[name='body']",
    "textarea[name='message']",
    "textarea[placeholder*='messaggio' i]",
    "textarea[placeholder*='scrivi' i]",
    "textarea[placeholder*='testo' i]",
    "textarea[aria-label*='messaggio' i]",
    ".nd-chat__textarea textarea",
    ".im-chat-input textarea",
    ".contact-form textarea",
    "form textarea",
    "textarea",
]

SEND_BUTTON_SELECTORS = [
    "button[type='submit']:has-text('Invia')",
    "button:has-text('Invia messaggio')",
    "button:has-text('Invia')",
    "button[aria-label*='invia' i]",
    "input[type='submit']",
    "[data-testid='send-button']",
    "button[type='submit']",
]

REMOVED_LISTING_INDICATORS = [
    "text=Questo annuncio non è disponibile",
    "text=annuncio non disponibile",
    "text=annuncio non esiste",
    "text=non è più disponibile",
    "text=è stato venduto",
    "text=L'annuncio è scaduto",
    "text=annuncio scaduto",
    "text=Annuncio rimosso",
    "text=non esiste più",
    "text=Pagina non trovata",
]

BLOCK_INDICATORS = [
    "text=comportamento",
    "text=sospett",
    "text=troppi",
    "text=bloccato",
    "text=captcha",
    "[class*='captcha']",
    "[id*='captcha']",
]

SUCCESS_INDICATORS = [
    "text=Messaggio inviato",
    "text=Richiesta inviata",
    "[class*='success']",
    "[class*='sent']",
    ".nd-snackbar",
]


class Immobiliare(Platform):
    name = "immobiliare"
    login_url = "https://www.immobiliare.it/login/"
    url_field = "directLink"

    def is_logged_in(self, page: Page) -> bool:
        try:
            page.goto("https://www.immobiliare.it/",
                       wait_until="domcontentloaded", timeout=15000)
            accept_cookies(page)
            indicator = page.locator(
                "[data-cy='user-menu'], [href*='/profilo/'], .nd-avatar"
            ).first
            return indicator.is_visible(timeout=5000)
        except Exception:
            return False

    def detect_removed(self, page: Page) -> bool:
        for sel in REMOVED_LISTING_INDICATORS:
            try:
                if page.locator(sel).first.is_visible(timeout=1000):
                    return True
            except Exception:
                pass
        # Controlla anche se la pagina ha restituito 404 tramite il titolo
        title = page.title().lower()
        if any(kw in title for kw in ("non trovata", "non disponibile", "404", "scaduto")):
            return True
        return False

    def detect_block(self, page: Page) -> bool:
        for sel in BLOCK_INDICATORS:
            try:
                if page.locator(sel).first.is_visible(timeout=1000):
                    return True
            except Exception:
                pass
        return False

    def send_message(self, page: Page, url: str, message: str,
                     config: dict) -> tuple[str, str]:
        # 1. Carica pagina
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_load_state("networkidle", timeout=10000)
        except PWTimeoutError:
            return "timeout", "pagina non caricata"
        except Exception as e:
            return "timeout", str(e)

        time.sleep(random.uniform(1.5, 3.0))
        accept_cookies(page)

        # 2. Controlla blocco
        if self.detect_block(page):
            save_snapshot(page, "blocked_immobiliare")
            return "blocked", "rilevato blocco anti-bot"

        # 2b. Controlla se annuncio rimosso/scaduto
        if self.detect_removed(page):
            return "skipped_removed", "annuncio non più disponibile"

        # 3. Simula lettura annuncio (scroll)
        human_scroll(page)
        time.sleep(random.uniform(1.0, 2.5))

        # 4. Trova textarea
        textarea = find_element(page, TEXTAREA_SELECTORS, timeout=4000)
        if textarea is None:
            # Scroll giu' per cercare il form
            page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.6)")
            time.sleep(random.uniform(0.8, 1.5))
            textarea = find_element(page, TEXTAREA_SELECTORS, timeout=4000)

        if textarea is None:
            ss, html = save_snapshot(page, "no_textarea_immobiliare")
            return "skipped_no_form", "textarea non trovata"

        # 5. Compila messaggio
        try:
            human_type(page, textarea, message, config)
            time.sleep(random.uniform(0.5, 1.0))
            # Verifica
            actual = textarea.input_value()
            if len(actual.strip()) < 20:
                return "validation_error", "testo non inserito correttamente"
        except Exception as e:
            save_snapshot(page, "fill_error_immobiliare")
            return "validation_error", str(e)

        # 6. Invia
        send_btn = find_element(page, SEND_BUTTON_SELECTORS, timeout=4000)
        if send_btn is None:
            save_snapshot(page, "no_send_btn_immobiliare")
            return "send_failed", "bottone Invia non trovato"

        try:
            human_click(page, send_btn)
            time.sleep(random.uniform(2.0, 3.5))
        except Exception as e:
            save_snapshot(page, "send_error_immobiliare")
            return "send_failed", str(e)

        # 7. Verifica successo esplicito
        if self.detect_block(page):
            save_snapshot(page, "blocked_after_send_immobiliare")
            return "blocked", "blocco rilevato dopo invio"

        for sel in SUCCESS_INDICATORS:
            try:
                if page.locator(sel).first.is_visible(timeout=2000):
                    return "sent", "conferma esplicita"
            except Exception:
                pass

        # Nessuna conferma esplicita
        ss, html = save_snapshot(page, "uncertain_immobiliare")
        return "uncertain", "nessuna conferma visibile"
