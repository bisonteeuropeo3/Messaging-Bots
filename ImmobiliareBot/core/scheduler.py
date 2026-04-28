"""Scheduling policy — timing umano, limiti per ora/giorno, backoff."""

import random
import time
from collections import deque
from datetime import datetime, timedelta


class Scheduler:
    def __init__(self, config: dict):
        self.cfg = config
        self.consecutive_errors = 0
        self.session_sent = 0
        # Traccia timestamp invii per rate limiting
        self._hour_timestamps: deque[datetime] = deque()
        self._day_timestamps: deque[datetime] = deque()
        # Prossima pausa lunga dopo N messaggi
        self._next_pause_at = self._random_pause_threshold()

    def _random_pause_threshold(self) -> int:
        return random.randint(
            self.cfg.get("pause_every_min", 4),
            self.cfg.get("pause_every_max", 7),
        )

    def wait_between_messages(self):
        """Attesa tra messaggi con distribuzione normale (piu' umana)."""
        lo = self.cfg.get("delay_min", 25)
        hi = self.cfg.get("delay_max", 55)
        mean = (lo + hi) / 2
        std = (hi - lo) / 4  # ~95% entro [lo, hi]
        delay = max(lo, min(hi, random.gauss(mean, std)))
        print(f"    Attendo {delay:.0f}s...")
        time.sleep(delay)

    def maybe_long_pause(self):
        """Pausa lunga ogni N messaggi — simula 'leggere altri annunci'."""
        self.session_sent += 1
        if self.session_sent >= self._next_pause_at:
            lo = self.cfg.get("pause_duration_min", 120)
            hi = self.cfg.get("pause_duration_max", 300)
            pause = random.uniform(lo, hi)
            print(f"\n    --- Pausa lunga: {pause:.0f}s ({pause/60:.1f} min) ---\n")
            time.sleep(pause)
            self.session_sent = 0
            self._next_pause_at = self._random_pause_threshold()

    def error_cooldown(self):
        """Cooldown dopo errore con backoff progressivo."""
        self.consecutive_errors += 1
        base_lo = self.cfg.get("error_cooldown_min", 60)
        base_hi = self.cfg.get("error_cooldown_max", 120)
        multiplier = min(self.consecutive_errors, 5)
        cooldown = random.uniform(base_lo * multiplier, base_hi * multiplier)
        print(f"    Cooldown errore: {cooldown:.0f}s (tentativo #{self.consecutive_errors})")
        time.sleep(cooldown)

    def reset_errors(self):
        self.consecutive_errors = 0

    def should_stop(self) -> tuple[bool, str]:
        """Controlla se la sessione deve fermarsi."""
        max_errors = self.cfg.get("max_consecutive_errors", 3)
        if self.consecutive_errors >= max_errors:
            return True, f"{max_errors} errori consecutivi"

        max_session = self.cfg.get("max_per_session", 0)
        if max_session and self.session_sent >= max_session:
            return True, f"limite sessione ({max_session})"

        return False, ""

    def check_rate_limits(self) -> tuple[bool, str]:
        """Controlla limiti per ora e per giorno. Ritorna (ok, motivo)."""
        now = datetime.now()

        # Pulisci timestamp vecchi
        hour_ago = now - timedelta(hours=1)
        while self._hour_timestamps and self._hour_timestamps[0] < hour_ago:
            self._hour_timestamps.popleft()

        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        while self._day_timestamps and self._day_timestamps[0] < day_start:
            self._day_timestamps.popleft()

        max_hour = self.cfg.get("max_per_hour", 25)
        if max_hour and len(self._hour_timestamps) >= max_hour:
            wait_until = self._hour_timestamps[0] + timedelta(hours=1)
            wait_secs = (wait_until - now).total_seconds()
            return False, f"limite orario ({max_hour}/h) — riprova tra {wait_secs/60:.0f} min"

        max_day = self.cfg.get("max_per_day", 100)
        if max_day and len(self._day_timestamps) >= max_day:
            return False, f"limite giornaliero ({max_day}/giorno) raggiunto"

        return True, ""

    def record_sent(self):
        """Registra un invio riuscito per il rate limiting."""
        now = datetime.now()
        self._hour_timestamps.append(now)
        self._day_timestamps.append(now)
