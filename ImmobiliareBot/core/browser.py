"""Browser management — anti-detection, login, interazioni umane."""

import os
import random
import time
from datetime import datetime

from playwright.sync_api import Page, BrowserContext, Browser


SNAPSHOTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "snapshots")

# User agents reali di Chrome su Windows (ruotati)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
]

# Cookie accept selectors (comuni a tutti i siti italiani)
COOKIE_SELECTORS = [
    "button#didomi-notice-agree-button",
    "button[id*='accept']",
    "button:has-text('Accetta tutto')",
    "button:has-text('Accetta tutti')",
    "button:has-text('Accetta')",
    "button:has-text('Accetto')",
    "[class*='cookie'] button[class*='accept']",
    "#onetrust-accept-btn-handler",
]


def get_launch_args(config: dict) -> dict:
    return dict(
        headless=config.get("headless", False),
        channel="chrome",
        slow_mo=config.get("slow_mo", 50),
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-first-run",
            "--no-default-browser-check",
        ],
    )


def create_context(browser: Browser, config: dict,
                   auth_state_path: str | None = None) -> BrowserContext:
    """Crea un browser context con fingerprint randomizzato."""
    widths = config.get("viewport_widths", [1280, 1366, 1440, 1536])
    heights = config.get("viewport_heights", [800, 900, 960, 1024])

    ctx_args = dict(
        viewport={"width": random.choice(widths), "height": random.choice(heights)},
        user_agent=random.choice(USER_AGENTS),
        locale="it-IT",
        timezone_id="Europe/Rome",
    )

    if auth_state_path and os.path.exists(auth_state_path):
        ctx_args["storage_state"] = auth_state_path

    context = browser.new_context(**ctx_args)

    # Inietta script anti-detection
    context.add_init_script("""
        // Nascondi il flag webdriver
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        // Fake plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5],
        });
        // Fake languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['it-IT', 'it', 'en-US', 'en'],
        });
        // Chrome runtime
        window.chrome = { runtime: {} };
    """)

    return context


def accept_cookies(page: Page):
    """Chiudi il banner cookie se presente."""
    for sel in COOKIE_SELECTORS:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=1500):
                human_click(page, btn)
                page.wait_for_load_state("networkidle", timeout=3000)
                return
        except Exception:
            pass


def human_click(page: Page, element, offset_range: int = 5):
    """Click con offset casuale dal centro dell'elemento."""
    try:
        box = element.bounding_box()
        if box:
            x = box["x"] + box["width"] / 2 + random.randint(-offset_range, offset_range)
            y = box["y"] + box["height"] / 2 + random.randint(-offset_range, offset_range)
            page.mouse.click(x, y)
        else:
            element.click()
    except Exception:
        element.click()


def human_type(page: Page, element, text: str, config: dict):
    """Digita testo con velocita' variabile, come un umano."""
    element.click()
    _small_pause(page)
    element.press("Control+a")
    _small_pause(page)
    element.press("Delete")
    _small_pause(page)

    delay_min = config.get("typing_delay_min", 40)
    delay_max = config.get("typing_delay_max", 130)

    for char in text:
        delay = random.randint(delay_min, delay_max)
        page.keyboard.type(char, delay=0)
        time.sleep(delay / 1000)
        # Pausa extra occasionale (come pensare)
        if random.random() < 0.03:
            time.sleep(random.uniform(0.3, 0.8))


def human_scroll(page: Page):
    """Scroll graduale verso il basso, come un umano che legge."""
    scroll_amount = random.randint(200, 500)
    steps = random.randint(3, 6)
    for _ in range(steps):
        page.mouse.wheel(0, scroll_amount // steps)
        time.sleep(random.uniform(0.1, 0.3))
    time.sleep(random.uniform(0.5, 1.5))


def find_element(page: Page, selectors: list[str], timeout: int = 5000):
    """Prova i selettori in ordine, restituisce il primo visibile o None."""
    for sel in selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=timeout):
                return el
        except Exception:
            pass
    return None


def save_snapshot(page: Page, name: str, save_html: bool = True) -> tuple[str, str]:
    """Salva screenshot + HTML della pagina per debug. Ritorna (screenshot_path, html_path)."""
    os.makedirs(SNAPSHOTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.join(SNAPSHOTS_DIR, f"{ts}_{name}")

    screenshot_path = ""
    html_path = ""

    try:
        screenshot_path = f"{base}.png"
        page.screenshot(path=screenshot_path)
    except Exception:
        screenshot_path = ""

    if save_html:
        try:
            html_path = f"{base}.html"
            content = page.content()
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception:
            html_path = ""

    return screenshot_path, html_path


def login_interactive(browser: Browser, login_url: str,
                      auth_state_path: str, config: dict | None = None):
    """Apre browser per login manuale, salva sessione."""
    config = config or {}
    context = create_context(browser, config)
    page = context.new_page()
    page.goto(login_url, wait_until="domcontentloaded")
    print()
    print("=" * 60)
    print(f"  AZIONE RICHIESTA: fai login su {login_url}")
    print("  Quando hai completato il login, torna qui e premi ENTER")
    print("=" * 60)
    input()
    context.storage_state(path=auth_state_path)
    print("  Sessione salvata.")
    context.close()


def launch_persistent(p, config: dict, user_data_dir: str) -> BrowserContext:
    """
    Lancia Chrome reale con un profilo utente persistente.
    Eredita cookies, history e fingerprint del profilo — molto piu' resistente
    al rilevamento anti-bot rispetto a un context vuoto + storage_state.
    """
    widths = config.get("viewport_widths", [1280, 1366, 1440, 1536])
    heights = config.get("viewport_heights", [800, 900, 960, 1024])

    context = p.chromium.launch_persistent_context(
        user_data_dir=user_data_dir,
        channel="chrome",
        headless=config.get("headless", False),
        slow_mo=config.get("slow_mo", 50),
        viewport={"width": random.choice(widths), "height": random.choice(heights)},
        locale="it-IT",
        timezone_id="Europe/Rome",
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-first-run",
            "--no-default-browser-check",
        ],
    )

    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5],
        });
        Object.defineProperty(navigator, 'languages', {
            get: () => ['it-IT', 'it', 'en-US', 'en'],
        });
        window.chrome = { runtime: {} };
    """)

    return context


def login_persistent(context: BrowserContext, login_url: str):
    """Apre login nel profilo persistente — Chrome salva la sessione da solo."""
    page = context.pages[0] if context.pages else context.new_page()
    page.goto(login_url, wait_until="domcontentloaded")
    print()
    print("=" * 60)
    print(f"  AZIONE RICHIESTA: fai login su {login_url}")
    print("  Quando hai completato il login, torna qui e premi ENTER")
    print("=" * 60)
    input()
    print("  Sessione salvata nel profilo Chrome.")


def _small_pause(page: Page):
    time.sleep(random.uniform(0.15, 0.35))
