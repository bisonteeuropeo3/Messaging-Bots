"""
Motore di campagna — loop principale di invio con batch, pause, anti-detection.

Ogni piattaforma importa questo modulo e passa il proprio oggetto Platform.
"""

import csv
import os
import sys
import time
import random
import traceback

import yaml
from playwright.sync_api import sync_playwright

from core.browser import (
    get_launch_args, create_context, login_interactive, save_snapshot,
)
from core.scheduler import Scheduler
from core.progress import (
    load_progress, save_progress, record_result, is_already_done,
)
from core.logger import StructuredLogger


def load_config(path: str) -> dict:
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def load_listings(csv_path: str) -> list[dict]:
    if not os.path.exists(csv_path):
        print(f"ERRORE: {csv_path} non trovato.")
        print("Esegui prima: python generate_messages.py")
        sys.exit(1)
    with open(csv_path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _is_browser_dead(reason: str) -> bool:
    """Verifica se l'errore indica un browser/context crashato."""
    dead_markers = [
        "has been closed",
        "Target closed",
        "browser has been closed",
        "context has been closed",
        "page has been closed",
        "Connection closed",
    ]
    return any(m.lower() in reason.lower() for m in dead_markers)


def run_batch(platform, page, context, pending: list[dict], batch_size: int,
              config: dict, progress: dict, progress_path: str,
              scheduler: Scheduler, logger: StructuredLogger,
              browser=None, auth_path: str = "") -> tuple:
    """
    Invia un batch di messaggi.
    Ritorna: (batch_sent, batch_errors, blocked, page, context)
    page/context vengono ritornati perche' potrebbero essere ricreati dopo un crash.
    """
    batch_sent = 0
    batch_errors = 0
    blocked = False

    for i, row in enumerate(pending[:batch_size]):
        # Rate limit
        ok, reason = scheduler.check_rate_limits()
        if not ok:
            print(f"\n    RATE LIMIT: {reason}")
            logger.log_session(platform.name, "rate_limit", reason=reason)
            break

        # Session limit
        should_stop, reason = scheduler.should_stop()
        if should_stop:
            print(f"\n    STOP: {reason}")
            break

        url = row.get("url", "").strip()
        message = row.get("custom_message", "").strip()
        title = row.get("title", url)[:60]

        print(f"\n  [{i+1}/{min(len(pending), batch_size)}] {title}")
        print(f"    URL: {url}")

        if not url or not message:
            print(f"    URL o messaggio vuoto — skip")
            record_result(progress, url, "skipped_no_form",
                          title=title, reason="URL o messaggio vuoto")
            save_progress(progress, progress_path)
            continue

        # Invio
        start_ms = time.time()
        status, reason = platform.send_message(page, url, message, config)
        duration_ms = int((time.time() - start_ms) * 1000)

        logger.log_attempt(
            platform=platform.name, url=url, title=title,
            status=status, reason=reason, attempt=1,
            duration_ms=duration_ms,
        )

        if status == "sent":
            scheduler.reset_errors()
            scheduler.record_sent()
            batch_sent += 1
            print(f"    INVIATO (confermato)")

        elif status == "uncertain":
            scheduler.reset_errors()
            scheduler.record_sent()
            batch_sent += 1
            print(f"    INVIATO (senza conferma esplicita)")

        elif status == "blocked":
            print(f"    BLOCCATO: {reason}")
            record_result(progress, url, status, title=title,
                          reason=reason, msg_text=message)
            save_progress(progress, progress_path)
            logger.log_session(platform.name, "blocked", reason=reason)
            blocked = True
            break

        elif status in ("timeout", "send_failed", "validation_error"):
            scheduler.error_cooldown()
            batch_errors += 1
            print(f"    ERRORE ({status}): {reason}")

            # Se il browser e' crashato, ricrea context e page
            if _is_browser_dead(reason) and browser and auth_path:
                print(f"    Browser crashato — ricreo context...")
                logger.log_session(platform.name, "browser_recovery",
                                   reason="context/page chiuso, ricreo")
                try:
                    # Chiudi vecchio context se possibile
                    try:
                        context.close()
                    except Exception:
                        pass
                    context = create_context(browser, config, auth_path)
                    page = context.new_page()
                    print(f"    Context ricreato OK")
                    time.sleep(random.uniform(2, 4))
                except Exception as e:
                    print(f"    Impossibile ricreare context: {e}")
                    break

            # Retry
            should_stop2, _ = scheduler.should_stop()
            if not should_stop2:
                print(f"    Retry...")
                start2 = time.time()
                status2, reason2 = platform.send_message(page, url, message, config)
                dur2 = int((time.time() - start2) * 1000)
                logger.log_attempt(
                    platform=platform.name, url=url, title=title,
                    status=status2, reason=reason2, attempt=2,
                    duration_ms=dur2,
                )
                if status2 in ("sent", "uncertain"):
                    scheduler.reset_errors()
                    scheduler.record_sent()
                    batch_sent += 1
                    status = status2
                    reason = reason2
                    print(f"    Retry OK: {status2}")
                elif status2 == "blocked":
                    blocked = True
                    record_result(progress, url, status2, title=title,
                                  reason=reason2, msg_text=message)
                    save_progress(progress, progress_path)
                    break
                else:
                    status = status2
                    reason = reason2
                    print(f"    Retry fallito: {status2}")

        elif status == "skipped_no_form":
            print(f"    SALTATO: {reason}")

        elif status == "skipped_removed":
            print(f"    RIMOSSO: {reason}")

        record_result(progress, url, status, title=title,
                      reason=reason, msg_text=message)
        save_progress(progress, progress_path)

        # Pausa lunga periodica
        if status in ("sent", "uncertain"):
            scheduler.maybe_long_pause()

        # Delay tra messaggi
        if i < min(len(pending), batch_size) - 1 and not blocked:
            scheduler.wait_between_messages()

    return batch_sent, batch_errors, blocked, page, context


def run_campaign(platform, script_dir: str, args):
    """
    Entry point principale. Gestisce batch multipli con pause inter-sessione.

    args deve avere: total, batch, pause, dry_run, config (path)
    """
    config_path = getattr(args, 'config', os.path.join(script_dir, "config.yaml"))
    config = load_config(config_path)

    csv_path = os.path.join(script_dir, "listings_ready.csv")
    progress_path = os.path.join(script_dir, "progress.json")
    logs_dir = os.path.join(script_dir, "logs")
    auth_path = os.path.join(script_dir, "auth_state.json")

    listings = load_listings(csv_path)
    progress = load_progress(progress_path)
    progress["total"] = len(listings)
    logger = StructuredLogger(logs_dir)

    total_target = args.total or 999999
    batch_size = args.batch or 50
    pause_minutes = args.pause or 10

    # Filtra pending
    url_field = platform.url_field
    all_pending = []
    for row in listings:
        url = row.get("url", "").strip() or row.get(url_field, "").strip()
        # Assicura che 'url' sia presente nel row
        if url and not row.get("url"):
            row["url"] = url
        if url and not is_already_done(progress, url):
            all_pending.append(row)

    already_done = sum(1 for v in progress["listings"].values()
                       if v.get("status") in ("sent", "uncertain"))

    print(f"Piattaforma      : {platform.name}")
    print(f"Totale annunci   : {len(listings)}")
    print(f"Gia' completati  : {already_done}")
    print(f"Da inviare       : {len(all_pending)}")
    print(f"Obiettivo        : {total_target if total_target < 999999 else 'tutti'}")
    print(f"Batch            : {batch_size} messaggi")
    print(f"Pausa tra batch  : {pause_minutes} minuti")
    print(f"Delay messaggi   : {config.get('delay_min', 25)}-{config.get('delay_max', 55)}s")
    print(f"Max per ora      : {config.get('max_per_hour', 25)}")
    print(f"Max per giorno   : {config.get('max_per_day', 100)}")
    if args.dry_run:
        print(f"MODALITA' DRY-RUN")
    print()

    if not all_pending:
        print("Nessun annuncio pending. Tutto completato!")
        return

    logger.log_session(platform.name, "campaign_start",
                       pending=len(all_pending), total_target=total_target,
                       batch_size=batch_size, pause_min=pause_minutes)

    # ── Dry run ──
    if args.dry_run:
        for i, row in enumerate(all_pending[:total_target]):
            url = row.get("url", "")
            title = row.get("title", "")[:60]
            msg = row.get("custom_message", "")
            print(f"[DRY {i+1}] {title}")
            print(f"  URL: {url}")
            print(f"  Msg ({len(msg)} chars): {msg[:80]}...")
            if (i + 1) % batch_size == 0 and i + 1 < total_target:
                print(f"\n  --- pausa {pause_minutes} min ---\n")
        n = min(len(all_pending), total_target)
        batches = (n + batch_size - 1) // batch_size
        total_time = n * 40 / 60 + (batches - 1) * pause_minutes  # stima
        print(f"\nDry run: {n} messaggi in ~{batches} batch.")
        print(f"Tempo stimato: ~{total_time:.0f} minuti ({total_time/60:.1f} ore)")
        return

    # ── Invio reale con batch multipli ──
    campaign_sent = 0
    campaign_errors = 0

    with sync_playwright() as p:
        need_login = not os.path.exists(auth_path)
        launch_args = get_launch_args(config)

        if need_login:
            print("Prima esecuzione — apertura browser per login...")
            browser = p.chromium.launch(**launch_args)
            login_interactive(browser, platform.login_url, auth_path, config)
            browser.close()

        browser = p.chromium.launch(**launch_args)
        context = create_context(browser, config, auth_path)
        page = context.new_page()

        print("Verifica sessione login...")
        if not platform.is_logged_in(page):
            print("Sessione scaduta — ri-autenticazione necessaria.")
            if os.path.exists(auth_path):
                os.remove(auth_path)
            context.close()
            login_interactive(browser, platform.login_url, auth_path, config)
            context = create_context(browser, config, auth_path)
            page = context.new_page()

        print("Login OK\n")

        batch_num = 0
        scheduler = Scheduler(config)

        try:
            while campaign_sent < total_target and all_pending:
                batch_num += 1
                remaining = total_target - campaign_sent
                current_batch = min(batch_size, remaining, len(all_pending))

                print("=" * 60)
                print(f"BATCH {batch_num} — {current_batch} messaggi")
                print(f"  Progresso campagna: {campaign_sent}/{total_target}")
                print("=" * 60)

                b_sent, b_errors, blocked, page, context = run_batch(
                    platform, page, context, all_pending, current_batch,
                    config, progress, progress_path, scheduler, logger,
                    browser=browser, auth_path=auth_path,
                )

                campaign_sent += b_sent
                campaign_errors += b_errors

                # Rimuovi dal pending quelli gia' processati
                done_urls = set(progress["listings"].keys())
                all_pending = [r for r in all_pending
                               if r.get("url", "") not in done_urls]

                if blocked:
                    print(f"\nBlocco rilevato. Campagna interrotta.")
                    break

                if campaign_sent >= total_target:
                    print(f"\nObiettivo raggiunto: {campaign_sent} messaggi inviati.")
                    break

                if not all_pending:
                    print(f"\nTutti gli annunci processati.")
                    break

                # Pausa inter-batch
                jitter = random.uniform(-2, 2)
                actual_pause = max(5, pause_minutes + jitter)
                print(f"\n{'='*60}")
                print(f"PAUSA INTER-SESSIONE: {actual_pause:.0f} minuti")
                print(f"Prossimo batch alle ~{_time_after_minutes(actual_pause)}")
                print(f"{'='*60}\n")

                logger.log_session(platform.name, "batch_pause",
                                   batch=batch_num, sent=b_sent,
                                   pause_min=actual_pause)

                time.sleep(actual_pause * 60)

        except KeyboardInterrupt:
            print("\n\nInterrotto dall'utente (Ctrl+C).")
            logger.log_session(platform.name, "interrupted")
        except Exception:
            print("\n\nErrore imprevisto:")
            traceback.print_exc()
            logger.log_session(platform.name, "crash",
                               error=traceback.format_exc())
        finally:
            try:
                context.storage_state(path=auth_path)
            except Exception:
                pass
            context.close()
            browser.close()

    save_progress(progress, progress_path)

    total_done = sum(1 for v in progress["listings"].values()
                     if v.get("status") in ("sent", "uncertain"))

    print()
    print("=" * 60)
    print(f"CAMPAGNA COMPLETATA ({platform.name})")
    print(f"  Batch eseguiti          : {batch_num}")
    print(f"  Inviati questa campagna : {campaign_sent}")
    print(f"  Errori questa campagna  : {campaign_errors}")
    print(f"  Totale inviati (storico): {total_done}")
    print(f"  Progress                : {progress_path}")
    print(f"  Log                     : {logs_dir}/")
    print("=" * 60)

    logger.log_session(platform.name, "campaign_end",
                       batches=batch_num, sent=campaign_sent,
                       errors=campaign_errors, total=total_done)


def _time_after_minutes(minutes: float) -> str:
    from datetime import datetime, timedelta
    t = datetime.now() + timedelta(minutes=minutes)
    return t.strftime("%H:%M")
