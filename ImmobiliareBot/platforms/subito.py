"""Piattaforma subito.it"""

import time
import random
from playwright.sync_api import Page, TimeoutError as PWTimeoutError

from platforms.base import Platform
from core.browser import (
    accept_cookies, find_element, human_click, human_type,
    human_scroll, save_snapshot,
)

CONTACT_BUTTON_SELECTORS = [
    # Classe reale del bottone "Contatta" su subito.it (aprile 2026)
    "button[class*='MwSkrG__contactButton']",
    "button[class*='contactButton']",
    # Sticky CTA bar in fondo alla pagina
    "#sticky-cta-container button:has-text('Contatta')",
    # Fallback generici
    "button:has-text('Contatta')",
    "a:has-text('Contatta')",
    "button:has-text('Rispondi')",
    "button:has-text('Chatta')",
    "button:has-text('Scrivi')",
]

TEXTAREA_SELECTORS = [
    "textarea[name='new_message']",        # campo reale subito.it
    "textarea[placeholder*='Scrivi un messaggio' i]",  # placeholder reale
    "textarea[name='message']",
    "textarea[name='body']",
    "textarea[placeholder*='messaggio' i]",
    "textarea[placeholder*='scrivi' i]",
    "textarea[aria-label*='messaggio' i]",
    "[role='dialog'] textarea",
    "[class*='chat'] textarea",
    "[class*='message'] textarea",
    "[class*='reply'] textarea",
    "[class*='modal'] textarea",
    "[class*='overlay'] textarea",
    "[class*='sidebar'] textarea",
    "form textarea",
    "textarea",
]

SEND_BUTTON_SELECTORS = [
    "button[class*='send-message']",       # classe reale subito.it
    "button:has-text('Invia messaggio')",
    "button[type='submit']:has-text('Invia')",
    "button:has-text('Invia')",
    "button[aria-label*='invia' i]",
    "[data-testid='send-button']",
    "[role='dialog'] button[type='submit']",
    "[class*='send'] button",
    "input[type='submit']",
    "button[type='submit']",
]

REMOVED_LISTING_INDICATORS = [
    "text=Questo annuncio non esiste più",
    "text=annuncio non esiste",
    "text=annuncio non disponibile",
    "text=È stato venduto",
    "text=non è più disponibile",
]

BLOCK_INDICATORS = [
    "text=comportamento sospetto",
    "text=troppi messaggi",
    "text=verifica che sei un umano",
    "iframe[src*='datadome']",
    ".captcha-container:not(.d-none):not([style*='display: none'])",
]

SUCCESS_INDICATORS = [
    "text=Messaggio inviato",
    "text=inviato",
    "text=Richiesta inviata",
    "[class*='success']",
    "[class*='sent']",
    "[class*='confirmation']",
]


class Subito(Platform):
    name = "subito"
    login_url = "https://areariservata.subito.it/login_form"
    url_field = "page_url"

    def is_logged_in(self, page: Page) -> bool:
        try:
            page.goto("https://www.subito.it/",
                       wait_until="domcontentloaded", timeout=15000)
            accept_cookies(page)
            # Il menu loggato mostra il nome utente nella classe 'username'
            # e ha link a /profilo, /annunci, logout ecc.
            indicator = page.locator(
                "[class*='username'], "
                "[class*='user-menu'], "
                "[href*='areariservata.subito.it/annunci'], "
                "[href*='areariservata.subito.it/logout'], "
                "[class*='UserMenu'], "
                "[class*='avatar']"
            ).first
            return indicator.is_visible(timeout=5000)
        except Exception:
            return False

    def detect_block(self, page: Page) -> bool:
        for sel in BLOCK_INDICATORS:
            try:
                el = page.locator(sel).first
                if el.is_visible(timeout=1000):
                    return True
            except Exception:
                pass

        # Check iframe captcha — ignora reCAPTCHA v3 invisibili (render=)
        try:
            iframes = page.locator("iframe[src*='captcha'], iframe[src*='challenge']")
            for i in range(iframes.count()):
                iframe = iframes.nth(i)
                src = iframe.get_attribute("src") or ""
                if "render=" in src:
                    continue  # reCAPTCHA v3 scoring, invisibile
                if iframe.is_visible(timeout=500):
                    return True
        except Exception:
            pass

        return False

    def detect_removed(self, page: Page) -> bool:
        """Rileva se l'annuncio è stato rimosso/venduto."""
        for sel in REMOVED_LISTING_INDICATORS:
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
            page.goto(url, wait_until="domcontentloaded", timeout=25000)
        except PWTimeoutError:
            return "timeout", "pagina non caricata"
        except Exception as e:
            return "timeout", str(e)

        # Attendi networkidle ma senza bloccare se scade (ads/trackers lenti)
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except PWTimeoutError:
            pass  # prosegui, il contenuto principale è già caricato

        time.sleep(random.uniform(2.0, 4.0))
        accept_cookies(page)

        # 2. Controlla se l'annuncio è stato rimosso/venduto
        if self.detect_removed(page):
            return "skipped_removed", "annuncio rimosso o venduto"

        # 3. Controlla blocco
        if self.detect_block(page):
            save_snapshot(page, "blocked_subito")
            return "blocked", "rilevato blocco anti-bot"

        # 4. Simula lettura annuncio scrollando fino in fondo
        #    Il bottone "Contatta" è molto in basso, caricato lazy da React
        for _ in range(random.randint(4, 7)):
            human_scroll(page)
            time.sleep(random.uniform(0.8, 1.5))
        # Scroll fino in fondo per triggerare il caricamento lazy
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(random.uniform(2.0, 3.5))
        # Torna su leggermente (la sticky bar appare dopo scroll)
        page.evaluate("window.scrollBy(0, -300)")
        time.sleep(random.uniform(1.0, 2.0))

        # 5. Aspetta idratazione React — lo skeleton viene sostituito dal vero bottone
        #    Attendi che almeno uno skeleton sparisca (segnale di idratazione completata)
        try:
            page.wait_for_function(
                "() => !document.querySelector('[class*=\"skeleton\"][class*=\"themed\"]')",
                timeout=10000,
            )
        except Exception:
            pass  # continua comunque, il bottone potrebbe essere gia' pronto
        time.sleep(random.uniform(0.5, 1.0))

        # 6. Click "Contatta" — cerca nella sticky bar o nella sezione venditore
        contact_btn = None
        for sel in CONTACT_BUTTON_SELECTORS:
            try:
                btns = page.locator(sel)
                for i in range(btns.count()):
                    btn = btns.nth(i)
                    try:
                        btn.scroll_into_view_if_needed(timeout=3000)
                        if btn.is_visible(timeout=2000):
                            contact_btn = btn
                            break
                    except Exception:
                        continue
                if contact_btn:
                    break
            except Exception:
                continue

        if contact_btn is None:
            save_snapshot(page, "no_contact_btn_subito")
            return "skipped_no_form", "bottone Contatta non trovato"

        try:
            contact_btn.scroll_into_view_if_needed(timeout=3000)
            time.sleep(random.uniform(0.3, 0.6))
            contact_btn.click(timeout=5000)
            # Il dialog React richiede tempo per caricarsi
            time.sleep(random.uniform(3.0, 5.0))
        except Exception:
            # Fallback: prova con JavaScript click
            try:
                contact_btn.dispatch_event("click")
                time.sleep(random.uniform(3.0, 5.0))
            except Exception:
                save_snapshot(page, "contact_click_error_subito")
                return "send_failed", "errore click Contatta"

        # Controlla se il click ha triggerato un redirect al login
        if "login" in page.url or "areariservata" in page.url:
            save_snapshot(page, "login_redirect_subito")
            return "blocked", "sessione scaduta — redirect al login"

        # 7. Trova textarea nel dialog aperto
        textarea = find_element(page, TEXTAREA_SELECTORS, timeout=6000)
        if textarea is None:
            # Potrebbe servire piu' tempo per il dialog React
            time.sleep(random.uniform(2.0, 3.0))
            textarea = find_element(page, TEXTAREA_SELECTORS, timeout=5000)

        if textarea is None:
            ss, html = save_snapshot(page, "no_textarea_subito")
            return "skipped_no_form", "textarea non trovata dopo click Contatta"

        # 6. Compila messaggio
        try:
            human_type(page, textarea, message, config)
            time.sleep(random.uniform(0.5, 1.2))
            actual = textarea.input_value()
            if len(actual.strip()) < 20:
                return "validation_error", "testo non inserito correttamente"
        except Exception as e:
            save_snapshot(page, "fill_error_subito")
            return "validation_error", str(e)

        # 7. Invia
        send_btn = find_element(page, SEND_BUTTON_SELECTORS, timeout=4000)
        if send_btn is None:
            save_snapshot(page, "no_send_btn_subito")
            return "send_failed", "bottone Invia non trovato"

        try:
            human_click(page, send_btn)
            time.sleep(random.uniform(2.5, 4.0))
        except Exception as e:
            save_snapshot(page, "send_error_subito")
            return "send_failed", str(e)

        # 8. Verifica
        if self.detect_block(page):
            save_snapshot(page, "blocked_after_send_subito")
            return "blocked", "blocco rilevato dopo invio"

        for sel in SUCCESS_INDICATORS:
            try:
                if page.locator(sel).first.is_visible(timeout=2000):
                    return "sent", "conferma esplicita"
            except Exception:
                pass

        ss, html = save_snapshot(page, "uncertain_subito")
        return "uncertain", "nessuna conferma visibile"
