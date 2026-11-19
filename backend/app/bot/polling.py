"""Daemon long-polling loop used for local development."""

import logging
import threading

from app.bot.client import TelegramClient
from app.bot.handlers import handle_update
from app.core.db import SessionLocal

log = logging.getLogger(__name__)
_stop = threading.Event()
_thread: threading.Thread | None = None


def _loop() -> None:
    client = TelegramClient()
    offset = None
    backoff = 1.0
    try:
        client.delete_webhook()
    except Exception as exc:  # noqa: BLE001
        log.warning("No se pudo borrar el webhook: %s", exc.__class__.__name__)
    while not _stop.is_set():
        try:
            for update in client.get_updates(offset=offset, timeout=25) or []:
                with SessionLocal() as db:
                    handle_update(db, update, client)
                offset = int(update["update_id"]) + 1
            backoff = 1.0
        except Exception as exc:  # noqa: BLE001
            log.warning("Polling de Telegram falló: %s", exc.__class__.__name__)
            _stop.wait(backoff)
            backoff = min(backoff * 2, 30)


def start() -> None:
    global _thread
    if _thread and _thread.is_alive():
        return
    _stop.clear()
    _thread = threading.Thread(target=_loop, name="telegram-polling", daemon=True)
    _thread.start()


def stop() -> None:
    _stop.set()
    if _thread and _thread.is_alive():
        _thread.join(timeout=2)
