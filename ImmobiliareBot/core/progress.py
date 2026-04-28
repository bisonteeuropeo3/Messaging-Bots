"""Gestione progress.json con stati granulari."""

import hashlib
import json
import os
from datetime import datetime

# Stati possibili per un annuncio
STATUSES = {
    "sent",              # messaggio inviato con conferma esplicita
    "uncertain",         # messaggio probabilmente inviato ma senza conferma
    "skipped_no_form",   # form di contatto non trovato
    "skipped_removed",   # annuncio rimosso o venduto
    "timeout",           # timeout caricamento pagina
    "blocked",           # rilevato blocco anti-bot
    "validation_error",  # errore compilazione form
    "send_failed",       # click invia fallito
}


def message_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def load_progress(path: str) -> dict:
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {
        "total": 0,
        "sent": 0,
        "uncertain": 0,
        "skipped": 0,
        "errors": 0,
        "last_updated": "",
        "listings": {},
    }


def save_progress(progress: dict, path: str):
    progress["last_updated"] = datetime.now().isoformat()
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def record_result(progress: dict, url: str, status: str, title: str = "",
                  reason: str = "", attempt: int = 1, msg_text: str = "",
                  screenshot: str = "", html_snapshot: str = ""):
    progress["listings"][url] = {
        "status": status,
        "reason": reason,
        "attempts": attempt,
        "timestamp": datetime.now().isoformat(),
        "title": title[:80],
        "message_hash": message_hash(msg_text) if msg_text else "",
        "screenshot": screenshot,
        "html_snapshot": html_snapshot,
    }
    if status == "sent":
        progress["sent"] += 1
    elif status == "uncertain":
        progress["uncertain"] += 1
    elif status in ("skipped_no_form", "skipped_removed"):
        progress["skipped"] += 1
    else:
        progress["errors"] += 1


def is_already_done(progress: dict, url: str) -> bool:
    entry = progress["listings"].get(url, {})
    return entry.get("status") in ("sent", "uncertain", "skipped_removed", "skipped_no_form")
