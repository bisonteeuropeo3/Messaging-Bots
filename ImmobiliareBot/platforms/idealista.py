"""Piattaforma idealista.it"""

import time
import random
from playwright.sync_api import Page, TimeoutError as PWTimeoutError

from platforms.base import Platform
from core.browser import (
    accept_cookies, find_element, human_click, human_type,
    human_scroll, save_snapshot,
)

CONTACT_BUTTON_SELECTORS = [
    "button:has-text('Contatta')",
    "button:has-text('Contatta l')",
    "a:has-text('Contatta')",
    "[class*='contact'] button",
    "[class*='Contact'] button",
    "button:has-text('Invia messaggio')",
    "[data-testid='contact-button']",
    "button:has-text('Rispondi')",
]

# Idealista spesso usa input fields separati + textarea
NAME_INPUT_SELECTORS = [
    "input[name='contactName']",
    "input[name='name']",
    "input[placeholder*='nome' i]",
    "input[id*='name' i]",
]

EMAIL_INPUT_SELECTORS = [
    "input[name='email']",
    "input[name='contactEmail']",
    "input[type='email']",
    "input[placeholder*='email' i]",
]

PHONE_INPUT_SELECTORS = [
    "input[name='phone']",
    "input[name='contactPhone']",
    "input[type='tel']",
    "input[placeholder*='telefono' i]",
]

TEXTAREA_SELECTORS = [
    "textarea[name='message']",
    "textarea[name='body']",
    "textarea[name='commentText']",
    "textarea[placeholder*='messaggio' i]",
    "textarea[placeholder*='scrivi' i]",
    "textarea[aria-label*='messaggio' i]",
    "[class*='contact'] textarea",
    "form textarea",
    "textarea",
]

SEND_BUTTON_SELECTORS = [
    "button[type='submit']:has-text('Invia')",
    "button:has-text('Invia messaggio')",
    "button:has-text('Invia')",
    "button:has-text('Contatta')",
    "button[aria-label*='invia' i]",
    "input[type='submit']",
    "[data-testid='send-button']",
    "button[type='submit']",
]

BLOCK_INDICATORS = [
    "text=comportamento",
    "text=sospett",
    "text=troppi",
    "text=bloccato",
    "text=captcha",
    "text=verifica",
    "text=robot",
    "[class*='captcha']",
    "[id*='captcha']",
    "[class*='challenge']",
    "iframe[src*='captcha']",
    "iframe[src*='recaptcha']",
]

SUCCESS_INDICATORS = [
    "text=Messaggio inviato",
    "text=Email inviata",
    "text=inviato con successo",
    "text=Grazie",
    "[class*='success']",
    "[class*='sent']",
    "[class*='confirmation']",
    "[class*='thank']",
]


class Idealista(Platform):
    name = "idealista"
    login_url = "https://www.idealista.it/login"
    url_field = "url"  # campo URL nel CSV idealista

    def is_logged_in(self, page: Page) -> bool:
        try:
            page.goto("https://www.idealista.it/",
                       wait_until="domcontentloaded", timeout=15000)
            accept_cookies(page)
            indicator = page.locator(
                "[href*='/il-mio-idealista'], "
                "[class*='user-menu'], "
                "[class*='avatar'], "
                "a:has-text('Il mio idealista'), "
                "[href*='/favoriti']"
            ).first
            return indicator.is_visible(timeout=5000)
        except Exception:
            return False

    def detect_block(self, page: Page) -> bool:
        for sel in BLOCK_INDICATORS:
            try:
                if page.locator(sel).first.is_visible(timeout=1000):
                    return True
            except Exception:
                pass
        # Idealista usa molto i captcha
        try:
            frames = page.frames
            for frame in frames:
                if "captcha" in frame.url.lower() or "recaptcha" in frame.url.lower():
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

        time.sleep(random.uniform(2.0, 4.5))
        accept_cookies(page)

        # 2. Controlla blocco
        if self.detect_block(page):
            save_snapshot(page, "blocked_idealista")
            return "blocked", "rilevato blocco anti-bot (captcha)"

        # 3. Simula lettura
        human_scroll(page)
        time.sleep(random.uniform(2.0, 3.5))

        # 4. Click "Contatta" se presente
        contact_btn = find_element(page, CONTACT_BUTTON_SELECTORS, timeout=5000)
        if contact_btn is None:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3)")
            time.sleep(random.uniform(0.8, 1.5))
            contact_btn = find_element(page, CONTACT_BUTTON_SELECTORS, timeout=4000)

        if contact_btn is not None:
            try:
                human_click(page, contact_btn)
                time.sleep(random.uniform(2.0, 3.5))
            except Exception:
                pass

        # 5. Controlla blocco post-click (idealista spesso mostra captcha qui)
        if self.detect_block(page):
            save_snapshot(page, "blocked_idealista_form")
            return "blocked", "captcha rilevato nel form contatto"

        # 6. Trova textarea
        textarea = find_element(page, TEXTAREA_SELECTORS, timeout=5000)
        if textarea is None:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.5)")
            time.sleep(random.uniform(0.8, 1.5))
            textarea = find_element(page, TEXTAREA_SELECTORS, timeout=4000)

        if textarea is None:
            ss, html = save_snapshot(page, "no_textarea_idealista")
            return "skipped_no_form", "textarea non trovata"

        # 7. Compila messaggio
        try:
            human_type(page, textarea, message, config)
            time.sleep(random.uniform(0.5, 1.2))
            actual = textarea.input_value()
            if len(actual.strip()) < 20:
                return "validation_error", "testo non inserito"
        except Exception as e:
            save_snapshot(page, "fill_error_idealista")
            return "validation_error", str(e)

        # 8. Invia
        send_btn = find_element(page, SEND_BUTTON_SELECTORS, timeout=4000)
        if send_btn is None:
            save_snapshot(page, "no_send_btn_idealista")
            return "send_failed", "bottone Invia non trovato"

        try:
            human_click(page, send_btn)
            time.sleep(random.uniform(2.5, 4.5))
        except Exception as e:
            save_snapshot(page, "send_error_idealista")
            return "send_failed", str(e)

        # 9. Verifica
        if self.detect_block(page):
            save_snapshot(page, "blocked_after_send_idealista")
            return "blocked", "blocco rilevato dopo invio"

        for sel in SUCCESS_INDICATORS:
            try:
                if page.locator(sel).first.is_visible(timeout=2500):
                    return "sent", "conferma esplicita"
            except Exception:
                pass

        ss, html = save_snapshot(page, "uncertain_idealista")
        return "uncertain", "nessuna conferma visibile"
