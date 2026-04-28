"""Interfaccia base per le piattaforme."""

from abc import ABC, abstractmethod
from playwright.sync_api import Page


class Platform(ABC):
    """Ogni piattaforma implementa questi metodi."""

    name: str = ""
    login_url: str = ""

    # Campi CSV per estrarre l'URL dell'annuncio
    url_field: str = ""

    @abstractmethod
    def is_logged_in(self, page: Page) -> bool:
        """Verifica se l'utente e' loggato."""

    @abstractmethod
    def send_message(self, page: Page, url: str, message: str,
                     config: dict) -> tuple[str, str]:
        """
        Invia un messaggio all'annuncio.
        Ritorna (status, reason).
        status: sent | uncertain | skipped_no_form | timeout | blocked |
                validation_error | send_failed
        """

    @abstractmethod
    def detect_block(self, page: Page) -> bool:
        """Rileva se il sito ci ha bloccato."""
